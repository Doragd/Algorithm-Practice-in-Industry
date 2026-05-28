# Tasks
- [x] Task 1: 梳理当前 HTML 生成链路：阅读 `generate_arxiv_html.py` 和静态资源，确认输入 JSON、模板来源、输出文件、资源复制、页面初始化和运行时脚本注入顺序。
  - [x] SubTask 1.1: 梳理 `main()`、`get_latest_json_file()`、`load_paper_data()`、`generate_html()` 的执行顺序。
  - [x] SubTask 1.2: 梳理 `generate_papers_html()`、精选/普通模板、评分、排序、折叠 class 和统计字段。
  - [x] SubTask 1.3: 梳理静态资源来源与 fallback：`frontend/`、`output/static/`、模板文件和资源引用改写。

- [x] Task 2: Review 日历逻辑：检查日期解析、可用日期列表、localStorage、跨月导航、点击跳转和选中态是否存在 bug 或体验问题。
  - [x] SubTask 2.1: 检查 `currentDateStr` 解析和 `new Date()` 兼容性。
  - [x] SubTask 2.2: 检查 `availableDates` 获取、排序、日期高亮和不可点击日期样式。
  - [x] SubTask 2.3: 检查 localStorage 是否会导致跨页面、跨天或不同日期页面显示错乱。
  - [x] SubTask 2.4: 检查日期跳转 URL、`index.html` 重定向和缺失日期页面行为。

- [x] Task 3: Review 页面交互和展示：检查筛选、折叠、低分论文展开、摘要详情、计数、移动端布局和视觉状态。
  - [x] SubTask 3.1: 检查“全部论文/仅显示精选”实际筛选逻辑和 `display-count` 是否准确。
  - [x] SubTask 3.2: 检查非精选论文折叠、低分论文隐藏、展开按钮和分割线插入位置是否合理。
  - [x] SubTask 3.3: 检查 `<details>` 摘要、标题点击、图标状态和链接点击是否冲突。
  - [x] SubTask 3.4: 检查统计卡片、评分 badge、作者截断、分类标签、空 summary/reasoning fallback 和移动端可读性。

- [x] Task 4: Review 逻辑正确性、安全与可维护性：检查模板渲染、数据变异、静态资源路径、重复脚本、内联 CSS/JS 和未来维护风险。
  - [x] SubTask 4.1: 检查 `load_paper_data()` 是否修改原始数据对象、是否影响后续逻辑。
  - [x] SubTask 4.2: 检查安全转义和 URL 白名单是否仍覆盖所有插入点。
  - [x] SubTask 4.3: 检查 `app.js` 与内联 `collapse_js`/`calendar_js` 是否存在重复绑定或职责冲突。
  - [x] SubTask 4.4: 按 P1/P2/P3 区分 bug、体验问题、可维护性改进和功能增强机会。

- [x] Task 5: Review 功能整体体验和新 idea：从用户每天读论文的路径出发，提出页面能力、阅读效率、历史浏览和发现能力的改进方向。
  - [x] SubTask 5.1: 评估信息架构：统计区、日期入口、筛选入口、精选区、普通论文区和低分隐藏区是否符合阅读优先级。
  - [x] SubTask 5.2: 评估发现能力：是否需要搜索、分类筛选、分数区间筛选、关键词高亮、只看未读、只看高分、按主题聚合等。
  - [x] SubTask 5.3: 评估历史能力：是否需要更好的跨日导航、最近有数据日期列表、月份热力图、跨日趋势、历史 Top 论文入口等。
  - [x] SubTask 5.4: 评估阅读动作：是否需要收藏、标记已读、复制引用、分享单篇、跳转 PDF/HTML/arXiv、展开全部摘要等。
  - [x] SubTask 5.5: 将新 idea 按近期可做、中期增强、远期探索分层，并标注收益、复杂度和风险。

- [x] Task 6: 执行无副作用验证并产出报告：用本地临时目录或静态检查验证关键结论，新增 `docs/paperbotv2-arxiv-html-ui-review.md`。
  - [x] SubTask 6.1: 对相关 Python 文件执行 `py_compile` 或等价语法检查。
  - [x] SubTask 6.2: 使用临时输出目录构造最小样本验证 HTML 生成、日历数据注入和资源引用，不覆盖线上 `output/`。
  - [x] SubTask 6.3: 将当前逻辑、问题清单、改进建议、新功能 idea 和验证记录写入 `docs/paperbotv2-arxiv-html-ui-review.md`。

# Task Dependencies
- Task 2 depends on Task 1.
- Task 3 depends on Task 1.
- Task 4 depends on Task 1.
- Task 5 depends on Task 1, Task 2, and Task 3.
- Task 6 depends on Task 2, Task 3, Task 4, and Task 5.
