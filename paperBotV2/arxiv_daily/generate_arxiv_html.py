import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from jinja2 import Template


# 配置参数
MAX_AUTHORS_DISPLAY_LENGTH = 80  # 作者名最大显示长度


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


def get_json_file_by_date(json_dir, date_str):
    """根据日期获取JSON文件路径
    
    Args:
        json_dir: JSON文件所在目录
        date_str: 日期字符串，格式为YYYYMMDD
    
    Returns:
        str: JSON文件的路径
    """
    file_name = f"{date_str}.json"
    file_path = os.path.join(json_dir, file_name)
    
    if not os.path.exists(file_path):
        print(f"未找到日期为 {date_str} 的JSON文件")
        return None
    
    return file_path


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


def read_frontend_file(directory, file_name):
    """读取文件内容
    
    Args:
        directory: 文件所在目录
        file_name: 文件名
    
    Returns:
        str: 文件内容
    """
    file_path = os.path.join(directory, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_name} 失败: {e}")
        return ''


def generate_date_options(current_date):
    """生成日期选择器的选项HTML
    
    Args:
        current_date: 当前日期
    
    Returns:
        str: 日期选项HTML
    """
    options = []
    # 生成最近7天的日期选项
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y%m%d')
        display_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        selected = ' selected' if date_str == current_date else ''
        options.append(f'<option value="{date_str}"{selected}> {display_date} </option>')
    return ''.join(options)


def render_template(template_content, context):
    """使用Jinja2渲染模板，支持条件逻辑、循环等功能
    
    Args:
        template_content: 模板内容
        context: 上下文变量字典
    
    Returns:
        str: 渲染后的内容
    """
    template = Template(template_content)
    return template.render(**context)


def generate_papers_html(papers, frontend_dir, static_dir=None):
    """生成论文列表的HTML（后端渲染）
    
    Args:
        papers: 论文数据列表
        frontend_dir: 前端目录路径
        static_dir: 静态资源目录路径（可选）
    
    Returns:
        str: 论文列表HTML
    """
    # 先按是否精选排序，再按评分从高到低排序
    papers_sorted = sorted(papers, key=lambda x: (not x.get('is_fine_ranked', False), -(x.get('rerank_relevance_score') or x.get('relevance_score') or 0)))
    
    # 读取模板文件
    # 优先从static_dir读取，如果没有再从frontend_dir读取
    if static_dir:
        templates_dir = os.path.join(static_dir, 'templates')
    else:
        templates_dir = os.path.join(frontend_dir, 'templates')
    selected_template = read_frontend_file(templates_dir, 'selected_paper_template.html')
    normal_template = read_frontend_file(templates_dir, 'normal_paper_template.html')
    
    papers_html = []
    
    for paper in papers_sorted:
        # 准备论文数据上下文
        score = paper.get('rerank_relevance_score') or paper.get('relevance_score') or 0
        
       # 确定论文类型和模板
        is_selected = paper.get('is_fine_ranked', False)
        template = selected_template if is_selected else normal_template
        
        # 分级折叠功能：为非精选论文添加不同的折叠级别
        if not is_selected:
            score_value = float(score)
            if score_value <= 1:
                # 分数<=1的论文，默认隐藏，只在分割线后显示标题
                display_class = "collapsed-level-2"
            else:
                # 其他非精选论文，默认只显示标题行
                display_class = "collapsed-level-1"
        else:
            # 精选论文，默认完全展开
            display_class = "expanded"
        
        # 准备论文数据上下文确定评分颜色
        if score >= 6:
            score_color = 'bg-green-100 text-green-800'
        elif score >= 4:
            score_color = 'bg-blue-100 text-blue-800'
        else:
            score_color = 'bg-gray-100 text-gray-800'
        
        # 处理分类标签
        category_tags = ''
        if isinstance(paper.get('categories'), list):
            category_tags = ''.join([f'<span class="category-tag">{cat}</span>' for cat in paper['categories']])
        elif paper.get('categories'):
            categories_str = str(paper['categories'])
            if ',' in categories_str:
                category_tags = ''.join([f'<span class="category-tag">{cat.strip()}</span>' for cat in categories_str.split(',')])
            else:
                category_tags = f'<span class="category-tag">{categories_str}</span>'
        
        # 截断作者名
        authors = paper.get('authors', '')
        if len(authors) > MAX_AUTHORS_DISPLAY_LENGTH:
            authors = authors[:MAX_AUTHORS_DISPLAY_LENGTH] + '...'
        
        # 准备渲染上下文
        # 处理评分：整数显示，不需要小数
        score_display = str(int(score))
        
        # 根据要求，所有论文优先使用非空的rerank_reasoning字段，否则使用reasoning字段，均为空时显示"无"
        reasoning_text = paper.get('reasoning', '无')
        if paper.get('rerank_reasoning'):
            reasoning_text = paper.get('rerank_reasoning')
        
        context = {
            'URL': paper.get('url', f'https://arxiv.org/abs/{paper.get("arxiv_id", "")}'),
            'TRANSLATION': paper.get('translation', paper.get('title', '')),
            'TITLE': paper.get('title', ''),
            'SCORE': score_display,
            'SCORE_COLOR': score_color,
            'ABSTRACT': paper.get('abstract', paper.get('summary', '暂无摘要')),
            'ORI_SUMMARY': paper.get('ori_summary', paper.get('abstract', paper.get('summary', '暂无摘要'))),
            'AUTHORS': authors,
            'SUMMARY': paper.get('summary', ''),
            'REASONING': reasoning_text,
            'PUB_DATE': paper.get('pub_date', ''),
            'ARXIV_ID': paper.get('arxiv_id', ''),
            'CATEGORY_TAGS': category_tags,
            'DISPLAY_CLASS': display_class
        }
        
        # 渲染模板
        paper_html = render_template(template, context)
        papers_html.append(paper_html)
    
    # 返回所有论文的HTML
    return ''.join(papers_html)


