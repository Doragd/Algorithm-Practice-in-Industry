# 大厂实践文章页面生成器

这个模块用于自动生成大厂实践文章的HTML页面，风格与arxiv_daily保持一致。

## 功能说明

1. 从`data/`目录下的CSV和JSON文件中读取大厂实践文章数据
2. 生成风格与arxiv_daily一致的HTML页面，包含以下功能：
   - 文章表格展示
   - 公司筛选
   - 标签筛选
   - 关键词搜索

## 文件结构

```
paperBotV2/industry_practice/
├── __init__.py             # 包初始化文件
├── data/                   # 数据目录
│   ├── article.csv         # 文章数据CSV文件
│   └── article.json        # 文章数据JSON文件
├── generate_industry_html.py # HTML页面生成脚本
├── maintain.py             # 维护脚本（更新数据、README和页面）
├── output/                 # 输出目录
└── README.md               # 说明文档
```

## 使用方法

### 手动运行

1. 确保已安装必要的依赖：`pip install -r requirements.txt`
2. 运行`generate_industry_html.py`脚本：`python generate_industry_html.py`

### 自动运行

当GitHub Actions中的`update_content` workflow被触发时，会自动执行以下操作：
1. 更新CSV和JSON数据文件
2. 更新README文件
3. 发送飞书通知
4. 生成并更新HTML页面

## 页面功能

1. **表格展示**：以表格形式展示所有文章，包含公司、标题、标签和发布时间
2. **公司筛选**：可以按公司筛选文章
3. **标签筛选**：可以按标签筛选文章
4. **关键词搜索**：可以搜索文章标题或内容中的关键词

## 注意事项

- 页面生成后会保存在`paperBotV2/industry_practice/output/`目录下
- 每次生成会直接更新`index.html`文件
- 静态资源文件会保存在`output/static/`目录下
