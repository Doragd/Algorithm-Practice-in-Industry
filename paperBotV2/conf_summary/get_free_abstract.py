

import json
import os
import asyncio
import aiohttp
import random
import argparse
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


def is_supported_conf(conf_name: str) -> bool:
    """检查会议类型是否支持（ICLR或ACL）"""
    return is_iclr_conf(conf_name) or is_acl_conf(conf_name)


def get_papers_with_empty_abstracts(results_data: dict, conf_pattern_func=None, max_papers=None) -> list:
    """获取所有摘要为空且会议类型支持的论文
    
    Args:
        results_data: 会议数据字典
        conf_pattern_func: 会议名称匹配函数，None表示处理所有会议
        max_papers: 限制返回的最大论文数量，None表示不限制
        
    Returns:
        论文对象和会议名称的元组列表
    """
    papers_to_process = []
    skipped_count = 0
    unsupported_conf_count = 0
    
    for conf_name, papers in results_data.items():
        # 如果提供了会议名称匹配函数，则只处理匹配的会议
        if conf_pattern_func and not conf_pattern_func(conf_name):
            continue
        
        # 检查会议类型是否支持（仅ICLR或ACL）
        if not is_supported_conf(conf_name):
            unsupported_conf_count += len(papers)
            continue
            
        for paper in papers:
            paper_name = paper.get('paper_name', '').strip()
            
            # 过滤条件：
            # 1. 摘要需要为空
            # 2. 论文名称不能仅包含'Frontmatter'，这通常不是真正的论文
            if (not paper.get('paper_abstract', '').strip() and 
                paper_name.lower() != 'frontmatter'):
                papers_to_process.append((conf_name, paper))
                # 如果达到最大数量限制，就停止添加
                if max_papers is not None and len(papers_to_process) >= max_papers:
                    print(f"找到 {len(papers_to_process)} 篇符合条件的论文需要处理（限制为 {max_papers} 篇）")
                    print(f"跳过了 {skipped_count} 篇不符合条件的论文（如Frontmatter）")
                    print(f"跳过了 {unsupported_conf_count} 篇不支持的会议类型的论文")
                    return papers_to_process
            else:
                if not paper.get('paper_abstract', '').strip():
                    skipped_count += 1
    
    print(f"找到 {len(papers_to_process)} 篇符合条件的论文需要处理")
    print(f"跳过了 {skipped_count} 篇不符合条件的论文（如Frontmatter）")
    print(f"跳过了 {unsupported_conf_count} 篇不支持的会议类型的论文")
    return papers_to_process


# ========================== ACL会议专用函数 ==========================

def is_acl_conf(conf_name: str) -> bool:
    """判断会议名称是否为ACL系列会议"""
    # 转换为小写以进行大小写不敏感匹配
    conf_lower = conf_name.lower()
    # ACL系列会议通常包含以下关键词
    acl_keywords = ['acl', 'naacl', 'emnlp', 'conll', 'findings', 'semeval', 'eacl', 'coling']
    for keyword in acl_keywords:
        if keyword in conf_lower:
            return True
    return False

def is_iclr_conf(conf_name: str) -> bool:
    """判断会议名称是否为ICLR会议"""
    return 'iclr' in conf_name.lower()


async def get_acl_abstract(session, url, max_retries=3, initial_delay=1):
    """从ACL页面获取摘要（异步版本）
    
    Args:
        session: aiohttp.ClientSession对象
        url: 论文URL
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        
    Returns:
        (摘要文本, 错误信息)：如果成功，错误信息为None；如果失败，错误信息包含状态码或异常信息
    """
    retry_count = 0
    last_error = None
    
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
                            return span.get_text().strip(), None
                    return None, "未找到摘要内容"
                else:
                    last_error = f"状态码: {response.status}"
                    # 仅在最后一次重试失败时打印错误信息
                    if retry_count == max_retries:
                        print(f"[错误] 获取页面失败: {url}, 状态码: {response.status}")
        except Exception as e:
            if isinstance(e, asyncio.TimeoutError):
                last_error = "超时"
                if retry_count == max_retries:
                    print(f"[超时] {url}")
            elif isinstance(e, aiohttp.ClientError):
                last_error = f"客户端错误: {str(e)}"
                if retry_count == max_retries:
                    print(f"[客户端错误] {url}")
            else:
                last_error = f"未知错误: {str(e)}"
                if retry_count == max_retries:
                    print(f"[未知错误] {url}: {str(e)}")
        
        retry_count += 1
        if retry_count <= max_retries:
            # 静默重试，不打印详细信息
            delay = initial_delay + random.uniform(0, 1)
            await asyncio.sleep(delay)
    
    return None, last_error

