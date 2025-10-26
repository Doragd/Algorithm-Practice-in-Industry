import json
import os
import re
import requests
import tqdm
import concurrent.futures
import asyncio
import aiohttp
import random
import time
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
}


def get_soup(conf):
    url = f'https://dblp.org/db/conf/{conf}/index.html'
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        print(
            f"Error: Failed to fetch {conf} with status code {r.status_code}")
        return None
    return conf, BeautifulSoup(r.text, "html.parser")


def get_links(results, confs, filter_keywords=[], start_year=2012):
    rsp_soup = []
    links_all = []

    existing_confs = list(results.keys())

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_soup, conf) for conf in confs]
        for future in concurrent.futures.as_completed(futures):
            soup = future.result()
            if soup is not None:
                rsp_soup.append(soup)

    for conf, soup in rsp_soup:
        links = [
            [conf + re.search(r'\d{4}', item['href']).group(), item['href']] for item in soup.find_all(class_='toc-link')
            if re.search(r'\d{4}', item['href'])
            and int(re.search(r'\d{4}', item['href']).group()) >= start_year
            and (f'{conf}/{conf}' in item['href'] or 'nips/neurips' in item['href'])
            and all(keyword not in item['href'] for keyword in filter_keywords)
            and conf + re.search(r'\d{4}', item['href']).group() not in existing_confs
        ]
        links_all.extend(links)

    return links_all


async def clean_author_name(author):
    return re.sub(r'\d+|-', '', author['title']).strip()


async def search_paper_info(session, paper_item):
    filter_keywords = ['Virtual Event', 'Proceedings', 
        'International Conference', 'Advances in Information Retrieval',
        'SIGIR Conference', 'Workshop', 'tutorial', 'The Web Conference ', 
        'ACM SIGKDD Conference', 'International World Wide Web', 'ACM Conference on Recommender Systems']
    try:
        paper_url = paper_item.find("li", class_="drop-down").div.a["href"]
        paper_name = paper_item.find(class_="title", itemprop="name")

        paper_authors = [
            await clean_author_name(author)
            for author in paper_item.find_all(class_=None, itemprop="name") if author.has_attr("title")]

        paper_title = "".join(
            [item.string if item.string else item for item in paper_name.contents])
        if paper_title[-1] == ".":
            paper_title = paper_title[:-1]
        if any(keyword in paper_title for keyword in filter_keywords):
            return None
        return {
            "paper_name": paper_title,
            "paper_url": paper_url,
            "paper_authors": paper_authors,
            "paper_abstract": "",
            "authors_detail": [],
            "abstract_translation": "",
            "title_translation": "",
            "relevance_score": 0,
            "reasoning": ""
        }
    except Exception as e:
        print(f"Error occurred while searching paper info: {e}")
        return None


