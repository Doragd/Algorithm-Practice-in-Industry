import re
import os
import requests
import json
import time
import feedparser
from openai import OpenAI
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_random_exponential
from openai import APIConnectionError, RateLimitError, APIStatusError

PRERANK_PROMPT = """
# Role
You are a highly experienced Research Engineer specializing in Large Language Models (LLMs) and Large-Scale Recommendation Systems, with deep knowledge of the search, recommendation, and advertising domains.

# My Current Focus

- **Core Domain Advances:** Core advances within RecSys, Search, or Ads itself, even if they do not involve LLMs.
- **Enabling LLM Tech:** Trends and Foundational progress in the core LLM which must have potential applications in RecSys, Search or Ads.
- **Enabling Transformer Tech: Advances in Transformer architecture (e.g., efficiency, new attention mechanisms, MoE, etc.).
- **Direct LLM Applications:* Novel ideas and direct applications of LLM technology for RecSys, Search or Ads.
- **VLM Analogy for Heterogeneous Data:** Ideas inspired by **Vision-Language Models** that treat heterogeneous data (like context features and user sequences) as distinct modalities for unified modeling. 

# Irrelevant Topics
- Federated learning, Security, Privacy, Fairness, Ethics, or other non-technical topics
- Medical, Biology, Chemistry, Physics or other domain-specific applications
- Neural Architectures Search (NAS) or general AutoML
- Purely theoretical papers without clear practical implications
- Hallucination, Evaluation benchmarks, or other purely NLP-centric topics
- Purely Vision、3D Vision, Graphic or Speech papers without clear relevance to RecSys/Search/Ads
- Ads creative generation, auction, bidding or other Non-Ranking Ads topics 
- AIGC, Content generation, Summarization, or other purely LLM-centric topics
- Reinforcement Learning (RL) papers without clear relevance to RecSys/Search/Ads

# Goal
Screen new papers based on my focus. DO NOT include irrelevant topics.

# Task
Based ONLY on the paper's title, provide a quick evaluation.
1. **Academic Translation**: Translate the title into professional Chinese, prioritizing accurate technical terms and faithful meaning.
2. **Relevance Score (1-10)**: How relevant is it to **My Current Focus**?
3. **Reasoning**: A 2-3 sentence explanation for your score. **For "Enabling Tech" papers, you MUST explain their potential application in RecSys/Search/Ads.**

# Input Paper
- **Title**: {title}

# Output Format
Provide your analysis strictly in the following JSON format.
{{
  "translation": "...",
  "relevance_score": <integer>,
  "reasoning": "..."
}}
"""

FINERANK_PROMPT = """
# Role
You are a highly experienced Research Engineer specializing in Large Language Models (LLMs) and Large-Scale Recommendation Systems, with deep knowledge of the search, recommendation, and advertising domains.

# My Current Focus

- **Core Domain Advances:** Core advances within RecSys, Search, or Ads itself, even if they do not involve LLMs.
- **Enabling LLM Tech:** Trends and Foundational progress in the core LLM which must have potential applications in RecSys, Search or Ads.
- **Enabling Transformer Tech: Advances in Transformer architecture (e.g., efficiency, new attention mechanisms, MoE, etc.).
- **Direct LLM Applications:* Novel ideas and direct applications of LLM technology for RecSys, Search or Ads.
- **VLM Analogy for Heterogeneous Data:** Ideas inspired by **Vision-Language Models** that treat heterogeneous data (like context features and user sequences) as distinct modalities for unified modeling. 

# Goal
Perform a detailed analysis of the provided paper based on its title and abstract. Identify its core contributions and relevance to my focus areas.

# Task
Based on the paper's **Title** and **Abstract**, provide a comprehensive analysis.
1.  **Relevance Score (1-10)**: Re-evaluate the relevance score (1-10) based on the detailed information in the abstract.
2.  **Reasoning**: A 2-3 sentence explanation for your score in Chinese.
3.  **Summary**: Distill the abstract into a high-density summary of no more than 150 Chinese words, prioritizing accurate technical terms and faithful meaning.

# Input Paper
- **Title**: {title}
- **Abstract**: {summary}

# Output Format
Provide your analysis strictly in the following JSON format.
{{
  "rerank_relevance_score": <integer>,
  "rerank_reasoning": "...",
  "summary": "..."
}}
"""

FEISHU_URL = os.environ.get("FEISHU_URL", None)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", None)
TARGET_CATEGORYS = ['cs.IR']
MAX_PAPERS = 100

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
        print("错误：API Key 未提供。请设置 DEEPSEEK_API_KEY 环境变量或通过参数传入。")
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
        print(f"API 遇到可重试错误: {e}。正在由 tenacity 进行重试...")
        raise  # 必须重新抛出异常，tenacity 才能捕获并执行重试策略
    except ImportError:
        print("错误：'openai' 库未安装。请运行 'pip install openai'。")
        return None
    except Exception as e:
        print(f"调用 API 时发生错误: {e}")
        return None


