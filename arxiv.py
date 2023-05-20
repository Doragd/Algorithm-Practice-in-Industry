
'''
credit to original author: Glenn (chenluda01@outlook.com)
'''

import os
import requests
import time
import json
import datetime
from tqdm import tqdm


def get_yesterday():
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')


def search_arxiv_papers(search_term, max_results=10):
    papers = []

    url = f'http://export.arxiv.org/api/query?' + \
          f'search_query=all:{search_term}' +  \
          f'&start=0&&max_results={max_results}' + \
          f'&sortBy=submittedDate&sortOrder=descending'

    response = requests.get(url)

    if response.status_code != 200:
        return []

    feed = response.text
    entries = feed.split('<entry>')[1:]

    if not entries:
        return []

    print('[+] 开始处理每日最新论文....')

    for entry in entries:

        title = entry.split('<title>')[1].split('</title>')[0].strip()
        summary = entry.split('<summary>')[1].split('</summary>')[0].strip()
        url = entry.split('<id>')[1].split('</id>')[0].strip()
        pub_date = entry.split('<published>')[1].split('</published>')[0]
        pub_date = datetime.datetime.strptime(pub_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")

        papers.append({
            'title': title,
            'url': url,
            'pub_date': pub_date,
            'summary': summary,
        })

    return papers


def send_wechat_message(title, content, SERVERCHAN_API_KEY):
    url = f'https://sctapi.ftqq.com/{SERVERCHAN_API_KEY}.send'
    params = {
        'title': title,
        'desp': content,
    }
    requests.post(url, params=params)


def save_to_local_file(papers, filename='arxiv.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        results = json.load(f)

    titles = {paper['title'].lower() for paper in results}
    add_papers = [paper for paper in papers if paper['title'].lower() not in titles]

    results.extend(add_papers)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

        


def cronjob():

    SERVERCHAN_API_KEY = os.environ.get("SERVERCHAN_API_KEY", None)

    if SERVERCHAN_API_KEY is None:
        raise Exception("未设置SERVERCHAN_API_KEY环境变量")

    search_term = os.environ.get('QUERY', 'cs.IR')
    max_results = os.environ.get('THREADS', 1)

    print('[+] 开始执行每日推送任务....')
    yesterday = get_yesterday()
    print('[+] 开始检索每日最新论文....')
    papers = search_arxiv_papers(search_term, max_results)

    save_to_local_file(papers)

    print('[+] 开始推送每日最新论文....')

    for paper in tqdm(papers, total=len(papers), desc=f"论文推送进度"):

        title = paper['title']
        url = paper['url']
        pub_date = paper['pub_date']
        summary = paper['summary']

        yesterday = get_yesterday()

        if pub_date == yesterday:
            msg_title = f'[Newest]Title: {title}' 
        else:
            msg_title = f'Title: {title}'

        msg_url = f'URL: {url}'
        msg_pub_date = f'Pub Date：{pub_date}'
        msg_summary = f'Summary：\n\n{summary}'

        today = datetime.datetime.now().strftime('%Y-%m-%d')
        push_title = f'Arxiv:{search_term}@{today}'
        msg_content = f"[{msg_title}]({url})\n\n{msg_pub_date}\n\n{msg_url}\n\n{msg_summary}\n\n"

        send_wechat_message(push_title, msg_content, SERVERCHAN_API_KEY)

        time.sleep(12)

    print('[+] 每日推送任务执行结束')


if __name__ == '__main__':
    cronjob()



