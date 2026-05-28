import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path

import requests
from tqdm import tqdm


SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = SCRIPT_DIR / "data" / "results.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
    ),
    "Content-Type": "application/json",
}

DEFAULT_CONFS = ["kdd", "www", "cikm", "recsys", "wsdm", "sigir", "ecir"]
PRIMARY_KEYWORDS = [
    "click-through", "recommend", "taobao", "ctr", "cvr", "conver", "match",
    "search", "rank", "alipay", "kuanshou", "multi-task", "candidate",
    "relevance", "query", "retriev", "personal", "click", "commerce",
    "embedding", "collaborative", "facebook", "sequential", "wechat",
    "tencent", "multi-objective", "ads", "tower", "approximat",
    "instacart", "airbnb", "negative",
]
SECONDARY_KEYWORDS = [
    "bias", "cold", "a/b", "intent", "product", "domain", "feed",
    "large-scale", "interest", "estima", "online", "twitter",
    "machine learning", "stream", "netflix", "linucb", "user", "term",
    "semantic", "explor", "sampl", "listwise", "constrative", "pairwise",
    "bandit", "variation", "session", "uplift", "distil", "item",
    "similar", "behavior", "cascad", "trigger", "transfer", "top-k",
    "top-n", "bid",
]


def parse_csv_env(name, default=None):
    raw_value = os.environ.get(name)
    if not raw_value:
        return default or []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def env_bool(name, default=False):
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_results(path=RESULTS_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results, path=RESULTS_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def match_score(item):
    title = item.get("paper_name", "").lower()
    score = 0
    for keyword in PRIMARY_KEYWORDS:
        if keyword.lower() in title:
            score += 1
    for keyword in SECONDARY_KEYWORDS:
        if keyword.lower() in title:
            score += 0.25
    return score


def fetch_private_paper(query, conf_url):
    if not conf_url:
        print("CONF_URL 未设置，跳过私有摘要补全")
        return None

    payload = {
        "query": query,
        "needDetails": True,
        "page": 0,
        "size": 20,
        "filters": [],
    }
    try:
        response = requests.post(
            conf_url,
            data=json.dumps(payload),
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"请求 CONF_URL 失败: {exc}")
        return None

    hit_list = data.get("data", {}).get("hitList", [])
    if not hit_list:
        return None
    return hit_list[0]


def parse_private_paper(item):
    authors = item.get("authors") or []
    cleaned_authors = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        cleaned_authors.append({
            "name": author.get("name", ""),
            "org": author.get("org", ""),
            "orgId": author.get("orgId", ""),
        })

    abstract = (item.get("pubAbstract") or "").strip()
    if not abstract:
        return None

    return {
        "authors_detail": cleaned_authors,
        "paper_abstract": abstract,
    }


def translate_with_deepseek(texts, api_key):
    if not api_key:
        print("DEEPSEEK_API_KEY 未设置，跳过摘要翻译")
        return ["" for _ in texts]

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    system_prompt = {
        "role": "system",
        "content": (
            "你是一位专业的翻译人员，擅长在人工智能领域内进行高质量的英文到中文翻译。"
            "请准确翻译论文摘要，保留专业术语和技术细节。"
        ),
    }
    translations = []
    for text in texts:
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[system_prompt, {"role": "user", "content": text}],
                temperature=1.3,
                stream=False,
            )
            translations.append(response.choices[0].message.content.strip())
        except Exception as exc:
            print(f"DeepSeek 翻译失败: {exc}")
            translations.append("")
    return translations


