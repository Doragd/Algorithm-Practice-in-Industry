import re
import os
import requests
import json
import time
import feedparser
import random
from openai import OpenAI
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_random_exponential
from openai import APIConnectionError, RateLimitError, APIStatusError
from .prompts import PRERANK_PROMPT, FINERANK_PROMPT

# 从环境变量获取配置，同时提供默认值
# 支持多个飞书URL，用逗号分隔
FEISHU_URLS = [url.strip() for url in os.environ.get("FEISHU_URL", "").split(',') if url.strip()]
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", None)
# TARGET_CATEGORYS 使用逗号分隔的字符串格式
TARGET_CATEGORYS = os.environ.get("TARGET_CATEGORYS", "cs.IR,cs.CL,cs.CV")
TARGET_CATEGORYS = [cat.strip() for cat in TARGET_CATEGORYS.split(',')]
MAX_PAPERS = int(os.environ.get("MAX_PAPERS", "100"))
ROUGH_SCORE_THRESHOLD = int(os.environ.get("ROUGH_SCORE_THRESHOLD", "4"))
RETURN_PAPERS = int(os.environ.get("RETURN_PAPERS", "20"))
ARXIV_LOOKBACK_HOURS = int(os.environ.get("ARXIV_LOOKBACK_HOURS", "36"))
ARXIV_PAGE_SIZE = int(os.environ.get("ARXIV_PAGE_SIZE", "100"))
ARXIV_MAX_PAGES = int(os.environ.get("ARXIV_MAX_PAGES", "20"))
ARXIV_REQUEST_INTERVAL = int(os.environ.get("ARXIV_REQUEST_INTERVAL", "60"))
ARXIV_CATEGORY_INTERVAL = int(os.environ.get("ARXIV_CATEGORY_INTERVAL", "120"))
ARXIV_JITTER_SECONDS = int(os.environ.get("ARXIV_JITTER_SECONDS", "120"))
ARXIV_CATEGORY_RETRY_ATTEMPTS = int(os.environ.get("ARXIV_CATEGORY_RETRY_ATTEMPTS", "1"))
ARXIV_USE_DAILY_CACHE = os.environ.get("ARXIV_USE_DAILY_CACHE", "true").lower() == "true"
ARXIV_RETRY_ATTEMPTS = int(os.environ.get("ARXIV_RETRY_ATTEMPTS", "4"))
ARXIV_RETRY_BASE_WAIT = int(os.environ.get("ARXIV_RETRY_BASE_WAIT", "600"))
ARXIV_RETRY_MAX_WAIT = int(os.environ.get("ARXIV_RETRY_MAX_WAIT", "2400"))
ARXIV_CATEGORY_MAX_PAGES = os.environ.get("ARXIV_CATEGORY_MAX_PAGES", "cs.IR:5,cs.CL:8,cs.CV:20")
ARXIV_API_BASE_URLS = [
    url.strip()
    for url in os.environ.get(
        "ARXIV_API_BASE_URLS",
        "https://export.arxiv.org/api/query,https://arxiv.org/api/query",
    ).split(',')
    if url.strip()
]
ARXIV_USER_AGENT = os.environ.get(
    "ARXIV_USER_AGENT",
    "Algorithm-Practice-in-Industry paperBotV2 arxiv_daily; "
    "https://github.com/Doragd/Algorithm-Practice-in-Industry",
)


class ArxivFetchError(RuntimeError):
    """Raised when arXiv data cannot be fetched reliably."""


def parse_category_max_pages(raw_config):
    """解析分类级最大页数配置，例如 cs.IR:5,cs.CL:8,cs.CV:20。"""
    parsed = {}
    for item in raw_config.split(','):
        if ':' not in item:
            continue
        category, max_pages = item.split(':', 1)
        category = category.strip()
        try:
            parsed[category] = int(max_pages.strip())
        except ValueError:
            print(f"⚠️ 忽略无效的分类页数配置: {item}")
    return parsed


CATEGORY_MAX_PAGES = parse_category_max_pages(ARXIV_CATEGORY_MAX_PAGES)


def sleep_with_jitter(base_seconds, reason):
    """带随机抖动的 sleep，降低固定节奏触发 arXiv 限流的概率。"""
    if base_seconds <= 0:
        return
    jitter = random.randint(0, ARXIV_JITTER_SECONDS) if ARXIV_JITTER_SECONDS > 0 else 0
    total_seconds = base_seconds + jitter
    print(f"⏱️ {reason}，等待 {total_seconds}s（基础 {base_seconds}s + 抖动 {jitter}s）")
    time.sleep(total_seconds)


