import json
import os
import re

# 文件路径
results_file = 'data/results.json'
papers_dir = 'data/papers'

# 黑名单会议列表，只对这些会议的摘要进行长度限制
ABSTRACT_TRUNCATE_BLACKLIST = ['acl', 'emnlp', 'naacl']

# 目标文件大小限制（字节）
TARGET_FILE_SIZE_BYTES = 1.3 * 1024 * 1024  # 1.3MB

# 摘要截断长度的最小和最大限制
MIN_ABSTRACT_LENGTH = 300  # 最小300字符
MAX_ABSTRACT_LENGTH = 5000  # 最大5000字符

# 检查results.json是否存在
if not os.path.exists(results_file):
    print(f"错误：文件 {results_file} 不存在")
    exit(1)

# 创建papers目录
os.makedirs(papers_dir, exist_ok=True)

# 读取JSON文件
print(f"正在读取文件：{results_file}")
with open(results_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 处理每个会议
total_confs = len(data)
processed_confs = 0
skipped_confs = 0

def clean_text(text):
    """清理文本，移除Markdown中的特殊字符"""
    if not text:
        return ''
    # 转义Markdown特殊字符
    text = text.replace('|', '\\|').replace('`', '\\`').replace('*', '\\*')
    # 移除多余的空白
    text = ' '.join(text.split())
    return text

def truncate_text(text, max_length=1000):
    """截断文本到指定长度"""
    if not text:
        return ''
    if len(text) <= max_length:
        return text
    # 确保在单词边界处截断
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return truncated + '...'

def calculate_optimal_abstract_length(papers_count):
    """
    基于论文数量计算最佳摘要截断长度，目标是控制最终文件大小在1.3MB左右
    
    Args:
        papers_count: 会议论文数量
    
    Returns:
        推荐的摘要最大长度（字符数）
    """
    if papers_count <= 0:
        return MAX_ABSTRACT_LENGTH
    
    # 估算每篇论文的平均大小（不含摘要）
    # 包括标题、链接、表格格式等固定开销
    avg_paper_size_without_abstract = 500  # 字节
    
    # 估算可用于摘要的总字节数
    available_size_for_abstracts = TARGET_FILE_SIZE_BYTES - (avg_paper_size_without_abstract * papers_count)
    
    # 计算平均每篇论文可用的摘要字节数
    # 注意：这里假设UTF-8编码，平均每个字符约为2字节
    avg_abstract_bytes_per_paper = available_size_for_abstracts / papers_count / 2
    
    # 转换为字符数，并确保在合理范围内
    optimal_length = int(avg_abstract_bytes_per_paper)
    optimal_length = max(MIN_ABSTRACT_LENGTH, optimal_length)
    optimal_length = min(MAX_ABSTRACT_LENGTH, optimal_length)
    
    return optimal_length

def generate_md_table(papers_list, conf_folder):
    """生成Markdown表格，包含所有字段"""
    # 表格头部
    table = "| 序号 | 标题 | 链接 | 推荐理由 | 推荐度 | 摘要 | 作者 | 组织 |\n"
    table += "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
    
    # 计算最佳摘要截断长度
    papers_count = len(papers_list)
    optimal_abstract_length = calculate_optimal_abstract_length(papers_count)
    
    # 表格内容
    for index, paper in enumerate(papers_list, start=1):
        title = clean_text(paper.get('paper_name', ''))
        authors = clean_text(', '.join(paper.get('paper_authors', [])))
        url = paper.get('paper_url', '')
        abstract = clean_text(paper.get('paper_abstract', ''))
        
        # 处理作者详情
        authors_detail = paper.get('authors_detail', [])
        if isinstance(authors_detail, list):
            authors_detail_str = set()
            for author in authors_detail:
                if isinstance(author, dict):
                    name = author.get('name', '')
                    org = author.get('org', '')
                    if org:
                        authors_detail_str.add(org)
            authors_detail_text = clean_text('; '.join(authors_detail_str))
        else:
            authors_detail_text = ''
        
        title_translation = clean_text(paper.get('title_translation', ''))
        relevance_score = paper.get('relevance_score', 0)
        reasoning = clean_text(paper.get('reasoning', ''))
        
        # 只对黑名单会议的摘要进行长度限制
        if conf_folder.lower() in ABSTRACT_TRUNCATE_BLACKLIST:
            abstract_display = truncate_text(abstract, max_length=optimal_abstract_length)
            print(f"  会议 {conf_folder} 论文数量: {papers_count}, 动态摘要截断长度: {optimal_abstract_length}")
        else:
            abstract_display = abstract
            
        table += f"| {index} | {title_translation} |  [{title}]({url}) | {reasoning} | {relevance_score} | {abstract_display} | {authors} | {authors_detail_text} |\n"
    
    return table

print(f"开始处理 {total_confs} 个会议...\n")

for conf_name, papers_list in data.items():
    processed_confs += 1
    print(f"[{processed_confs}/{total_confs}] 处理会议: {conf_name}")
    
    # 检查论文列表是否有效
    if not isinstance(papers_list, list) or not papers_list:
        print(f"  跳过：{conf_name} - 没有有效论文数据")
        skipped_confs += 1
        continue
    
    # 提取会议名称（例如从www2024提取www）
    conf_folder = re.match(r'([a-z]+)\d+', conf_name, re.IGNORECASE)
    if conf_folder:
        conf_folder = conf_folder.group(1).lower()
    else:
        conf_folder = conf_name.lower()
    
    # 创建会议文件夹
    conf_folder_path = os.path.join(papers_dir, conf_folder)
    os.makedirs(conf_folder_path, exist_ok=True)
    
    # 生成markdown内容
    md_content = f"# {conf_name.upper()}\n\n"
    md_content += f"## 会议论文列表\n\n"
    md_content += f"本会议共有 {len(papers_list)} 篇论文\n\n"
    md_content += generate_md_table(papers_list, conf_folder)
    
    # 写入markdown文件
    md_file_path = os.path.join(conf_folder_path, f"{conf_name}.md")
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"  已生成：{md_file_path}")

print(f"\n处理完成！")
print(f"总共处理：{processed_confs} 个会议")
print(f"跳过会议：{skipped_confs} 个")
print(f"成功生成：{processed_confs - skipped_confs} 个markdown文件")