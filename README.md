<!--
 * @Author: Doragd doragd@users.noreply.github.com
 * @Date: 2025-10-10 02:18:25
 * @LastEditors: Doragd doragd@users.noreply.github.com
 * @LastEditTime: 2025-10-10 03:32:43
 * @FilePath: /Algorithm-Practice-in-Industry/paperBotV2/arxiv_output/README.md
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
# arXiv 每日论文精选 - GitHub Pages

这个目录包含自动生成的HTML页面，用于展示arXiv每日论文精选。这些页面会通过GitHub Actions自动生成并部署到GitHub Pages。

## 页面结构

每个HTML页面对应一天的论文精选，文件名格式为`arxiv_YYYYMMDD.html`，其中`YYYYMMDD`是日期。

## 访问方式

部署到GitHub Pages后，可以通过以下URL访问最新的论文精选页面：

```
https://[GitHub用户名].github.io/[仓库名]/arxiv_output/arxiv_YYYYMMDD.html
```

首页地址为：

```
https://[GitHub用户名].github.io/[仓库名]/arxiv_output/index.html
```

## 页面功能

每个HTML页面包含以下功能：

- 顶部显示日期和统计信息（总论文数、精选论文数、平均评分）
- 日期选择器（可以切换不同日期的论文）
- 筛选器（可以显示全部论文或仅显示精选论文）
- 论文列表，按评分排序，精选论文排在前面
- 每篇论文包含标题、翻译、作者、核心总结、个性化推荐理由等信息
- 点击论文标题可以跳转到arXiv原文页面

## 技术实现

HTML页面基于`paperBotV2/generate_arxiv_html.py`脚本生成，该脚本会读取`arxiv_daily`目录下的JSON文件，解析论文数据，并生成与`example.html`相似的网页。

## 自动化部署

HTML页面通过`.github/workflows/arxiv_daily_full.yml`工作流自动生成和部署，该工作流会在每天UTC时间10:00（北京时间18:00）自动执行，也支持手动触发。

工作流完成以下操作：
1. 执行脚本生成JSON数据
2. 调用`paperBotV2/generate_arxiv_html.py`生成HTML页面
3. 使用`peaceiris/actions-gh-pages@v3`将内容发布到`gh-pages`分支

发布成功后，可以通过GitHub Pages访问生成的HTML页面。

## 如何在本地预览

可以直接在浏览器中打开HTML文件进行预览，无需启动服务器。

```bash
# 直接用浏览器打开
open paperBotV2/arxiv_output/arxiv_YYYYMMDD.html
```

## 自定义配置

如果需要修改HTML页面的样式或功能，可以编辑`paperBotV2/generate_arxiv_html.py`脚本中的HTML模板部分。