def get_daily_arxiv_papers(category='cs.CL', max_results=20):
    """
    获取指定 arXiv 领域今天发布的论文。

    Args:
        category (str): 你感兴趣的 arXiv 类别，例如 'cs.CL', 'cs.AI', 'stat.ML'。
        max_results (int): 希望获取的最大论文数量。
    """
    # 0. results json
    results = {}

    # 1. 构建 API 请求 URL
    base_url = 'http://export.arxiv.org/api/query?'

    # 2. 定义搜索参数
    # 获取今天的日期范围（考虑到 UTC 时间）
    # arXiv 的服务器在美国东部，但 API 通常使用 UTC 时间
    today_utc = datetime.now(timezone.utc)
    start_of_day = today_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    # 格式化为 API 需要的 YYYYMMDDHHMMSS 格式
    # 为了确保能抓取到今天发布的所有论文，我们可以把范围稍微放宽一点
    # 比如从昨天晚上到今天晚上
    yesterday_utc = start_of_day - timedelta(days=1)
    start_date_str = yesterday_utc.strftime('%Y%m%d%H%M%S')
    end_date_str = today_utc.strftime('%Y%m%d%H%M%S')

    # 构建 search_query
    # 语法: cat:cs.CL AND submittedDate:[YYYYMMDDHHMMSS TO YYYYMMDDHHMMSS]
    search_query = f'cat:{category} AND submittedDate:[{start_date_str} TO {end_date_str}]'

    query_params = {
        'search_query': search_query,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending',
        'start': 0,
        'max_results': max_results
    }

    # 3. 发送请求并获取数据
    try:
        response = requests.get(base_url, params=query_params)
        response.raise_for_status()  # 如果请求失败 (例如 404, 500), 会抛出异常
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return {}

    # 4. 使用 feedparser 解析返回的 XML 数据
    feed = feedparser.parse(response.content)

    # 5. 打印论文信息
    print(f"🔍 在分类 '{category}' 中找到 {len(feed.entries)} 篇今天更新的论文：")
    print("=" * 50)

    if not feed.entries:
        print("今天还没有新论文，或者查询范围有误。")
        return {}

    for i, entry in enumerate(feed.entries):
        # 提取核心信息
        title = re.sub(r'\s+', ' ', entry.title.replace('\n', ' ').strip())
        arxiv_id = entry.id.split('/abs/')[-1]
        alphaxiv_link = f"https://www.alphaxiv.org/abs/{arxiv_id}"
        authors = ', '.join(author.name for author in entry.authors)
        summary = re.sub(r'\s+', ' ', entry.summary.replace('\n', ' ').strip())
        published_date = entry.published_parsed
        published_str = datetime(
            *published_date[:6]).strftime('%Y-%m-%d %H:%M:%S')
        categories = ', '.join(tag.term for tag in entry.tags)

        results[arxiv_id] = {
            'title': title,
            'url': alphaxiv_link,
            'arxiv_id': arxiv_id,
            'authors': authors,
            'categories': categories,
            'pub_date': published_str,
            'summary': summary
        }

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
                print(f"处理论文 {paper_info['title']} 时产生异常: {exc}")
    if not analyzed_papers:
        print("\n没有成功分析任何论文。")
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
        title=paper['title'], summary=paper['summary'])
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
        print(f"  - 摘要: {paper.get('summary', 'N/A')}")
    print("-" * 60)

    return analyzed_papers


def send_papers_to_feishu(papers, feishu_url=FEISHU_URL):
    
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
        
        paper = f"[{title}]({url})"
        score = "⭐️" * score + f" <text_tag color='blue'>{score}分</text_tag>" if isinstance(score, int) else "N/A"
        
        card_data['data']['template_variable']['loop'].append({
            "paper": paper,
            "translation": translation,
            "score": score,
            "summary": summary
        })
        
    card = json.dumps(card_data)
    body = json.dumps({"msg_type": "interactive", "card": card})
    headers = {"Content-Type": "application/json"}
    ret = requests.post(url=feishu_url, data=body, headers=headers)
    print(f"飞书推送返回状态: {ret.status_code}")


# --- 主程序入口 ---
if __name__ == "__main__":
    results = {}
    for TARGET_CATEGORY in TARGET_CATEGORYS:
        results.update(get_daily_arxiv_papers(
            category=TARGET_CATEGORY, max_results=MAX_PAPERS))
        time.sleep(3)  # 避免请求过于频繁
    print(f"召回到 {len(results)} 篇论文。")

    filtered_papers = rough_rank_papers(results, filter_threshold=4)
    print(f"粗排筛选 {len(filtered_papers)} 篇高质量论文。")

    final_papers = fine_rank_papers(filtered_papers, paper_count=20)
    print(f"精排得到 {len(final_papers)} 篇顶级论文。")

    send_papers_to_feishu(final_papers)
    
    print("所有操作完成！")