def translate_with_caiyun(texts, api_key):
    if not api_key:
        print("CAIYUN_TOKEN 未设置，跳过摘要翻译")
        return ["" for _ in texts]

    payload = {
        "source": texts,
        "trans_type": "en2zh",
        "request_id": "conf_daily",
        "detect": True,
    }
    headers = {
        "content-type": "application/json",
        "x-authorization": "token " + api_key,
    }
    try:
        response = requests.post(
            "http://api.interpreter.caiyunai.com/v1/translator",
            data=json.dumps(payload),
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        targets = response.json().get("target", [])
        if len(targets) == len(texts):
            return targets
    except (requests.RequestException, ValueError) as exc:
        print(f"彩云翻译失败: {exc}")
    return ["" for _ in texts]


def translate_abstracts(texts, model_type):
    if not texts:
        return []
    if model_type.lower() == "caiyun":
        return translate_with_caiyun(texts, os.environ.get("CAIYUN_TOKEN", ""))
    return translate_with_deepseek(texts, os.environ.get("DEEPSEEK_API_KEY", ""))


def find_and_update_papers(results, conf_url, limits, interval, confs, start_year, dry_run):
    selected = []
    years = list(range(dt.datetime.now().year, start_year - 1, -1))

    for year in years:
        for conf in confs:
            key = f"{conf}{year}"
            papers = results.get(key)
            if not papers:
                continue

            sorted_indexes = sorted(
                range(len(papers)),
                key=lambda idx: match_score(papers[idx]),
                reverse=True,
            )
            for paper_index in sorted_indexes:
                if len(selected) >= limits:
                    return selected
                paper = papers[paper_index]
                if paper.get("paper_abstract", "").strip():
                    continue

                title = paper.get("paper_name", "")
                print(f"开始补全论文摘要: {key} - {title}")
                if dry_run:
                    print("DRY_RUN=true，仅预览，不请求 CONF_URL")
                    selected.append((key, paper_index, {"paper_abstract": "[DRY_RUN]"}))
                    continue

                private_item = fetch_private_paper(title, conf_url)
                if private_item is None:
                    print(f"未找到摘要: {title}")
                    time.sleep(interval)
                    continue

                parsed_item = parse_private_paper(private_item)
                if not parsed_item:
                    print(f"解析摘要失败: {title}")
                    time.sleep(interval)
                    continue

                selected.append((key, paper_index, parsed_item))
                time.sleep(interval)

    return selected


def apply_updates(results, selected, model_type, dry_run):
    if dry_run:
        return selected

    abstracts = [item["paper_abstract"] for _, _, item in selected]
    translations = translate_abstracts(abstracts, model_type)
    for idx, (_, _, item) in enumerate(selected):
        translation = translations[idx] if idx < len(translations) else ""
        item["abstract_translation"] = translation
        item["translated"] = translation

    for key, paper_index, item in selected:
        results[key][paper_index].update(item)

    return selected


def get_org_text(paper):
    orgs = set()
    for author in paper.get("authors_detail", []):
        if isinstance(author, dict) and author.get("org"):
            orgs.add(author["org"].split(",")[0])
    return "; ".join(sorted(orgs)) if orgs else "NA"


def build_message(key, paper, index, model_type):
    today = dt.datetime.now().strftime("%Y-%m-%d")
    title = paper.get("paper_name", "")
    url = paper.get("paper_url", "#")
    authors = "; ".join(paper.get("paper_authors", [])) or "NA"
    org = get_org_text(paper)
    summary = paper.get("paper_abstract", "")
    translated = paper.get("abstract_translation") or paper.get("translated") or "NA"

    push_title = f"{key.upper()}[{index}]@{today}"
    content = (
        f"[[{key.upper()}]{title}]({url})\n\n"
        f"Author: {authors}\n\n"
        f"ORG: {org}\n\n"
        f"URL: {url}\n\n"
        f"Translated (Powered by {model_type}):\n\n{translated}\n\n"
        f"Summary:\n\n{summary}\n\n"
    )
    return push_title, content


def send_feishu_message(title, content, urls, dry_run):
    if dry_run:
        print(f"[DRY_RUN] 将发送飞书消息: {title}")
        return
    if not urls:
        print("没有有效的 FEISHU_URL，跳过发送消息")
        return

    card_data = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [{"tag": "markdown", "content": content}],
    }
    body = json.dumps({"msg_type": "interactive", "card": json.dumps(card_data)})
    headers = {"Content-Type": "application/json"}

    for idx, url in enumerate(urls):
        try:
            response = requests.post(url=url, data=body, headers=headers, timeout=10)
            print(f"飞书推送[{idx + 1}/{len(urls)}]返回状态: {response.status_code}")
        except requests.RequestException as exc:
            print(f"飞书推送[{idx + 1}/{len(urls)}]失败: {exc}")


def run(args):
    results = load_results(args.results)
    confs = [conf.lower() for conf in parse_csv_env("CONFS", DEFAULT_CONFS)]
    selected = find_and_update_papers(
        results=results,
        conf_url=os.environ.get("CONF_URL", ""),
        limits=args.limits,
        interval=args.interval,
        confs=confs,
        start_year=args.start_year,
        dry_run=args.dry_run,
    )

    if not selected:
        print("没有需要补全和推送的会议论文")
        return 0

    selected = apply_updates(results, selected, args.model_type, args.dry_run)
    if not args.dry_run:
        save_results(results, args.results)

    feishu_urls = parse_csv_env("FEISHU_URL", [])
    for index, (key, paper_index, _) in enumerate(tqdm(selected, desc="会议论文推送进度")):
        paper = results[key][paper_index]
        title, content = build_message(key, paper, index, args.model_type)
        send_feishu_message(title, content, feishu_urls, args.dry_run)
        if not args.dry_run:
            time.sleep(args.push_interval)

    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fill conference paper abstracts and send daily Feishu notifications."
    )
    parser.add_argument("--results", type=Path, default=RESULTS_PATH)
    parser.add_argument("--limits", type=int, default=int(os.environ.get("LIMITS", "10")))
    parser.add_argument("--interval", type=int, default=int(os.environ.get("INTERVAL", "5")))
    parser.add_argument("--push-interval", type=int, default=12)
    parser.add_argument("--start-year", type=int, default=2012)
    parser.add_argument("--model-type", default=os.environ.get("MODEL_TYPE", "DeepSeek"))
    parser.add_argument("--dry-run", action="store_true", default=env_bool("DRY_RUN", False))
    return parser.parse_args()


def main():
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