def generate_html(papers, date_str, script_dir, output_file=None):
    """生成HTML页面
    
    Args:
        papers: 论文数据列表
        date_str: 日期字符串，格式为YYYYMMDD
        script_dir: 脚本所在目录
        output_file: 输出文件路径，默认为None（自动生成）
    
    Returns:
        str: 生成的HTML文件路径
    """
    # 格式化日期显示
    display_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    # 计算统计信息
    total_papers = len(papers)
    # 统一精选论文判断逻辑，与app.js保持一致
    selected_papers = len([p for p in papers if p.get('is_fine_ranked', False)])

    
    if total_papers > 0:
        total_score = sum(p.get('rerank_relevance_score') or p.get('relevance_score') or 0 for p in papers)
        avg_score = f"{total_score / total_papers:.1f}"
    else:
        avg_score = "0"
    
    # 检查前端目录是否存在
    frontend_dir = os.path.join(script_dir, "frontend")
    
    # 如果未指定输出文件，则自动生成
    if output_file is None:
        output_dir = os.path.join(script_dir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, f"arxiv_{date_str}.html")
    
    # 确保静态资源目录存在
    static_dir = os.path.join(output_dir, "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # 确保templates子目录存在
    static_templates_dir = os.path.join(static_dir, "templates")
    if not os.path.exists(static_templates_dir):
        os.makedirs(static_templates_dir)
    
    # 如果frontend目录存在，复制静态资源文件
    import shutil
    if os.path.exists(frontend_dir):
        # 复制静态资源文件
        static_files = ['styles.css', 'tailwind.config.js', 'app.js', 'index.html']
        for file_name in static_files:
            src_path = os.path.join(frontend_dir, file_name)
            dst_path = os.path.join(static_dir, file_name)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                print(f"已复制静态资源: {file_name}")
        
        # 复制模板文件
        templates_dir = os.path.join(frontend_dir, "templates")
        if os.path.exists(templates_dir):
            template_files = ['normal_paper_template.html', 'selected_paper_template.html']
            for file_name in template_files:
                src_path = os.path.join(templates_dir, file_name)
                dst_path = os.path.join(static_templates_dir, file_name)
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dst_path)
                    print(f"已复制模板文件: {file_name}")
    
    # 优先从static_dir读取HTML模板，如果不存在再从frontend_dir读取
    html_template = read_frontend_file(static_dir, 'index.html')
    if not html_template and os.path.exists(frontend_dir):
        html_template = read_frontend_file(frontend_dir, 'index.html')
    
    if not html_template:
        print("无法读取HTML模板文件")
        return None
    
    # 生成动态内容
    papers_html = generate_papers_html(papers, frontend_dir, static_dir)
    date_options = generate_date_options(date_str)
    
    # 替换模板中的变量
    html_content = html_template.replace('{{DISPLAY_DATE}}', display_date)
    html_content = html_content.replace('{{TOTAL_PAPERS}}', str(total_papers))
    html_content = html_content.replace('{{SELECTED_PAPERS}}', str(selected_papers))
    html_content = html_content.replace('{{AVG_SCORE}}', avg_score)
    html_content = html_content.replace('{{DATE_OPTIONS}}', date_options)
    html_content = html_content.replace('{{PAPERS_HTML}}', papers_html)
    
    # 移除不必要的JSON数据部分
    import re
    html_content = re.sub(r'<script id="papers-data" type="application/json">[\s\S]*?</script>\s*', '', html_content)
    
    # 添加分级折叠功能的CSS样式
    collapse_css = '''
    <style>
        /* 分级折叠功能样式 */
        .collapsed-level-1 .paper-details {
            display: none;
        }
        
        .collapsed-level-2 {
            display: none !important;
        }
        
        /* 展开/折叠图标样式 */
        .expand-icon {
            display: inline-block;
            width: 20px;
            text-align: center;
            margin-right: 5px;
        }
        
        /* 展开/折叠按钮样式 */
        .expand-toggle {
            cursor: pointer;
            padding: 8px 12px;
            background-color: #f3f4f6;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            margin-bottom: 16px;
            text-align: center;
            font-weight: 500;
            color: #4b5563;
            transition: all 0.2s ease;
        }
        
        .expand-toggle:hover {
            background-color: #e5e7eb;
        }
        
        /* 分割线样式 */
        .papers-divider {
            height: 1px;
            background-color: #e5e7eb;
            margin: 20px 0;
            position: relative;
        }
        
        .papers-divider-label {
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            background-color: white;
            padding: 0 12px;
            color: #9ca3af;
            font-size: 14px;
            cursor: pointer;
        }
        
        .papers-divider-label:hover {
            color: #4b5563;
        }
        
        /* 展开后的样式 */
        .expanded-all .collapsed-level-1 .paper-details,
        .expanded-all .collapsed-level-2 {
            display: block;
        }
        
        .expanded-level-2 .collapsed-level-2 {
            display: block;
        }
    </style>
    '''
    
    # 更新资源引用路径
    html_content = html_content.replace('../frontend/styles.css', 'static/styles.css')
    html_content = html_content.replace('../frontend/tailwind.config.js', 'static/tailwind.config.js')
    html_content = html_content.replace('../frontend/app.js', 'static/app.js')
    
    # 在HTML内容中的</head>标签前插入CSS样式
    html_content = html_content.replace('</head>', collapse_css + '</head>')
    
    # 添加时间戳以避免CSS缓存
    import time
    timestamp = int(time.time())
    html_content = html_content.replace('{{TIMESTAMP}}', str(timestamp))
    
    # 添加分级折叠功能的JavaScript代码
    collapse_js = '''
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // 在精选论文和普通论文之间添加展开/折叠按钮
            const papersContainer = document.querySelector('#papers-container');
            if (papersContainer) {
                // 添加展开/折叠全部按钮
                const expandAllButton = document.createElement('div');
                expandAllButton.className = 'expand-toggle';
                expandAllButton.textContent = '展开/折叠全部非精选论文';
                expandAllButton.addEventListener('click', function() {
                    papersContainer.classList.toggle('expanded-all');
                    this.textContent = papersContainer.classList.contains('expanded-all') ? 
                        '收起全部非精选论文' : '展开全部非精选论文';
                    
                    // 更新所有论文标题前的图标状态
                    const collapsedPapers = papersContainer.querySelectorAll('.collapsed-level-1');
                    collapsedPapers.forEach(paper => {
                        const iconElement = paper.querySelector('.expand-icon');
                        if (iconElement) {
                            iconElement.className = papersContainer.classList.contains('expanded-all') ? 
                                'expand-icon fa fa-eye' : 'expand-icon fa fa-eye-slash';
                        }
                    });
                });
                
                // 找到第一个非精选论文的位置
                const firstNormalPaper = papersContainer.querySelector('.simple-paper-card');
                if (firstNormalPaper) {
                    papersContainer.insertBefore(expandAllButton, firstNormalPaper);
                }
                
                // 添加分割线用于展开分数<=1的论文
                const divider = document.createElement('div');
                divider.className = 'papers-divider';
                
                const dividerLabel = document.createElement('div');
                dividerLabel.className = 'papers-divider-label';
                dividerLabel.textContent = '点击展开更多论文（评分较低）';
                dividerLabel.addEventListener('click', function() {
                    papersContainer.classList.toggle('expanded-level-2');
                    this.textContent = papersContainer.classList.contains('expanded-level-2') ? 
                        '点击收起低分论文' : '点击展开更多论文（评分较低）';
                });
                
                divider.appendChild(dividerLabel);
                
                // 在所有非精选论文的最后一个元素后面添加分割线
                const normalPapers = papersContainer.querySelectorAll('.simple-paper-card');
                if (normalPapers.length > 0) {
                    const lastNormalPaper = normalPapers[normalPapers.length - 1];
                    papersContainer.insertBefore(divider, lastNormalPaper.nextSibling);
                }
            }
            
            // 为每个非精选论文添加点击标题展开/折叠详情的功能
            const collapsedPapers = document.querySelectorAll('.collapsed-level-1');
            collapsedPapers.forEach(paper => {
                const titleElement = paper.querySelector('h3');
                if (titleElement) {
                    titleElement.style.cursor = 'pointer';
                    
                    // 创建展开/折叠图标元素并设置样式
                    const iconElement = document.createElement('i');
                    iconElement.className = 'expand-icon fa fa-eye-slash cursor-pointer';
                    iconElement.style.marginRight = '8px';
                    
                    // 将图标插入到标题链接之前，作为同级元素
                    const linkElement = titleElement.querySelector('a');
                    if (linkElement) {
                        // 将图标直接添加到标题元素中，位于链接之前
                        titleElement.insertBefore(iconElement, linkElement);
                        
                        // 为图标单独添加点击事件处理展开/折叠
                        iconElement.addEventListener('click', function(e) {
                            e.stopPropagation(); // 阻止事件冒泡到标题元素
                            const details = paper.querySelector('.paper-details');
                            if (details) {
                                const isExpanded = details.style.display === 'block';
                                details.style.display = isExpanded ? 'none' : 'block';
                                
                                // 更新图标状态
                                this.className = isExpanded ? 
                                    'expand-icon fa fa-eye-slash cursor-pointer' : 'expand-icon fa fa-eye cursor-pointer';
                                this.style.marginRight = '8px';
                            }
                        });
                    }
                    
                    // 为标题元素添加点击事件，也可以展开/折叠，但会检查点击目标
                    titleElement.addEventListener('click', function(e) {
                        // 仅当点击的是标题本身（非链接、非图标）时才展开/折叠
                        if (!e.target.closest('a') && !e.target.closest('.expand-icon')) {
                            const details = paper.querySelector('.paper-details');
                            if (details) {
                                const isExpanded = details.style.display === 'block';
                                details.style.display = isExpanded ? 'none' : 'block';
                                
                                // 更新图标状态
                                const iconElement = this.querySelector('.expand-icon');
                                if (iconElement) {
                                    iconElement.className = isExpanded ? 
                                        'expand-icon fa fa-eye-slash cursor-pointer' : 'expand-icon fa fa-eye cursor-pointer';
                                    iconElement.style.marginRight = '8px';
                                }
                            }
                        }
                    });
                }
            });
            
            // 实现"仅显示精选"按钮功能
            const showSelectedButton = document.getElementById('show-selected');
            if (showSelectedButton) {
                showSelectedButton.addEventListener('click', function() {
                    // 显示所有精选论文，隐藏所有普通论文
                    const selectedPapers = document.querySelectorAll('.paper-card');
                    const normalPapers = document.querySelectorAll('.simple-paper-card');
                    
                    selectedPapers.forEach(paper => {
                        paper.style.display = 'block';
                    });
                    
                    normalPapers.forEach(paper => {
                        paper.style.display = 'none';
                    });
                    
                    // 更新显示计数
                    const displayCountElement = document.getElementById('display-count');
                    if (displayCountElement) {
                        displayCountElement.textContent = `显示 ${selectedPapers.length} 篇论文 (共 ${selectedPapers.length + normalPapers.length} 篇)`;
                    }
                    
                    // 更新按钮样式
                    this.className = 'px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary/90 transition-colors';
                    document.getElementById('show-all').className = 'px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors';
                    
                    // 隐藏展开/折叠按钮和分割线
                    const expandToggle = document.querySelector('.expand-toggle');
                    if (expandToggle) expandToggle.style.display = 'none';
                    
                    const papersDivider = document.querySelector('.papers-divider');
                    if (papersDivider) papersDivider.style.display = 'none';
                });
            }
            
            // 实现"全部论文"按钮功能
            const showAllButton = document.getElementById('show-all');
            if (showAllButton) {
                showAllButton.addEventListener('click', function() {
                    // 显示所有论文
                    const allPapers = document.querySelectorAll('.paper-card, .simple-paper-card');
                    allPapers.forEach(paper => {
                        paper.style.display = 'block';
                    });
                    
                    // 重置折叠状态
                    papersContainer.classList.remove('expanded-all');
                    
                    // 更新显示计数
                    const displayCountElement = document.getElementById('display-count');
                    if (displayCountElement) {
                        displayCountElement.textContent = `显示 ${allPapers.length} 篇论文 (共 ${allPapers.length} 篇)`;
                    }
                    
                    // 更新按钮样式
                    this.className = 'px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary/90 transition-colors';
                    document.getElementById('show-selected').className = 'px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors';
                    
                    // 重新显示展开/折叠按钮和分割线
                    const expandToggle = document.querySelector('.expand-toggle');
                    if (expandToggle) {
                        expandToggle.style.display = 'block';
                        expandToggle.textContent = '展开全部非精选论文';
                    }
                    
                    const papersDivider = document.querySelector('.papers-divider');
                    if (papersDivider) papersDivider.style.display = 'block';
                });
            }
        });
    </script>'''
    
    # 获取有论文数据的日期列表
    def get_available_dates(json_dir):
        available_dates = []
        if os.path.exists(json_dir):
            for file in os.listdir(json_dir):
                if file.endswith('.json') and len(file) == 13 and file != 'results.json':  # 格式: YYYYMMDD.json
                    date_str = file[:-5]  # 移除.json
                    available_dates.append(date_str)
        return available_dates
    
    # 根据script_dir计算json_dir
    json_dir = os.path.join(script_dir, "data")
    
    # 获取有论文数据的日期列表
    available_dates = get_available_dates(json_dir)
    available_dates_js = '[' + ','.join(f'"{date}"' for date in available_dates) + ']'
    
    # 将日历相关的JavaScript代码直接嵌入到HTML文件中，添加论文数据存在性检查
    calendar_js = '''
    <script>
    
    // 初始化日历
    document.addEventListener('DOMContentLoaded', () => {
        try {
            console.log('Attempting to initialize calendar...');
            initCalendar();
        } catch (error) {
            console.error('Error initializing calendar:', error);
        }
    });
    
    // 日历初始化函数
    function initCalendar() {
        const toggleBtn = document.getElementById('date-picker-toggle');
        const datePicker = document.getElementById('date-picker');
        const calendarGrid = document.getElementById('calendar-grid');
        const prevMonthBtn = document.getElementById('prev-month');
        const nextMonthBtn = document.getElementById('next-month');
        const currentMonthEl = document.getElementById('current-month');
        const selectedDateText = document.getElementById('selected-date-text');
        
        // 当前显示的日期（从页面获取）
        const currentDateStr = document.getElementById('current-date').textContent.trim().replace(/^\d+年|月|日/g, '');
        const currentDate = new Date(currentDateStr);
        let displayYear = currentDate.getFullYear();
        let displayMonth = currentDate.getMonth();
        
        // 有论文数据的日期列表
        const availableDates = ''' + available_dates_js + ''';
        
        // 尝试从localStorage恢复选择状态
        const savedDate = localStorage.getItem('selectedDate');
        const savedYear = localStorage.getItem('selectedYear');
        const savedMonth = localStorage.getItem('selectedMonth');
        
        // 确保页面加载时显示当前选中的日期
        // 修复持久化问题：确保每次加载都能正确恢复选中状态
        if (savedDate) {
            selectedDateText.textContent = savedDate;
            if (savedYear) displayYear = parseInt(savedYear);
            if (savedMonth) displayMonth = parseInt(savedMonth);
        } else {
            // 首次加载时，将当前页面日期保存到localStorage
            const currentPageDate = currentDateStr.replace(/\//g, '-');
            selectedDateText.textContent = currentPageDate;
            localStorage.setItem('selectedDate', currentPageDate);
            localStorage.setItem('selectedYear', currentDate.getFullYear().toString());
            localStorage.setItem('selectedMonth', currentDate.getMonth().toString());
        }
    
        // 切换日历显示状态
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            
            // 显式控制hidden类的添加和移除
            if (datePicker.classList.contains('hidden')) {
                // 显示日历 - 确保移除hidden类
                datePicker.classList.remove('hidden');
                renderCalendar();
            } else {
                // 隐藏日历
                datePicker.classList.add('hidden');
            }
        });
        
        // 点击其他区域关闭日历
        document.addEventListener('click', () => {
            if (!datePicker.classList.contains('hidden')) {
                datePicker.classList.add('hidden');
            }
        });
        
        // 阻止日历内部点击事件冒泡
        datePicker.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        // 上月和下月按钮
        prevMonthBtn.addEventListener('click', () => {
            displayMonth--;
            if (displayMonth < 0) {
                displayMonth = 11;
                displayYear--;
            }
            renderCalendar();
        });
        
        nextMonthBtn.addEventListener('click', () => {
            displayMonth++;
            if (displayMonth > 11) {
                displayMonth = 0;
                displayYear++;
            }
            renderCalendar();
        });
        
        /**
         * 渲染日历
         */
        function renderCalendar() {
            // 清空日历网格
            calendarGrid.innerHTML = '';
            
            // 更新当前月份显示
            const monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
            currentMonthEl.textContent = displayYear + '年' + monthNames[displayMonth];
            
            // 计算当前月份的第一天是星期几
            const firstDay = new Date(displayYear, displayMonth, 1);
            const firstDayOfWeek = firstDay.getDay();
            
            // 计算当前月份的天数
            const daysInMonth = new Date(displayYear, displayMonth + 1, 0).getDate();
            
            // 添加上月的占位天数
            for (let i = 0; i < firstDayOfWeek; i++) {
                const emptyDay = document.createElement('div');
                emptyDay.classList.add('py-1', 'text-gray-300');
                calendarGrid.appendChild(emptyDay);
            }
            
            // 获取当前日期（用于高亮显示）
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            
            // 添加当前月份的天数
            for (let day = 1; day <= daysInMonth; day++) {
                const dayElement = document.createElement('div');
                const currentDateObj = new Date(displayYear, displayMonth, day);
                const dateStr = displayYear + String(displayMonth + 1).padStart(2, '0') + String(day).padStart(2, '0');
                const displayDateStr = displayYear + '-' + String(displayMonth + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
                
                // 设置日期元素基本样式
                dayElement.textContent = day;
                
                // 检查该日期是否有论文数据
                const hasPapers = availableDates.includes(dateStr);
                
                if (hasPapers) {
                    // 有论文数据的日期样式
                    dayElement.classList.add('py-1', 'cursor-pointer', 'hover:bg-gray-100', 'rounded', 'bg-blue-50', 'font-medium');
                    
                    // 添加点击事件，跳转到对应日期的页面
                    dayElement.addEventListener('click', () => {
                        console.log('Date clicked:', displayDateStr);
                        selectedDateText.textContent = displayDateStr;
                        
                        // 保存选择状态到localStorage
                        localStorage.setItem('selectedDate', displayDateStr);
                        localStorage.setItem('selectedYear', displayYear.toString());
                        localStorage.setItem('selectedMonth', displayMonth.toString());
                        
                        datePicker.classList.add('hidden');
                        
                        // 构造目标URL并跳转
                        const targetUrl = 'arxiv_' + dateStr + '.html';
                        window.location.href = targetUrl;
                    });
                } else {
                    // 没有论文数据的日期样式（置灰不可点击）
                    dayElement.classList.add('py-1', 'text-gray-400', 'cursor-not-allowed');
                }
                
                // 高亮显示当天日期（覆盖之前的样式）
                if (currentDateObj.getTime() === today.getTime()) {
                    dayElement.classList.remove('bg-blue-50');
                    dayElement.classList.add('bg-primary', 'text-white', 'font-bold', 'shadow');
                    if (!hasPapers) {
                        // 当天没有论文时，仍然置灰但保持背景色
                        dayElement.classList.add('opacity-70');
                    }
                }
                
                // 高亮显示当前选中的日期
                if (displayDateStr === selectedDateText.textContent) {
                    dayElement.classList.add('font-bold', 'border-2', 'border-primary', 'rounded-lg', 'shadow-md');
                }
                
                // 增强有论文数据的日期样式，使其更明显
                if (hasPapers && currentDateObj.getTime() !== today.getTime()) {
                    dayElement.classList.add('bg-blue-100', 'hover:bg-blue-200', 'transition-colors', 'duration-200');
                }
                
                calendarGrid.appendChild(dayElement);
            }
        }
    }
    </script>
    '''
    
    html_content = html_content.replace('</body>', collapse_js + calendar_js + '</body>')
    
    # 写入文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML页面已生成: {output_file}")
        
        # 创建默认首页（index.html），指向当天日期的页面
        index_file = os.path.join(output_dir, "index.html")
        # 生成重定向HTML内容
        index_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>arXiv 每日论文精选 - 重定向</title>
    <meta http-equiv="refresh" content="0;url=arxiv_{date_str}.html">