async def get_iclr_abstract(session, url, max_retries=3, initial_delay=1):
    """从ICLR页面获取摘要（异步版本）
    
    Args:
        session: aiohttp.ClientSession对象
        url: 论文URL
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        
    Returns:
        (摘要文本, 错误信息)：如果成功，错误信息为None；如果失败，错误信息包含状态码或异常信息
    """
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as response:
                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # 从meta标签中提取摘要
                    meta_abstract = soup.find("meta", {"name": "citation_abstract"})
                    if meta_abstract and meta_abstract.get("content"):
                        return meta_abstract["content"].strip(), None
                    
                    return None, "未找到摘要内容"
                else:
                    last_error = f"状态码: {response.status}"
                    # 仅在最后一次重试失败时打印错误信息
                    if retry_count == max_retries:
                        print(f"[错误] 获取ICLR页面失败: {url}, 状态码: {response.status}")
        except Exception as e:
            if isinstance(e, asyncio.TimeoutError):
                last_error = "超时"
                if retry_count == max_retries:
                    print(f"[超时] {url}")
            elif isinstance(e, aiohttp.ClientError):
                last_error = f"客户端错误: {str(e)}"
                if retry_count == max_retries:
                    print(f"[客户端错误] {url}")
            else:
                last_error = f"未知错误: {str(e)}"
                if retry_count == max_retries:
                    print(f"[未知错误] {url}: {str(e)}")
        
        retry_count += 1
        if retry_count <= max_retries:
            # 静默重试，不打印详细信息
            delay = initial_delay + random.uniform(0, 1)
            await asyncio.sleep(delay)
    
    return None, last_error


async def process_single_paper(session, conf_name, paper, sem, save_to_file=False):
    """处理单篇论文（支持ACL和ICLR）
    
    Args:
        session: aiohttp.ClientSession对象
        conf_name: 会议名称
        paper: 论文对象
        sem: 信号量，控制并发
        save_to_file: 是否保存结果到文件，测试时可设为False
        
    Returns:
        (是否成功, 论文对象, 失败原因)
    """
    # 获取论文URL
    paper_url = paper.get('paper_url', '')
    
    # 根据会议名称选择适当的摘要获取函数
    # 由于在get_papers_with_empty_abstracts中已经进行了支持类型的筛选，这里只需要判断是ICLR还是ACL
    if is_iclr_conf(conf_name):
        get_abstract_func = get_iclr_abstract
        conf_type = "ICLR"
    else:  # 因为已经筛选过，这里必然是ACL类型
        get_abstract_func = get_acl_abstract
        conf_type = "ACL"
    
    # 检查会话是否已关闭
    if session.closed:
        # 创建新会话
        async with aiohttp.ClientSession() as new_session:
            async with sem:
                # 获取摘要
                abstract, error = await get_abstract_func(new_session, paper_url)
                if abstract:
                    # 测试模式下只输出摘要长度和会议名
                    if not save_to_file:
                        print(f"会议: {conf_name} - 摘要长度: {len(abstract)} 字符")
                    paper['paper_abstract'] = abstract
                    return True, paper, None
                return False, paper, f"{conf_type}摘要获取失败（会话已关闭）: {error}"
    
    async with sem:
        # 获取摘要
        abstract, error = await get_abstract_func(session, paper_url)
        if abstract:
            # 测试模式下只输出摘要长度和会议名
            if not save_to_file:
                print(f"会议: {conf_name} - 摘要长度: {len(abstract)} 字符")
            paper['paper_abstract'] = abstract
            return True, paper, None
        return False, paper, f"{conf_type}摘要获取失败: {error}"

async def crawl_papers_abstracts(papers_to_process, threads=10, save_to_file=False):
    """并发爬取论文摘要（支持ACL和ICLR）
    
    Args:
        papers_to_process: 论文对象和会议名称的元组列表
        threads: 并发线程数
        save_to_file: 是否保存结果到文件，测试时可设为False
        
    Returns:
        更新后的论文字典
    """
    updated_count = 0
    sem = asyncio.Semaphore(threads)  # 限制并发请求数
    total_papers = len(papers_to_process)
    failure_reasons = {}
    failed_papers = []
    
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
                    process_single_paper(session, conf_name, paper, sem, save_to_file)
                    for conf_name, paper in batch
                ]
                
                # 并发处理当前批次
                results = await asyncio.gather(*current_batch_tasks)
                
                # 处理结果
                for idx, (success, paper, reason) in enumerate(results):
                    conf_name, original_paper = batch[idx]
                    if success:
                        updated_count += 1
                        # 更新原始论文对象
                        original_paper.update(paper)
                    else:
                        # 记录失败原因和论文信息
                        paper_name = paper.get('paper_name', 'Unknown')
                        failed_papers.append((conf_name, paper_name))
                        # 统计失败原因
                        if reason not in failure_reasons:
                            failure_reasons[reason] = 0
                        failure_reasons[reason] += 1
                    pbar.update(1)  # 进度条更新所有尝试处理的论文，无论成功与否
                
                # 每批次处理后短暂暂停，避免请求过于频繁
                if i + batch_size < total_papers:
                    await asyncio.sleep(random.uniform(1, 2))
    
    print(f"处理完成，成功更新 {updated_count} 篇论文摘要")
    
    # 打印失败统计
    if failure_reasons:
        print("\n错误统计：")
        # 添加错误码和详细分类
        for idx, (reason, count) in enumerate(failure_reasons.items(), 1):
            print(f"  错误 {idx}: {reason} - 发生次数: {count}")
        
        # 统计总失败数
        total_failures = sum(failure_reasons.values())
        print(f"\n总失败次数: {total_failures}")
    
    return updated_count