def get_category_max_pages(category):
    """优先使用分类级页数上限，降低低产分类不必要请求次数。"""
    return CATEGORY_MAX_PAGES.get(category, ARXIV_MAX_PAGES)


def load_today_cached_papers(category):
    """同一天手动重跑时优先复用已有成功结果，减少重复请求 arXiv。"""
    if not ARXIV_USE_DAILY_CACHE:
        return {}

    current_dir = os.path.dirname(os.path.abspath(__file__))
    today_file = os.path.join(current_dir, "data", f"{datetime.now().strftime('%Y%m%d')}.json")
    if not os.path.exists(today_file):
        return {}

    try:
        with open(today_file, 'r', encoding='utf-8') as f:
            today_data = json.load(f)
    except Exception as exc:
        print(f"⚠️ 读取今日缓存失败，将继续请求 arXiv: {exc}")
        return {}

    cached = {
        arxiv_id: paper
        for arxiv_id, paper in today_data.items()
        if category in paper.get('categories', '')
    }
    if cached:
        print(f"📦 分类 '{category}' 复用今日缓存 {len(cached)} 篇论文，跳过 arXiv 请求。")
    return cached


def parse_arxiv_entry(entry):
    """将 arXiv feed entry 转换为内部论文结构。"""
    title = re.sub(r'\s+', ' ', entry.title.replace('\n', ' ').strip())
    arxiv_id = entry.id.split('/abs/')[-1]
    alphaxiv_link = f"https://www.alphaxiv.org/abs/{arxiv_id}"
    authors = ', '.join(author.name for author in entry.authors)
    summary = re.sub(r'\s+', ' ', entry.summary.replace('\n', ' ').strip())
    published_date = entry.published_parsed
    published_str = datetime(*published_date[:6]).strftime('%Y-%m-%d %H:%M:%S')
    categories = ', '.join(tag.term for tag in entry.tags)

    return arxiv_id, {
        'title': title,
        'url': alphaxiv_link,
        'arxiv_id': arxiv_id,
        'authors': authors,
        'categories': categories,
        'pub_date': published_str,
        'ori_summary': summary,
        'summary': '',  # 占位，后续由 LLM 填充
        'translation': '',  # 占位，后续由 LLM 填充
        'relevance_score': 0,  # 占位，后续由 LLM 填充
        'reasoning': '',  # 占位，后续由 LLM 填充
        'rerank_relevance_score': 0,  # 占位，后续由 LLM 填充
        'rerank_reasoning': '',  # 占位，后续由 LLM 填充
    }


def get_retry_wait_seconds(response, attempt):
    """优先遵循 Retry-After，否则使用指数退避。"""
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            return min(int(retry_after), ARXIV_RETRY_MAX_WAIT)
        except ValueError:
            pass
    return min(ARXIV_RETRY_BASE_WAIT * (2 ** (attempt - 1)), ARXIV_RETRY_MAX_WAIT)