</head>
<body>
    <p>正在重定向到当天的论文精选页面...</p>
    <p>如果没有自动跳转，请<a href="arxiv_{date_str}.html">点击这里</a></p>
</body>
</html>
        """
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        print(f"默认首页已创建: {index_file}")
        
        return output_file
    except Exception as e:
        print(f"生成HTML页面失败: {e}")
        return None


def create_default_templates(templates_dir):
    """创建默认模板文件（仅作备份，当前实现不使用）
    
    Args:
        templates_dir: 模板目录路径
    """
    pass  # 当前实现不使用模板文件，实际渲染逻辑在app.js中实现


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成arXiv每日论文HTML页面')
    parser.add_argument('--date', type=str, help='指定日期（格式：YYYYMMDD），如不指定则使用最新日期')
    parser.add_argument('--output', type=str, help='输出文件路径')
    args = parser.parse_args()
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(script_dir, "data")
    
    # 确保JSON目录存在
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
        print(f"创建目录: {json_dir}")
    
    # 获取JSON文件路径
    if args.date:
        json_file = get_json_file_by_date(json_dir, args.date)
    else:
        json_file = get_latest_json_file(json_dir)
    
    if not json_file:
        print("无法获取JSON文件，程序退出")
        return
    
    # 加载论文数据
    papers = load_paper_data(json_file)
    if not papers:
        print("未加载到论文数据，程序退出")
        return
    
    # 生成HTML页面
    date_str = args.date if args.date else os.path.basename(json_file).split('.')[0]
    generate_html(papers, date_str, script_dir, args.output)


if __name__ == "__main__":
    main()