async def search_from_dblp(session, url, name, results, sem, max_retries=3, initial_delay=2):
    """
    从dblp页面爬取多篇论文信息，支持失败重试
    
    Args:
        session: aiohttp.ClientSession对象
        url: 要爬取的页面URL
        name: 会议名称+年份
        results: 存储结果的字典
        sem: 信号量，用于限制并发
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        
    Returns:
        更新后的results字典
    """
    if name in results:
        print(f"Skipping {name} as it already exists in results")
        return results
    
    print(f"Starting to crawl {name} from {url}")
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            async with sem:
                # 减少超时时间以加快失败检测
                async with session.get(url, timeout=15) as response:
                    print(f"Received response for {name}: status {response.status}")
                    if response.status == 200:
                        html_content = await response.text()
                        print(f"Parsing HTML for {name}...")
                        dblp_soup = BeautifulSoup(html_content, "html.parser")

                        if name not in results:
                            results[name] = []

                        # 直接处理论文项，不使用额外的异步任务
                        paper_count = 0
                        for paper_item in dblp_soup.find_all("li", class_="entry"):
                            paper_info = await search_paper_info(session, paper_item)
                            if paper_info is not None:
                                results[name].append(paper_info)
                                paper_count += 1

                        print(f"Successfully crawled {paper_count} papers for {name}")
                        return results
                    else:
                        print(f"Error: Failed to fetch {url} with status code {response.status}. Attempt {retry_count+1}/{max_retries+1}")
        except aiohttp.ClientError as e:
            print(f"Error fetching {url}: {str(e)}. Attempt {retry_count+1}/{max_retries+1}")
        except asyncio.TimeoutError:
            print(f"Timeout error fetching {url}. Attempt {retry_count+1}/{max_retries+1}")
        except Exception as e:
            print(f"Unexpected error fetching {url}: {str(e)}. Attempt {retry_count+1}/{max_retries+1}")
        
        retry_count += 1
        if retry_count <= max_retries:
            # 使用更简单的延迟策略
            delay = initial_delay + random.uniform(0, 1)
            print(f"Retrying {url} in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
    
    print(f"Failed to fetch {url} after {max_retries+1} attempts")
    return results


async def crawl(urls, names, results, threads, max_retries=3, initial_delay=2):
    """
    异步并发爬取多个会议页面，添加失败重试和延迟策略
    
    Args:
        urls: URL列表
        names: 会议名称+年份列表
        results: 存储结果的字典
        threads: 并发线程数
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        
    Returns:
        更新后的results字典
    """
    print(f"Starting to crawl {len(urls)} URLs with {threads} concurrent connections")
    
    # 创建并立即执行所有任务，不等待完成
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        sem = asyncio.Semaphore(threads)  # 限制并发请求数
        
        # 使用更高效的方式创建和执行任务
        async def create_task_with_delay(url, name):
            # 添加随机延迟
            await asyncio.sleep(random.uniform(0, 0.3))
            return await search_from_dblp(session, url, name, results, sem, max_retries, initial_delay)
        
        # 并行执行所有任务
        tasks = [create_task_with_delay(url, name) for url, name in zip(urls, names)]
        
        # 使用tqdm显示进度
        print(f"Created {len(tasks)} tasks. Starting execution...")
        
        # 使用gather直接收集所有结果
        await asyncio.gather(*tasks)
        
    print(f"Completed crawling {len(urls)} URLs")
    return results


def load_results(filename='results.json'):
    if not os.path.exists(filename):
        return {}
    return json.load(open(filename, 'r'))


def save_results(results, filename='results.json'):
    try:
        json.dump(results, open(filename, 'w'), indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error: Failed to save results to {filename}: {e}")

def filter_results(results):
    for conf in results:
        results[conf] = [
            paper_item for paper_item in results[conf] if paper_item is not None]
    return results

def run_all(
    # no need to crawl for coling, aaai and ijcai
    confs=['www', 'kdd', 'cikm', 'sigir', 'wsdm', 'ecir', 'recsys', 'nips','icml', 'iclr', 'acl', 'emnlp', 'naacl'],
    filter_keywords=['kddcup', 'w.html', 'lbr.html'],
    start_year=2020,
    filename='data/results.json',
    writename='data/results.json',
    threads=20,  # 增加并发数，提高爬取速度
    max_retries=2,  # 减少重试次数
    initial_delay=1  # 减少初始延迟时间
):
    """
    协调整个爬取流程，添加失败重试和延迟策略
    
    Args:
        confs: 要爬取的会议列表
        filter_keywords: 需要过滤的关键词
        start_year: 开始年份
        filename: 输入文件名
        writename: 输出文件名
        threads: 并发线程数
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间
    """
    results = load_results(filename)
    print(f"Loaded existing results from {filename}")
    
    # 添加请求头轮换，模拟不同浏览器
    global HEADERS
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    
    # 选择随机User-Agent
    HEADERS["User-Agent"] = random.choice(user_agents)
    print(f"Using User-Agent: {HEADERS['User-Agent']}")
    
    # 获取会议链接
    links = get_links(results, confs, filter_keywords, start_year)
    
    if len(links) > 0:
        names, urls = zip(*links)
        print(f'Found {len(links)} papers to crawl')
        
        # 增加批次大小以减少批次数量
        batch_size = 20  # 增加每批处理的论文数
        total_batches = (len(urls) + batch_size - 1) // batch_size
        
        # 使用tqdm显示整体进度
        with tqdm.tqdm(total=len(urls), desc="Overall Progress") as pbar:
            for i in range(0, len(urls), batch_size):
                batch_end = min(i + batch_size, len(urls))
                batch_urls = urls[i:batch_end]
                batch_names = names[i:batch_end]
                
                print(f'\nProcessing batch {i//batch_size + 1}/{total_batches}: {len(batch_urls)} papers')
                
                # 爬取当前批次
                results = asyncio.run(crawl(batch_urls, batch_names, results, threads, max_retries, initial_delay))
                
                # 更新整体进度条
                pbar.update(len(batch_urls))
                
                # 完全移除批次间延迟以加快速度
                if batch_end < len(urls):
                    print(f"Completed batch. Moving to next batch immediately...")
    else:
        print("No new papers found to crawl")
    
    results = filter_results(results)
    save_results(results, writename)
    print(f"Results saved to {writename}")


if __name__ == '__main__':
    run_all()