def request_arxiv_page(base_urls, query_params):
    """请求单页 arXiv API；遇到 429/5xx 时长退避重试。"""
    headers = {"User-Agent": ARXIV_USER_AGENT}
    last_error = None
    if isinstance(base_urls, str):
        base_urls = [base_urls]

    for attempt in range(1, ARXIV_RETRY_ATTEMPTS + 1):
        retryable_failure = False
        last_response = None
        for base_url in base_urls:
            try:
                response = requests.get(
                    base_url,
                    params=query_params,
                    headers=headers,
                    timeout=(5, 30),
                )
                last_response = response
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    last_error = requests.exceptions.HTTPError(
                        f"{response.status_code} error from {base_url}"
                    )
                    retryable_failure = True
                    print(
                        f"⏳ arXiv API {base_url} 返回 {response.status_code}，"
                        f"第 {attempt}/{ARXIV_RETRY_ATTEMPTS} 轮重试..."
                    )
                    continue

                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as exc:
                last_error = exc
                retryable_failure = True
                print(
                    f"⏳ arXiv API {base_url} 请求异常: {exc}，"
                    f"第 {attempt}/{ARXIV_RETRY_ATTEMPTS} 轮重试..."
                )

        if attempt == ARXIV_RETRY_ATTEMPTS:
            break

        wait_seconds = get_retry_wait_seconds(last_response if retryable_failure else None, attempt)
        jitter = random.randint(0, ARXIV_JITTER_SECONDS) if ARXIV_JITTER_SECONDS > 0 else 0
        total_wait = min(wait_seconds + jitter, ARXIV_RETRY_MAX_WAIT)
        print(
            f"⏳ 本轮 arXiv API 请求未成功，等待 {total_wait}s "
            f"（基础 {wait_seconds}s + 抖动 {jitter}s）后重试..."
        )
        time.sleep(total_wait)

    raise ArxivFetchError(f"arXiv API 请求多次失败: {last_error}")

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(5))
def call_deepseek_api(prompt_content: str,
                      
                      api_key: str = None,
                      model: str = "deepseek-chat",
                      base_url: str = "https://api.deepseek.com/v1"):
    """
    调用 DeepSeek API 并以 JSON 格式返回结果。
    Args:
        prompt_content (str): 发送给模型的完整提示词内容。
        api_key (str, optional): 你的 DeepSeek API Key。如果为 None，会尝试从环境变量 'DEEPSEEK_API_KEY' 读取。
        model (str, optional): 使用的模型名称。默认为 "deepseek-chat"。
        base_url (str, optional): API 的基础 URL。默认为 DeepSeek 的官方地址。
    Returns:
        dict: 解析后的 JSON 对象。如果发生错误，则返回 None。
    """
    # 优先使用传入的 api_key，否则从环境变量读取
    if api_key is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("🔑 错误: API Key 未提供。请设置 DEEPSEEK_API_KEY 环境变量或通过参数传入。")
        return None
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages = [
            {"role": "user", "content": prompt_content}
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={'type': 'json_object'}  # 强制返回 JSON
        )
        response_content = response.choices[0].message.content
        return json.loads(response_content)
    except (APIConnectionError, RateLimitError, APIStatusError) as e:
        print(f"🔄 API 遇到可重试错误: {e}。正在由 tenacity 进行重试...")
        raise  # 必须重新抛出异常，tenacity 才能捕获并执行重试策略
    except ImportError:
        print("📦 错误：'openai' 库未安装。请运行 'pip install openai'。")
        return None
    except Exception as e:
        print(f"❌ 调用 API 时发生错误: {e}")
        return None


def get_daily_arxiv_papers(category='cs.CL', max_results=20):
    """
    获取指定 arXiv 领域今天发布的论文。

    Args:
        category (str): 你感兴趣的 arXiv 类别，例如 'cs.CL', 'cs.AI', 'stat.ML'。
        max_results (int): 希望获取的最大论文数量。
    """
    results = {}
    end_utc = datetime.now(timezone.utc)
    start_utc = end_utc - timedelta(hours=ARXIV_LOOKBACK_HOURS)
    start_date_str = start_utc.strftime('%Y%m%d%H%M%S')
    end_date_str = end_utc.strftime('%Y%m%d%H%M%S')
    search_query = f'cat:{category} AND submittedDate:[{start_date_str} TO {end_date_str}]'

    page_size = min(max_results, ARXIV_PAGE_SIZE)
    max_pages = get_category_max_pages(category)
    print(
        f"🔍 开始抓取分类 '{category}'，窗口: {start_utc.isoformat()} -> {end_utc.isoformat()}，"
        f"page_size={page_size}, max_pages={max_pages}"
    )
    print("=" * 50)

    for page in range(max_pages):
        query_params = {
            'search_query': search_query,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending',
            'start': page * page_size,
            'max_results': page_size,
        }

        response = request_arxiv_page(ARXIV_API_BASE_URLS, query_params)
        feed = feedparser.parse(response.content)
        entries = feed.entries
        print(f"📄 分类 '{category}' 第 {page + 1} 页返回 {len(entries)} 篇论文")

        if not entries:
            break

        for entry in entries:
            arxiv_id, paper = parse_arxiv_entry(entry)
            results[arxiv_id] = paper

        if len(entries) < page_size:
            break

        sleep_with_jitter(ARXIV_REQUEST_INTERVAL, f"分类 '{category}' 分页请求间隔")

    if not results:
        print(f"📭 分类 '{category}' 在 {ARXIV_LOOKBACK_HOURS} 小时窗口内没有新论文。")
    else:
        print(f"✅ 分类 '{category}' 共抓取 {len(results)} 篇论文。")

    return results


