#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成大厂实践文章HTML页面
"""

import os
import sys
import json
import shutil
import argparse
import time
from datetime import datetime
from jinja2 import Template

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 直接定义配置项
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
STATIC_DIR = os.path.join(OUTPUT_DIR, "static")
ARTICLE_JSON_FILE = os.path.join(DATA_DIR, "article.json")
MAX_TITLE_DISPLAY_LENGTH = 100

# 定义确保目录存在的函数
def ensure_directories():
    """确保所有必要的目录存在"""
    for directory in [DATA_DIR, OUTPUT_DIR, STATIC_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")

def render_template(template_content, context):
    """使用Jinja2渲染模板
    
    Args:
        template_content: 模板内容
        context: 上下文变量字典
    
    Returns:
        str: 渲染后的内容
    """
    template = Template(template_content)
    return template.render(**context)


def load_article_data(file_path):
    """加载文章数据
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        list: 文章数据列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 转换中文键名为英文键名
        converted_data = []
        for item in data:
            # 确保公司名称是字符串类型
            company = item.get('公司', '未知')
            if not isinstance(company, str):
                company = str(company) if company is not None else '未知'
                
            converted_item = {
                'title': item.get('内容', '无标题'),
                'link': item.get('链接', '#'),
                'company': company,
                'tags': item.get('标签', []),
                'date': item.get('时间', '')
            }
            converted_data.append(converted_item)
            
        return converted_data
    except Exception as e:
        print(f"加载文章数据失败: {e}")
        print("请确保article.json文件存在且格式正确")
        return []


def get_sortable_date(date_str):
    """将日期字符串转换为可排序的格式
    
    Args:
        date_str: 日期字符串
    
    Returns:
        str: 标准格式的日期字符串
    """
    try:
        # 处理格式：YYYY-MM-DD
        if len(date_str) == 10 and '-' in date_str:
            return date_str
        # 处理格式：YYYY.MM.DD
        elif len(date_str) == 10 and '.' in date_str:
            return date_str.replace('.', '-')
        # 处理格式：MM/DD/YYYY
        elif len(date_str) == 10 and '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[2]}-{parts[0]}-{parts[1]}"
        # 处理格式：YYYY年MM月DD日
        elif len(date_str) >= 8 and '年' in date_str and '月' in date_str:
            year = date_str.split('年')[0]
            month_part = date_str.split('年')[1].split('月')[0]
            day_part = date_str.split('月')[1].split('日')[0] if '日' in date_str else date_str.split('月')[1]
            return f"{year}-{month_part.zfill(2)}-{day_part.zfill(2)}"
        # 处理格式：MM-DD-YY
        elif len(date_str) == 8 and '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3 and len(parts[2]) == 2:
                return f"20{parts[2]}-{parts[0]}-{parts[1]}"
        # 默认返回当前日期
        return datetime.now().strftime('%Y-%m-%d')
    except Exception as e:
        print(f"日期格式转换错误: {date_str}, {e}")
        return datetime.now().strftime('%Y-%m-%d')


def generate_table_rows(items):
    """生成表格行HTML
    
    Args:
        items: 文章数据列表
    
    Returns:
        str: 表格行HTML
    """
    rows = []
    for idx, item in enumerate(items, 1):  # 从1开始计数作为序号
        # 处理标题，限制显示长度
        title = item.get('title', '无标题')
        display_title = title if len(title) <= MAX_TITLE_DISPLAY_LENGTH else title[:MAX_TITLE_DISPLAY_LENGTH] + '...'
        
        # 处理链接
        link = item.get('link', '#')
        
        # 处理公司
        company = item.get('company', '未知')
        
        # 处理日期
        date = item.get('date', '')
        
        # 处理标签
        tags = item.get('tags', [])
        tag_display = ', '.join(tags)
        
        # 生成表格行HTML，确保列顺序与表头一致：序号、公司、标题、标签、发布时间
        row_html = f"""
        <tr class="article-row" data-company="{company}" data-tags="{','.join(tags)}">
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                {idx}
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {company}
                </span>
            </td>
            <td class="px-4 py-3 whitespace-nowrap">
                <a href="{link}" target="_blank" rel="noopener noreferrer" title="{title}" class="text-blue-600 hover:text-blue-800 hover:underline transition-colors">
                    {display_title}
                </a>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                {tag_display}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                {date}
            </td>
        </tr>
        """
        rows.append(row_html)
    
    return ''.join(rows)


def create_static_templates():
    """创建静态资源文件"""
    # 检查并创建目录
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    # 静态资源文件已通过其他方式创建或维护
    print("静态资源文件管理完成")


def generate_industry_html():
    """生成大厂实践文章HTML页面
    
    Returns:
        str: 生成的HTML文件路径
    """
    try:
        # 确保目录存在
        ensure_directories()
        
        # 创建静态模板文件
        create_static_templates()
        
        # 加载文章数据
        print("加载文章数据...")
        items = load_article_data(ARTICLE_JSON_FILE)
        print(f"成功加载 {len(items)} 条文章数据")
        
        if not items:
            print("没有找到文章数据，无法生成HTML页面")
            return None
        
        # 按日期排序
        print("按日期排序文章...")
        items_sorted = sorted(items, key=lambda x: get_sortable_date(x.get('date', '')), reverse=True)
        
        # 提取公司列表
        print("提取公司和标签列表...")
        companies = sorted(list(set([item.get('company', '未知') for item in items])))
        tags = sorted(list(set([tag for item in items for tag in item.get('tags', [])])))
        print(f"共提取 {len(companies)} 家公司，{len(tags)} 个标签")
        
        # 生成表格行HTML
        print("生成表格行HTML...")
        table_rows = generate_table_rows(items_sorted)
        print(f"表格行生成完成")
        
        # 准备渲染上下文
        print("准备渲染上下文...")
        context = {
            'TIMESTAMP': int(time.time()),
            'LAST_UPDATED': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_items': len(items),
            'companies': companies,
            'tags': tags,
            'table_rows': table_rows,
            'articles_json': json.dumps(items_sorted, ensure_ascii=False, default=str)
        }
        print(f"上下文准备完成，键数量: {len(context.keys())}")
        
        # 读取HTML模板文件，从output/static/templates目录读取
        template_file = os.path.join(OUTPUT_DIR, "static", "templates", "index.html.template")
        with open(template_file, 'r', encoding='utf-8') as f:
            html_template = f.read()
        print(f"成功读取模板文件: {template_file}")
        
        # 渲染HTML内容
        print("开始渲染HTML内容...")
        html_content = render_template(html_template, context)
        print("HTML渲染成功")
        
        # 生成输出文件路径，直接生成index.html
        output_file = os.path.join(OUTPUT_DIR, "index.html")
        
        # 写入文件
        print(f"写入HTML文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML页面已成功生成: {output_file}")
        return output_file
    except Exception as e:
        print(f"生成HTML页面失败: {e}")
        import traceback
        print(f"完整错误栈:\n{traceback.format_exc()}")
        return None



def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成大厂实践文章HTML页面')
    args = parser.parse_args()
    
    # 生成HTML页面（直接生成index.html）
    html_file = generate_industry_html()


if __name__ == "__main__":
    main()