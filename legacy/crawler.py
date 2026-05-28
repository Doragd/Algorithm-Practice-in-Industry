import json
import os
import re
import requests
import tqdm
import concurrent.futures
import asyncio
import aiohttp
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
            and f'{conf}/{conf}' in item['href']
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
            "paper_abstract": '',
            "paper_code": "#",
            "paper_cite": -1,
        }
    except Exception as e:
        print(f"Error occurred while searching paper info: {e}")
        return None


async def search_from_dblp(session, url, name, results, sem):
    if name in results:
        return results
    try:
        async with sem:
            async with session.get(url) as response:
                if response.status != 200:
                    print(
                        f"Error: Failed to fetch {url} with status code {response.status}")
                    return results

                dblp_soup = BeautifulSoup(await response.text(), "html.parser")

                if name not in results:
                    results[name] = []

                tasks = []
                for paper_item in dblp_soup.find_all("li", class_="entry"):
                    ret = search_paper_info(session, paper_item)
                    if ret is not None:
                        tasks.append(ret)

                results[name].extend(await asyncio.gather(*tasks))
    except aiohttp.ClientError as e:
        print(f"Error: {e} at url: {url}")
    return results


async def crawl(urls, names, results, threads):
    tasks = []
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        sem = asyncio.Semaphore(threads)  # Limits concurrent requests to 10
        for url, name in zip(urls, names):
            tasks.append(asyncio.create_task(
                search_from_dblp(session, url, name, results, sem)))
        for f in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            await f
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
    confs=['www', 'kdd', 'cikm', 'sigir', 'wsdm', 'ecir', 'recsys'],
    filter_keywords=['kddcup', 'w.html', 'lbr.html'],
    start_year=2012,
    filename='results.json',
    threads = 20
):
    results = load_results(filename)
    links = get_links(results, confs, filter_keywords, start_year)
    if len(links) > 0:
        names, urls = zip(*links)
        results = asyncio.run(crawl(urls, names, results, threads))
    results = filter_results(results)
    save_results(results, filename)


if __name__ == '__main__':
    run_all()