def rough_analyze_paper(arxiv_id, paper):
    prompt = PRERANK_PROMPT.format(title=paper['title'])
    analysis = call_deepseek_api(
        prompt, api_key=DEEPSEEK_API_KEY)
    if analysis:
        # 将分析结果合并到原始论文信息中
        paper.update(analysis)
        return paper
    else:
        # 即使分析失败，也打印日志，但返回 None
        print(f"❌ [{arxiv_id}] {paper['title']} - 分析失败")
        return None


def rough_analyze_papers_cocurrent(results, max_workers=10):
    analyzed_papers = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_paper = {
            executor.submit(rough_analyze_paper, arxiv_id, paper): paper
            for arxiv_id, paper in results.items()
        }
        print(f"\n🚀 开始并发分析 {len(results)} 篇论文，使用 {max_workers} 个工作线程...")
        progress_bar = tqdm(as_completed(future_to_paper),
                            total=len(results), desc="分析进度")
        for future in progress_bar:
            try:
                updated_paper = future.result()
                if updated_paper:
                    analyzed_papers.append(updated_paper)
            except Exception as exc:
                paper_info = future_to_paper[future]
                print(f"⚠️ 处理论文 {paper_info['title']} 时产生异常: {exc}")
    if not analyzed_papers:
        print("📭 \n没有成功分析任何论文。")
        return []
    print(f"\n✅ 所有论文分析完成，成功处理 {len(analyzed_papers)} 篇。")
    return analyzed_papers


def rough_rank_papers(results, filter_threshold=2, max_workers=10):
    # LLM rough analyze papers concurrently
    analyzed_papers = rough_analyze_papers_cocurrent(
        results, max_workers=max_workers)

    # 核心排序逻辑：按 relevance_score 降序排序
    analyzed_papers.sort(key=lambda p: p.get(
        'relevance_score', 0), reverse=True)

    # 打印排序和过滤前的结果预览
    print("\n--- 分析结果预览 (按相关性排序) ---")
    for paper in analyzed_papers:
        print("-" * 60)
        print(f"✅ [{paper['arxiv_id']}] {paper['title']}")
        print(f"  - 翻译: {paper.get('translation', 'N/A')}")
        print(f"  - 相关性评分: {paper.get('relevance_score', 'N/A')}/10")
        print(f"  - 理由: {paper.get('reasoning', 'N/A')}")
    print("-" * 60)

    # 过滤低分论文
    filtered_papers = [p for p in analyzed_papers if p.get(
        'relevance_score', 0) >= filter_threshold]
    print(
        f"\n⚠️ 过滤掉 {len(analyzed_papers) - len(filtered_papers)} 篇低分论文，剩余 {len(filtered_papers)} 篇高质量论文。")
    return filtered_papers


def fine_analyze_paper(arxiv_id, paper):
    prompt = FINERANK_PROMPT.format(
        title=paper['title'], summary=paper['ori_summary'])
    analysis = call_deepseek_api(
        prompt, api_key=DEEPSEEK_API_KEY)
    if analysis:
        # 将分析结果合并到原始论文信息中
        paper.update(analysis)
        return paper
    else:
        # 即使分析失败，也打印日志，但返回 None
        print(f"❌ [{arxiv_id}] {paper['title']} - 分析失败")
        return None


def fine_analyze_papers_cocurrent(papers, max_workers=10):
    analyzed_papers = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_paper = {
            executor.submit(fine_analyze_paper, paper['arxiv_id'], paper): paper
            for paper in papers
        }
        print(f"\n🚀 开始并发精排 {len(papers)} 篇论文，使用 {max_workers} 个工作线程...")
        progress_bar = tqdm(as_completed(future_to_paper),
                            total=len(papers), desc="精排进度")
        for future in progress_bar:
            try:
                updated_paper = future.result()
                if updated_paper:
                    analyzed_papers.append(updated_paper)
            except Exception as exc:
                paper_info = future_to_paper[future]
                print(f"处理论文 {paper_info['title']} 时产生异常: {exc}")
    if not analyzed_papers:
        print("\n没有成功精排任何论文。")
        return []
    print(f"\n✅ 所有论文精排完成，成功处理 {len(analyzed_papers)} 篇。")
    return analyzed_papers


