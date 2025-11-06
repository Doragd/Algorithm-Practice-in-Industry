

import json
import os
import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup
from tqdm import tqdm

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
}

# 数据文件路径（使用相对路径，提高可移植性）
RESULTS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'results.json')


# ========================== 通用工具函数 ==========================

def load_results(file_path: str) -> dict:
    """加载results.json文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"成功加载results.json，包含 {len(data)} 个会议")
        return data
    except Exception as e:
        print(f"加载results.json失败: {str(e)}")
        return {}


def save_results(data: dict, file_path: str) -> bool:
    """保存数据到results.json文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"成功保存results.json到 {file_path}")
        return True
    except Exception as e:
        print(f"保存results.json失败: {str(e)}")
        return False


def get_papers_with_empty_abstracts(results_data: dict, url_pattern_func, max_papers=None) -> list:
    """获取所有摘要为空且URL匹配特定模式的论文
    
    Args:
        results_data: 会议数据字典
        url_pattern_func: URL匹配函数
        max_papers: 限制返回的最大论文数量，None表示不限制
        
    Returns:
        论文对象和会议名称的元组列表
    """
    papers_to_process = []
    skipped_count = 0
    
    for conf_name, papers in results_data.items():
        for paper in papers:
            paper_url = paper.get('paper_url', '')
            paper_name = paper.get('paper_name', '').strip()
            
            # 过滤条件：
            # 1. URL需要匹配模式
            # 2. 摘要需要为空
            # 3. 论文名称不能仅包含'Frontmatter'，这通常不是真正的论文
            if (url_pattern_func(paper_url) and 
                not paper.get('paper_abstract', '').strip() and 
                paper_name.lower() != 'frontmatter'):
                papers_to_process.append((conf_name, paper))
                # 如果达到最大数量限制，就停止添加
                if max_papers is not None and len(papers_to_process) >= max_papers:
                    print(f"找到 {len(papers_to_process)} 篇符合条件的论文需要处理（限制为 {max_papers} 篇）")
                    print(f"跳过了 {skipped_count} 篇不符合条件的论文（如Frontmatter）")
                    return papers_to_process
            else:
                if url_pattern_func(paper_url) and not paper.get('paper_abstract', '').strip():
                    skipped_count += 1
    
    print(f"找到 {len(papers_to_process)} 篇符合条件的论文需要处理")
    print(f"跳过了 {skipped_count} 篇不符合条件的论文（如Frontmatter）")
    return papers_to_process


# ========================== ACL会议专用函数 ==========================

def is_acl_url(url: str) -> bool:
    """判断URL是否为ACL会议URL"""
    flag = False
    keywords = ['aclanthology', 'findings', 'acl', 'naacl', 'emnlp', 'conll']
    # 转换为小写以进行大小写不敏感匹配
    url_lower = url.lower()
    for keyword in keywords:
        if keyword.lower() in url_lower:
            flag = True
            break
    return flag


async def get_acl_abstract(session, url, max_retries=3, initial_delay=1):
    """从ACL页面获取摘要（异步版本）
    
    Args:
        session: aiohttp.ClientSession对象
        url: 论文URL
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        
    Returns:
        摘要文本，如果获取失败则返回None
    """
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as response:
                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # 获取摘要
                    abstract = soup.find("div", {"class": "acl-abstract"})
                    if abstract:
                        span = abstract.find("span")
                        if span:
                            return span.get_text().strip()
                    return None
                # 仅在最后一次重试失败时打印错误信息
                elif retry_count == max_retries:
                    print(f"[错误] 获取页面失败: {url}, 状态码: {response.status}")
        except Exception as e:
            # 仅在最后一次重试失败时打印错误信息
            if retry_count == max_retries:
                if isinstance(e, asyncio.TimeoutError):
                    print(f"[超时] {url}")
                elif isinstance(e, aiohttp.ClientError):
                    print(f"[客户端错误] {url}")
                else:
                    print(f"[未知错误] {url}: {str(e)}")
        
        retry_count += 1
        if retry_count <= max_retries:
            # 静默重试，不打印详细信息
            delay = initial_delay + random.uniform(0, 1)
            await asyncio.sleep(delay)
    
    return None


async def process_single_paper(session, conf_name, paper, sem):
    """处理单篇论文（ACL）
    
    Args:
        session: aiohttp.ClientSession对象
        conf_name: 会议名称
        paper: 论文对象
        sem: 信号量，控制并发
        
    Returns:
        (是否成功, 论文对象)
    """
    paper_url = paper.get('paper_url', '')
    
    # 检查会话是否已关闭
    if session.closed:
        # 静默创建新会话
        async with aiohttp.ClientSession() as new_session:
            async with sem:
                # 获取摘要
                abstract = await get_acl_abstract(new_session, paper_url)
                if abstract:
                    paper['paper_abstract'] = abstract
                    return True, paper
                return False, paper
    
    async with sem:
        # 获取摘要（静默执行）
        abstract = await get_acl_abstract(session, paper_url)
        if abstract:
            paper['paper_abstract'] = abstract
            return True, paper
        return False, paper


