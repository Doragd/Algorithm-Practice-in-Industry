import os
import json
import time
import requests
import datetime
from tqdm import tqdm
from arxiv import send_wechat_message, send_feishu_message
from translate import translate

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Content-Type": "application/json"
}

URL = os.environ.get("CONF_URL", None)
SERVERCHAN_API_KEY = os.environ.get("SERVERCHAN_API_KEY", None)
LIMITS = int(os.environ.get('LIMITS', 4))
ERROR_LIMITS = int(os.environ.get('ERROR_LIMITS', 1))
INTERVAL = int(os.environ.get("INTERVAL", 3))
# 支持多个飞书URL，用逗号分隔
FEISHU_URLS = [url.strip() for url in os.environ.get("FEISHU_URL", "").split(',') if url.strip()]
MODEL_TYPE = os.environ.get("MODEL_TYPE", "DeepSeek")

def match_score(item):
    keywords = [
        "click-through", "recommend", "taobao", "ctr", "cvr", "conver", "match",
        "search", "rank", "alipay", "kuanshou", "multi-task", "candidate", "relevance", "query",
        "retriev", "personal",  "click", "commerce", "embedding", "collaborative", "facebook",
        "sequential",  "wechat", "tencent", "multi-objective", "ads", "tower", "approximat", 
        "instacart", "airbnb", "negative"
    ]
    keywords2 = [
        "bias", "cold", "a/b", "intent", "product", "domain", "feed", "large-scale", "interest", "estima", "online", "twitter",
        "machine learning", "stream", "netflix", "linucb", "user", "term", "semantic",  
        "explor", "sampl", "listwise", "constrative", "pairwise", "bandit", "variation", "session", 
        "uplift", "distil", "item", "similar", "behavior", "cascad", "trigger", "transfer"
        "top-k", "top-n", "bid"
    ]
    score = 0
    for keyword in keywords:
        if 'paper_name' in item and keyword.lower() in item['paper_name'].lower():
            score += 1
    for keyword in keywords2:
        if 'paper_name' in item and keyword.lower() in item['paper_name'].lower():
            score += 0.25
    return score

def get_paper(query):
    req = {
        "query": query,
        "needDetails": True,
        "page": 0,
        "size": 20,
        "filters": []
    }
    try:
        r = requests.post(URL, data=json.dumps(req), headers=HEADERS, timeout=10)
        r.raise_for_status()
        ret = r.json()
        if 'data' in ret and 'hitList' in ret['data']:
            hit_list = ret['data']['hitList']
            if len(hit_list) > 0:
                return hit_list[0]
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error occurred when requesting data from {URL}: {e}")
    return None

def load_results(filename='results.json'):
    if not os.path.exists(filename):
        return {}
    return json.load(open(filename, 'r'))

def save_results(results, filename='results.json'):
    try:
        json.dump(results, open(filename, 'w'), indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error: Failed to save results to {filename}: {e}")

def parse_item(item):
    ret = {}
    authors = item["authors"] if "authors" in item else []
    for author_idx, author in enumerate(authors):
        if "email" in author:
            del authors[author_idx]["email"]
        if "id" in author:
            del authors[author_idx]["id"]
        if "name" not in author:
            authors[author_idx]["name"] = ""
        if "org" not in author:
            authors[author_idx]["org"] = ""
    ret["authors_detail"] = authors
    ret["paper_abstract"] = item["pubAbstract"].strip()
    ret["translated"] = ""

    return ret

def update_results(results):
    # confs = ['kdd', 'cikm', 'sigir', 'www', 'wsdm', 'ecir', 'recsys']
    confs = ['kdd', 'www', 'cikm', 'recsys', 'wsdm', 'sigir', 'ecir']
    years = list(range(2025, 2010, -1))
    count = 0
    daily_limits = False
    ret_items = []
    for year in years:
        for conf in confs:
            key = f"{conf}{year}"
            if key not in results:
                continue
            for i in range(len(results[key])):
                if count >= LIMITS:
                    daily_limits = True
                    break
                if results[key][i]["paper_abstract"] != "":
                    continue
                item = get_paper(results[key][i]["paper_name"])
                if item is None:
                    print(f"[+] find error at paper {results[key][i]['paper_name']}")
                    time.sleep(INTERVAL * 20)
                    continue
                try:
                    parse_ret = parse_item(item)
                except:
                    print(f"[+] find error at paper {results[key][i]['paper_name']}")
                    time.sleep(INTERVAL * 20)
                    continue
                if not parse_ret:
                    print(f"[+] find error at paper {results[key][i]['paper_name']}")
                    time.sleep(INTERVAL * 20)
                    continue
                print(f"[+] get sucuess at papaer {results[key][i]['paper_name']}")
                ret_items.append([key, i, parse_ret])
                count += 1
                time.sleep(INTERVAL * 10)
            if daily_limits:
                break
        if daily_limits:
            break
    source = [item[-1]["paper_abstract"] for item in ret_items]
    target = translate(source)
    if len(target) == len(source):
        for i, _ in enumerate(ret_items):
            ret_items[i][-1].update({"translated": target[i]})
    for key, i, item in ret_items:
        results[key][i].update(item)
    save_results(results)

    return ret_items

def cronjob(error_cnt):
    print("[+] 开始加载历史数据")
    results = load_results()
    for key in results:
        results[key] = sorted(results[key], key=match_score, reverse=True)
    print("[+] 开始检索最新顶会论文")
    ret_items = update_results(results)
    if not ret_items:
        if error_cnt >= ERROR_LIMITS:
            print('[+] 每日推送任务执行结束')
            return -1
        return 0
    print('[+] 开始推送每日顶会论文....')
    for ii, [key, i, _] in enumerate(tqdm(ret_items, total=len(ret_items), desc="论文推送进度")):
        ret = results[key][i]
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        title = ret["paper_name"]
        url = ret["paper_url"]
        author = "; ".join(ret["paper_authors"])
        conf = key.upper()
        summary = ret['paper_abstract']
        try:
            translated = ret['translated']
        except:
            translated = "NA"
        try:
            org = "; ".join(list(set([author["org"].split(",")[0] for author in ret["authors_detail"]])))
        except:
            org = "NA"
        
        msg_title = f'[{conf}]{title}'
        msg_author = f'Author: {author}'
        msg_org = f'ORG: {org}'
        msg_url = f'URL: {url}'
        msg_summary = f'Summary：\n\n{summary}'
        msg_translated = f'Translated (Powered by {MODEL_TYPE}):\n\n{translated}'

        push_title = f'{conf}[{ii}]@{today}'
        msg_content = f"[{msg_title}]({url})\n\n{msg_author}\n\n{msg_org}\n\n{msg_url}\n\n{msg_translated}\n\n{msg_summary}\n\n"

        # send_wechat_message(push_title, msg_content, SERVERCHAN_API_KEY)
        # 从arxiv模块导入的send_feishu_message函数已经支持多个URL
        send_feishu_message(push_title, msg_content)

        time.sleep(12)

    print('[+] 每日推送任务执行结束')

    return 1

if __name__ == '__main__':
    print("[+] 开始执行cronjob任务")
    error_cnt = 0
    code = -1
    while code == -1:
        if error_cnt > 0:
            print("[+] 重试中...")
            time.sleep(error_cnt * 60)
        code = cronjob(error_cnt)
        error_cnt += 1