def fine_rank_papers(papers, max_workers=10, paper_count=5):
    papers = papers[:paper_count]  # 只精排前 N 篇论文

    # LLM fine analyze papers concurrently
    analyzed_papers = fine_analyze_papers_cocurrent(
        papers, max_workers=max_workers)

    # 核心排序逻辑：按 rerank_relevance_score 降序排序
    analyzed_papers.sort(key=lambda p: p.get(
        'rerank_relevance_score', 0), reverse=True)

    # 打印排序后的结果预览
    print("\n--- 精排结果预览 (按精排评分排序) ---")
    for paper in analyzed_papers:
        print("-" * 60)
        print(f"✅ [{paper['arxiv_id']}] {paper['title']}")
        print(f"  - 翻译: {paper.get('translation', 'N/A')}")
        print(f"  - 精排相关性评分: {paper.get('rerank_relevance_score', 'N/A')}/10")
        print(f"  - 理由: {paper.get('rerank_reasoning', 'N/A')}")
        print(f"  - 总结: {paper.get('summary', 'N/A')}")
    print("-" * 60)

    return analyzed_papers


def send_papers_to_feishu(papers, feishu_urls=None):
    # 如果没有指定URL列表，使用默认的FEISHU_URLS
    if feishu_urls is None:
        feishu_urls = FEISHU_URLS
    
    # 如果没有设置飞书URL，跳过发送
    if not feishu_urls:
        print("[-] 没有设置飞书URL，跳过发送消息")
        return
    
    date = datetime.now().strftime('%Y-%m-%d')
    
    card_data = {
        "type": "template",
        "data": {
            "template_id": "AAqxH62u1uNko",
            "template_version_name": "1.0.5",
            "template_variable": {
                "loop": [],
                "date": date
            }
        }
    }

    for paper in papers:
        title = paper['title']
        translation = paper.get('translation', 'N/A')
        score = paper.get('rerank_relevance_score', 'N/A')
        summary = paper.get('summary', 'N/A')
        url = paper['url']
        
        paper_formatted = f"[{title}]({url})"
        score_formatted = "⭐️" * score + f" <text_tag color='blue'>{score}分</text_tag>" if isinstance(score, int) else "N/A"
        
        card_data['data']['template_variable']['loop'].append({
            "paper": paper_formatted,
            "translation": translation,
            "score": score_formatted,
            "summary": summary
        })
        
    card = json.dumps(card_data)
    body = json.dumps({"msg_type": "interactive", "card": card})
    headers = {"Content-Type": "application/json"}
    
    # 循环发送到所有飞书URL
    for idx, url in enumerate(feishu_urls):
        try:
            # 设置超时时间为10秒
            ret = requests.post(url=url, data=body, headers=headers, timeout=10)
            print(f"✉️ 飞书推送[{idx+1}/{len(feishu_urls)}]返回状态: {ret.status_code}")
        except Exception as e:
            print(f"❌ 飞书推送[{idx+1}/{len(feishu_urls)}]失败: {e}")

def get_papers_from_all_categories():
    """从所有指定分类获取论文并初始化状态标记，去除与前一天重复的论文"""
    all_papers = {}
    
    # 获取当前脚本所在目录（paperBotV2目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取前一天的日期
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_file = os.path.join(current_dir, "data", f"{yesterday.strftime('%Y%m%d')}.json")
    
    # 读取前一天的论文ID集合（用于去重）
    yesterday_paper_ids = set()
    if os.path.exists(yesterday_file):
        try:
            with open(yesterday_file, 'r', encoding='utf-8') as f:
                yesterday_data = json.load(f)
                yesterday_paper_ids = set(yesterday_data.keys())
            print(f"📋 已加载前一天的论文ID集合，共 {len(yesterday_paper_ids)} 篇论文。")
        except Exception as e:
            print(f"❌ 读取前一天论文文件失败: {e}")
    
    # 获取当前日期的所有分类论文
    for index, category in enumerate(TARGET_CATEGORYS):
        category_results = load_today_cached_papers(category)
        if not category_results:
            for attempt in range(1, ARXIV_CATEGORY_RETRY_ATTEMPTS + 1):
                try:
                    category_results = get_daily_arxiv_papers(category=category, max_results=MAX_PAPERS)
                    break
                except ArxivFetchError as exc:
                    if attempt == ARXIV_CATEGORY_RETRY_ATTEMPTS:
                        raise
                    print(
                        f"⚠️ 分类 '{category}' 第 {attempt}/{ARXIV_CATEGORY_RETRY_ATTEMPTS} 次抓取失败: {exc}"
                    )
                    sleep_with_jitter(ARXIV_CATEGORY_INTERVAL, f"分类 '{category}' 失败后重试间隔")
        
        # 添加到all_papers并初始化状态标记，跳过与前一天重复的论文
        for arxiv_id, paper in category_results.items():
            if arxiv_id not in yesterday_paper_ids:
                paper['is_filtered'] = False  # 默认为未过滤
                paper['is_fine_ranked'] = False  # 默认为未精排
                all_papers[arxiv_id] = paper
        if index < len(TARGET_CATEGORYS) - 1:
            sleep_with_jitter(ARXIV_CATEGORY_INTERVAL, "分类之间请求间隔")
    
    print(f"📚 获取到 {len(all_papers)} 篇论文（已去除与前一天重复的论文）。")
    return all_papers