async def crawl_acl_abstracts(papers_to_process, threads=10):
    """并发爬取ACL论文摘要
    
    Args:
        papers_to_process: 论文对象和会议名称的元组列表
        threads: 并发线程数
        
    Returns:
        更新后的论文字典
    """
    updated_count = 0
    sem = asyncio.Semaphore(threads)  # 限制并发请求数
    total_papers = len(papers_to_process)
    
    print(f"准备处理 {total_papers} 篇论文，设置并发数为 {threads}")
    
    # 创建进度条，设置更友好的参数
    with tqdm(total=total_papers, desc="处理论文进度", dynamic_ncols=True, 
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
        # 分批处理论文
        batch_size = threads * 2  # 每批处理的论文数量
        
        # 为每批论文单独创建会话，避免会话长时间打开
        for i in range(0, total_papers, batch_size):
            # 获取当前批次的论文
            batch = papers_to_process[i:i+batch_size]
            
            async with aiohttp.ClientSession() as session:
                # 为当前批次的论文创建任务
                current_batch_tasks = [
                    process_single_paper(session, conf_name, paper, sem)
                    for conf_name, paper in batch
                ]
                
                # 并发处理当前批次
                results = await asyncio.gather(*current_batch_tasks)
                
                # 处理结果
                for success, _ in results:
                    if success:
                        updated_count += 1
                    pbar.update(1)
                
                # 每批次处理后短暂暂停，避免请求过于频繁
                if i + batch_size < total_papers:
                    await asyncio.sleep(random.uniform(1, 2))
    
    print(f"处理完成，成功更新 {updated_count} 篇论文摘要")
    return updated_count


# ========================== 主函数 ==========================

async def process_abstracts(results_data, url_pattern_func=is_acl_url, threads=10, max_papers=None):
    """处理摘要的主函数（可扩展支持其他会议）
    
    Args:
        results_data: 会议数据字典
        url_pattern_func: URL匹配函数
        threads: 并发线程数
        max_papers: 限制处理的最大论文数量，None表示不限制
        
    Returns:
        更新的论文数量
    """
    # 获取需要处理的论文
    papers_to_process = get_papers_with_empty_abstracts(results_data, url_pattern_func, max_papers)
    
    if not papers_to_process:
        print("没有需要处理的论文")
        return 0
    
    # 目前仅支持ACL，后续可以根据URL模式选择不同的处理函数
    # 例如：if is_acl_url == url_pattern_func: 处理ACL
    #      elif is_other_conf_url == url_pattern_func: 处理其他会议
    
    # 处理ACL论文
    updated_count = await crawl_acl_abstracts(papers_to_process, threads)
    
    return updated_count


def main(
    file_path=RESULTS_FILE_PATH,
    threads=10,
    conf_type="acl",  # 可以是 'acl', 'all' 或其他自定义类型
    max_papers=None  # 限制处理的最大论文数量，None表示处理所有论文
):
    """主函数
    
    Args:
        file_path: 数据文件路径
        threads: 并发线程数
        conf_type: 会议类型，'acl'表示仅处理ACL会议
        max_papers: 限制处理的最大论文数量，None表示处理所有论文
    """
    # 加载数据
    results_data = load_results(file_path)
    if not results_data:
        print("没有数据可处理")
        return
    
    # 根据会议类型选择处理函数
    url_pattern_func = is_acl_url  # 默认处理ACL会议
    
    # 执行异步处理
    print(f"开始处理 {conf_type.upper()} 会议论文摘要")
    print(f"并发线程数: {threads}")
    if max_papers:
        print(f"限制处理论文数量: {max_papers}")
    
    updated_count = asyncio.run(process_abstracts(results_data, url_pattern_func, threads, max_papers))
    
    # 如果有更新，则保存结果
    if updated_count > 0:
        save_results(results_data, file_path)
    else:
        print("没有更新任何论文摘要，无需保存")


if __name__ == "__main__":
    # 添加请求头轮换，模拟不同浏览器
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    
    # 选择随机User-Agent
    HEADERS["User-Agent"] = random.choice(user_agents)
    print(f"使用User-Agent: {HEADERS['User-Agent']}")
    
    # 执行主函数
    main(threads=50, max_papers=1000)
