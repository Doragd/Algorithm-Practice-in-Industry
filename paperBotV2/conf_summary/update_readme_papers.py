#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新README.md中的顶会论文列表
"""
import os
import re

def get_all_meetings_and_years(papers_dir):
    """获取所有会议及其年份信息"""
    meetings = {}
    
    # 遍历会议文件夹
    for meeting in os.listdir(papers_dir):
        meeting_path = os.path.join(papers_dir, meeting)
        if not os.path.isdir(meeting_path):
            continue
        
        years = []
        # 遍历会议文件夹下的文件
        for file in os.listdir(meeting_path):
            if file.endswith('.md'):
                # 提取年份 (假设文件名格式为 meetingYYYY.md)
                match = re.search(r'\d{4}', file)
                if match:
                    year = int(match.group())
                    years.append(year)
        
        if years:
            meetings[meeting] = sorted(years)
    
    return meetings

def generate_papers_table(meetings, papers_rel_path):
    """生成Markdown表格"""
    # 按字母顺序排序会议
    sorted_meetings = sorted(meetings.keys())
    
    # 表格头部
    table = "| " + " | ".join([m.upper() for m in sorted_meetings]) + " |\n"
    table += "| " + " | ".join(["------" for _ in sorted_meetings]) + " |\n"
    
    # 获取所有年份范围
    all_years = set()
    for years in meetings.values():
        all_years.update(years)
    min_year = min(all_years)
    max_year = max(all_years)
    
    # 为每个年份生成一行
    for year in range(min_year, max_year + 1):
        row = []
        for meeting in sorted_meetings:
            if year in meetings[meeting]:
                # 生成链接
                file_path = f"{papers_rel_path}/{meeting}/{meeting}{year}.md"
                row.append(f"[{year}]({file_path})")
            else:
                row.append(str(year))
        table += "| " + " | ".join(row) + " |\n"
    
    return table

def update_readme():
    """更新README.md文件"""
    # 当脚本在conf_summary目录下运行时的路径计算
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "../.."))
    readme_path = os.path.join(repo_root, "README.md")
    papers_dir = os.path.join(script_dir, "data", "papers")
    papers_rel_path = "paperBotV2/conf_summary/data/papers"
    
    # 读取README.md
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 获取会议和年份信息
    print("收集会议和年份信息...")
    meetings = get_all_meetings_and_years(papers_dir)
    print(f"找到 {len(meetings)} 个会议:")
    for meeting, years in sorted(meetings.items()):
        print(f"  {meeting.upper()}: {len(years)} 年 ({min(years)}-{max(years)})")
    
    # 生成新的表格
    print("\n生成新的论文列表表格...")
    new_table = generate_papers_table(meetings, papers_rel_path)
    
    # 替换旧的表格
    # 使用正则表达式匹配表格部分
    pattern = r'## 顶会论文列表\n(.*?)(?=\n## |$)'  # 匹配从"## 顶会论文列表"开始到下一个标题或文件结束
    replacement = f"## 顶会论文列表\n{new_table}"
    
    # 使用DOTALL模式让.匹配换行符
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # 写回README.md
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"\nREADME.md 已更新!")
    print(f"新的论文列表包含 {len(meetings)} 个会议，年份范围: {min(set().union(*meetings.values()))}-{max(set().union(*meetings.values()))}")

if __name__ == "__main__":
    update_readme()