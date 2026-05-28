import os
import json
import requests
from datetime import datetime

# 从环境变量获取配置，同时提供默认值
# 支持多个飞书URL，使用逗号分隔
FEISHU_URLS = os.environ.get("FEISHU_URL", "").split(',')
# 去除空字符串和空格
FEISHU_URLS = [url.strip() for url in FEISHU_URLS if url.strip()]
RETURN_PAPERS = int(os.environ.get("RETURN_PAPERS", "20"))


def get_latest_json_file(json_dir):
    """获取最新的JSON文件路径
    
    Args:
        json_dir: JSON文件所在目录
    
    Returns:
        str: 最新JSON文件的路径
    """
    try:
        # 获取目录中的所有JSON文件
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json') and f != 'results.json']
        if not json_files:
            print("未找到JSON文件")
            return None
        
        # 按文件名（日期）排序，获取最新的
        json_files.sort(reverse=True)
        latest_file = json_files[0]
        return os.path.join(json_dir, latest_file)
    except Exception as e:
        print(f"获取最新JSON文件失败: {e}")
        return None


def load_paper_data(file_path):
    """加载并解析论文数据
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        list: 论文数据列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 转换为列表并添加arxiv_id字段
        papers = []
        for arxiv_id, paper_info in data.items():
            paper_info['arxiv_id'] = arxiv_id
            papers.append(paper_info)
        
        return papers
    except Exception as e:
        print(f"加载论文数据失败: {e}")
        return []


def send_papers_to_feishu(papers, feishu_urls=None):
    # 如果没有指定URL列表，使用默认的FEISHU_URLS
    if feishu_urls is None:
        feishu_urls = FEISHU_URLS

    feishu_urls = [url.strip() for url in feishu_urls if url and url.strip()]

    # 如果没有有效的飞书URL，直接返回
    if not feishu_urls:
        print("⚠️ 没有有效的飞书URL，跳过发送消息")
        return
    
    date = datetime.now().strftime('%Y-%m-%d')
    
    card_data = {
        "type": "template",
        "data": {
            "template_id": "AAqxH62u1uNko",
            "template_version_name": "1.0.8",
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
    failures = []
    
    # 向每个飞书URL发送消息
    for idx, url in enumerate(feishu_urls):
        send_label = f"[{idx+1}/{len(feishu_urls)}]"
        try:
            ret = requests.post(url=url, data=body, headers=headers, timeout=10)
            print(f"✉️ 飞书推送{send_label}返回状态: {ret.status_code}")
            response_body = ret.text[:500]
            if not ret.ok:
                failures.append(f"{send_label} HTTP失败: {ret.status_code}; body={response_body}")
                continue

            try:
                ret_data = ret.json()
            except ValueError as e:
                failures.append(
                    f"{send_label} 响应不是有效JSON: {e}; "
                    f"HTTP {ret.status_code}; body={response_body}"
                )
                continue

            status_code = ret_data.get("StatusCode", ret_data.get("code"))
            if status_code != 0:
                status_msg = ret_data.get("StatusMessage", ret_data.get("msg", ""))
                failures.append(
                    f"{send_label} 业务失败: code={status_code}, "
                    f"msg={status_msg}; body={response_body}"
                )
                continue
        except requests.RequestException as e:
            failures.append(f"{send_label} 请求失败: {e}")

    if failures:
        for failure in failures:
            print(f"❌ 飞书推送失败: {failure}")
        raise RuntimeError("飞书推送存在失败:\n" + "\n".join(failures))


def main():
    """主函数，读取最新论文数据并发送飞书消息"""
    # 获取当前脚本所在目录（paperBotV2/arxiv_daily目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(current_dir, "data")
    
    # 获取最新的JSON文件
    latest_json_file = get_latest_json_file(json_dir)
    if not latest_json_file:
        print("无法获取最新的JSON文件，程序退出")
        return
    
    # 从文件名中提取日期并检查是否为今天
    latest_file_name = os.path.basename(latest_json_file)
    if latest_file_name.endswith('.json'):
        file_date_str = latest_file_name[:-5]  # 去掉.json后缀
        try:
            # 解析文件名中的日期
            file_date = datetime.strptime(file_date_str, '%Y%m%d')
            # 获取今天的日期（不含时间）
            today = datetime.now().date()
            # 检查文件日期是否为今天
            if file_date.date() != today:
                print(f"⚠️ 最新文件的日期 {file_date.date()} 不是今天 {today}，避免重复发送，程序退出")
                return
        except ValueError:
            print(f"⚠️ 无法从文件名 {latest_file_name} 中解析日期，继续处理")
    
    # 加载论文数据
    papers = load_paper_data(latest_json_file)
    if not papers:
        print("未加载到论文数据，程序退出")
        return
    
    # 按照精排分数排序并选择前N篇论文
    papers_with_score = [p for p in papers if 'rerank_relevance_score' in p and p.get('is_fine_ranked', False)]
    papers_with_score.sort(key=lambda x: x['rerank_relevance_score'], reverse=True)
    selected_papers = papers_with_score[:RETURN_PAPERS]
    
    # 检查是否有有效的飞书URL
    if not FEISHU_URLS:
        print("⚠️ 环境变量FEISHU_URL未设置或为空，无法发送飞书消息")
        return
        
    print(f"📤 准备发送 {len(selected_papers)} 篇论文到 {len(FEISHU_URLS)} 个飞书URL...")
    
    # 发送到飞书
    if selected_papers:
        send_papers_to_feishu(selected_papers)
        print("✅ 飞书消息发送完成！")
    else:
        print("⚠️ 没有符合条件的论文可以发送")


if __name__ == "__main__":
    main()