# ========================== 主函数 ==========================

async def process_abstracts(results_data, conf_pattern_func=None, threads=10, max_papers=None, save_to_file=False):
    """处理摘要的主函数（支持ACL和ICLR）
    
    Args:
        results_data: 会议数据字典
        conf_pattern_func: 会议名称匹配函数，None表示处理所有会议
        threads: 并发线程数
        max_papers: 限制处理的最大论文数量，None表示不限制
        save_to_file: 是否保存结果到文件，测试时可设为False
        
    Returns:
        更新的论文数量
    """
    # 获取需要处理的论文
    papers_to_process = get_papers_with_empty_abstracts(results_data, conf_pattern_func, max_papers)
    
    if not papers_to_process:
        print("没有需要处理的论文")
        return 0
    
    # 调用通用的摘要爬取函数
    updated_count = await crawl_papers_abstracts(papers_to_process, threads, save_to_file)
    
    return updated_count


def main(
    file_path=RESULTS_FILE_PATH,
    threads=10,
    conf_type=None,  # 可以是 'acl', 'iclr', 'all' 或None（自动检测）
    max_papers=None,  # 限制处理的最大论文数量，None表示处理所有论文
    save_to_file=True  # 是否保存结果到文件，测试时可设为False
):
    """主函数
    
    Args:
        file_path: 数据文件路径
        threads: 并发线程数
        conf_type: 会议类型，None表示自动检测，'acl'表示仅处理ACL会议，'iclr'表示仅处理ICLR会议
        max_papers: 限制处理的最大论文数量，None表示处理所有论文
        save_to_file: 是否保存结果到文件，测试时可设为False
    """
    # 加载数据
    results_data = load_results(file_path)
    if not results_data:
        print("没有数据可处理")
        return
    
    # 根据会议类型选择匹配函数
    if conf_type and conf_type.lower() == "iclr":
        conf_pattern_func = is_iclr_conf
        print(f"开始处理ICLR会议论文摘要")
    elif conf_type and conf_type.lower() == "acl":
        conf_pattern_func = is_acl_conf
        print(f"开始处理ACL系列会议论文摘要")
    else:  # None或"all"或其他类型
        conf_pattern_func = None  # None表示处理所有会议，会自动检测每个会议类型
        print(f"开始处理所有会议论文摘要，将自动检测会议类型")
    
    print(f"并发线程数: {threads}")
    if max_papers:
        print(f"限制处理论文数量: {max_papers}")
    
    # 显示是否保存结果的设置
    if save_to_file:
        print(f"结果将保存到: {file_path}")
    else:
        print("结果不会保存到文件（测试模式）")
    
    updated_count = asyncio.run(process_abstracts(results_data, conf_pattern_func, threads, max_papers, save_to_file))
    
    # 如果有更新且允许保存，则保存结果
    if updated_count > 0:
        if save_to_file:
            save_results(results_data, file_path)
        else:
            print(f"成功处理了 {updated_count} 篇论文，但由于save_to_file=False，结果未保存")
    else:
        print("没有更新任何论文摘要，无需保存")


def parse_args():
    """解析命令行参数
    
    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(description='从论文会议网站爬取免费摘要')
    parser.add_argument('--threads', type=int, default=50, help='并发线程数')
    parser.add_argument('--conf-type', type=str, default='acl', choices=['acl', 'iclr', 'all'],
                        help='会议类型，默认为None（自动检测）')
    parser.add_argument('--max-papers', type=int, default=1000, help='最大处理论文数量')
    parser.add_argument('--save-to-file', action='store_true', help='是否保存结果到文件（默认不保存）')
    parser.add_argument('--file-path', type=str, default=RESULTS_FILE_PATH, help='结果保存文件路径')
    return parser.parse_args()

# 主函数调用
if __name__ == '__main__':
    # 解析命令行参数
    args = parse_args()
    
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
    
    # 执行主函数，使用命令行参数
    main(
        file_path=args.file_path,
        threads=args.threads,
        conf_type=args.conf_type,
        max_papers=args.max_papers,
        save_to_file=True
    )