def perform_rough_ranking(all_papers):
    """执行粗排并标记过滤状态"""
    # 直接使用rough_rank_papers函数进行并发粗排，获取过滤后的论文
    filtered_papers = rough_rank_papers(all_papers, filter_threshold=ROUGH_SCORE_THRESHOLD, max_workers=10)
    
    # 更新all_papers中的论文信息并标记过滤状态
    for paper in filtered_papers:
        arxiv_id = paper['arxiv_id']
        all_papers[arxiv_id].update(paper)
        all_papers[arxiv_id]['is_filtered'] = False  # 通过粗排的论文
    
    # 标记未通过粗排的论文
    for arxiv_id, paper in all_papers.items():
        if arxiv_id not in [p['arxiv_id'] for p in filtered_papers]:
            all_papers[arxiv_id]['is_filtered'] = True  # 未通过粗排的论文
    
    print(f"✨ 粗排筛选 {len(filtered_papers)} 篇高质量论文。")
    return filtered_papers


def perform_fine_ranking(filtered_papers, all_papers):
    """执行精排并标记精排状态"""
    final_papers = fine_rank_papers(filtered_papers, paper_count=RETURN_PAPERS)
    
    for paper in final_papers:
        arxiv_id = paper['arxiv_id']
        all_papers[arxiv_id].update(paper)  # 更新精排信息
        all_papers[arxiv_id]['is_fine_ranked'] = True  # 标记为已精排
    
    print(f"🏆 精排得到 {len(final_papers)} 篇顶级论文。")
    return final_papers


def save_results_to_json(all_papers):
    """保存所有结果到指定路径的JSON文件，包括天级文件和全量文件"""
    # 如果没有新论文，直接返回
    if not all_papers:
        print("📭 今天没有新论文，跳过保存JSON文件")
        return
    
    # 获取当前脚本所在目录（paperBotV2/arxiv_daily目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 确保data目录存在于paperBotV2/arxiv_daily目录下
    save_dir = os.path.join(current_dir, "data")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 1. 保存当天的结果到日期格式的文件
    daily_file = os.path.join(save_dir, f"{datetime.now().strftime('%Y%m%d')}.json")
    with open(daily_file, 'w', encoding='utf-8') as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)
    
    print(f"💾 当天论文结果已保存到 {daily_file}")
    
    # 2. 保存/更新全量results.json文件
    all_results_file = os.path.join(save_dir, "results.json")
    
    # 读取已有全量结果（如果存在）
    all_results = {}
    if os.path.exists(all_results_file):
        try:
            with open(all_results_file, 'r', encoding='utf-8') as f:
                all_results = json.load(f)
            print(f"📋 已加载现有全量结果，共 {len(all_results)} 篇论文。")
        except Exception as e:
            print(f"❌ 读取全量结果文件失败: {e}")
    
    # 增量更新全量结果（使用arxiv_id作为唯一标识）
    new_papers_count = 0
    for arxiv_id, paper in all_papers.items():
        if arxiv_id not in all_results:
            all_results[arxiv_id] = paper
            new_papers_count += 1
    
    # 保存更新后的全量结果
    with open(all_results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"📊 全量结果已更新到 {all_results_file}，新增 {new_papers_count} 篇论文，总论文数: {len(all_results)}")


def process_papers():
    """处理并保存论文的主函数 - 协调各个子函数的执行"""
    # 1. 获取论文
    all_papers = get_papers_from_all_categories()
    
    # 2. 粗排
    filtered_papers = perform_rough_ranking(all_papers)
    
    # 3. 精排
    final_papers = perform_fine_ranking(filtered_papers, all_papers)
    
    # 4. 保存结果
    save_results_to_json(all_papers)
    
    print("✅ 论文处理流程已全部完成！")
    
    # 注意：飞书消息发送功能已移至独立脚本 send_feishu_message.py
    # 在GitHub Actions工作流中，将在网页生成完成后触发发送


# --- 主程序入口 ---
if __name__ == "__main__":
    process_papers()
