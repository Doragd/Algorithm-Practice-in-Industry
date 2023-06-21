import os
import re
import json

with open('results.json', 'r') as f:
    data = json.load(f)

confs = []
years = []
for conference, papers in data.items():
    sorted_papers = sorted(papers, key=lambda x: x['paper_cite'], reverse=True)
    markdown = f'# {conference.upper()} Paper List\n\n'
    markdown += '|论文|作者|组织|摘要|翻译|代码|引用数|\n'
    markdown += '|---|---|---|---|---|---|---|\n'

    pattern = re.compile(r'([a-zA-Z]+)(\d+)')
    match = pattern.match(conference)
    conf, year = 'default', ''
    if match:
        conf = match.group(1)
        year = match.group(2)

    confs.append(conf)
    years.append(year)

    for paper in sorted_papers:
        paper_name = paper['paper_name']
        paper_authors = ', '.join(paper['paper_authors'])
        paper_org = "; ".join(list(set([item.get("org", "") for item in paper["authors_detail"]]))) if "authors_detail" in paper else ""
        paper_abstract = paper['paper_abstract']
        paper_translated = paper['translated'] if "translated" in paper else ""
        paper_url = paper['paper_url']
        paper_code = f'[code](https://paperswithcode.com/search?q_meta=&q_type=&q={paper_name.replace(" ", "+")})'
        paper_cite = paper['paper_cite']
        paper_link = f'[{paper_name}]({paper_url})'
        markdown += f'|{paper_link}|{paper_authors}|{paper_org}|{paper_abstract}|{paper_translated}|{paper_code}|{paper_cite}|\n'

    folder_path = f'papers/{conf}'
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    with open(f'papers/{conf}/{conference}.md', 'w') as f:
        f.write(markdown)

with open("README.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

title_st = "## 顶会论文列表"
title_ed = '## 大厂实践文章'
st_index, ed_index = None, None
for i, line in enumerate(lines):
    if st_index is not None and ed_index is not None:
        break
    if line.strip() == title_st:
        st_index = i
    if line.strip() == title_ed:
        ed_index = i

if st_index is not None and ed_index is not None:
    confs, years = list(set(confs)), list(set(years))
    confs.sort()
    years.sort()
    markdown = [
        "".join([f"|   {conf.upper()}  " for conf in confs]) + '|\n',
        '|  ------ ' * (len(confs)) + ' |\n',
    ]
    for year in years:
        markdown_str = '|   '
        markdown_str += "".join([ 
            f"[{year}](./papers/{conf}/{conf}{year}.md)" + '  |   '
            if os.path.exists(f'./papers/{conf}/{conf}{year}.md')
            else f"{year}" + '  |   '
            for conf in confs
        ])
        markdown_str += '\n'
        markdown.append(markdown_str)
    markdown.append('\n')
    
    newlines = lines[:st_index] + [lines[st_index]] + markdown + lines[ed_index:]

    with open("README.md", "w", encoding="utf-8") as f:
        f.writelines(newlines)




    


