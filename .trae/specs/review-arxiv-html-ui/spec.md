# arXiv HTML Feature Review Spec

## Why
当前 arXiv HTML 页面已经承载每日论文浏览、日期切换、筛选、折叠和摘要展示，但用户观察到日历交互可能存在问题。除了定位 bug，还需要从功能整体体验出发，评估这个页面是否还能在阅读效率、历史浏览、筛选发现、交互体验、可维护性和后续扩展方向上继续提升。

## What Changes
- 系统性审查 `paperBotV2/arxiv_daily/generate_arxiv_html.py` 的 HTML 生成逻辑、日期选择、数据加载、排序、统计、模板渲染和输出路径。
- 系统性审查生成页面依赖的静态资源与模板，包括 `output/static/index.html`、`app.js`、`styles.css`、`templates/*.html`。
- 重点检查日历逻辑，包括当前日期解析、可用日期识别、localStorage 状态、跨月切换、可点击日期、跳转 URL 和选中态。
- 检查界面交互，包括“全部论文/仅显示精选”、非精选论文折叠、低分论文展开、摘要展开、按钮状态、计数显示和移动端体验。
- 检查展示逻辑，包括评分、精选判断、排序、统计数字、标题/翻译/摘要/推荐理由展示、作者截断、分类标签和空状态。
- 从功能整体角度评估页面信息架构、阅读路径、筛选/搜索能力、历史导航、跨日对比、主题聚合、论文收藏/标记、分享和移动端阅读体验。
- 从长期演进角度提出新功能 idea，并按收益、复杂度、风险和是否适合近期落地分层。
- 区分明确 bug、体验优化、工程可维护性、产品功能增强和远期 idea。
- 输出结构化 review 报告到 `docs/`，包含问题、证据、影响、严重度、建议方案和验证记录。
- 本 spec 阶段不修改业务代码；实现阶段优先做 review 和报告，除非用户后续明确要求修复。

## Impact
- Affected specs: `paperBotV2.arxiv_daily` HTML 页面生成与展示体验。
- Affected code: `paperBotV2/arxiv_daily/generate_arxiv_html.py`、`paperBotV2/arxiv_daily/output/static/index.html`、`paperBotV2/arxiv_daily/output/static/app.js`、`paperBotV2/arxiv_daily/output/static/styles.css`、`paperBotV2/arxiv_daily/output/static/templates/*.html`。
- Affected docs: 新增 `docs/paperbotv2-arxiv-html-ui-review.md`。

## ADDED Requirements
### Requirement: HTML Feature Review Report
The system SHALL produce a structured Markdown review report for `generate_arxiv_html.py` and the generated arXiv daily HTML feature.

#### Scenario: Review report is generated
- **WHEN** the review is completed
- **THEN** `docs/paperbotv2-arxiv-html-ui-review.md` SHALL include current logic summary, issue list, product/experience improvement opportunities, new feature ideas, severity or priority, evidence, recommendations, and verification records.

### Requirement: Calendar Logic Review
The review SHALL explicitly inspect calendar behavior and date navigation logic.

#### Scenario: Calendar issues are assessed
- **WHEN** the calendar logic is reviewed
- **THEN** the report SHALL cover current date parsing, selected date state, available date discovery, cross-month navigation, date clickability, URL routing, and stale localStorage behavior.

### Requirement: Interaction Review
The review SHALL explicitly inspect page interactions.

#### Scenario: Interaction issues are assessed
- **WHEN** the interaction layer is reviewed
- **THEN** the report SHALL cover filtering buttons, paper collapse/expand behavior, low-score paper reveal behavior, abstract/details behavior, display counts, and button visual states.

### Requirement: Display Logic Review
The review SHALL explicitly inspect display and data transformation logic.

#### Scenario: Display issues are assessed
- **WHEN** display logic is reviewed
- **THEN** the report SHALL cover sorting, selected-paper detection, score formatting, average score calculation, title/translation fallback, summary/reasoning fallback, authors truncation, category tags, empty data handling, and static resource fallback.

### Requirement: Feature Improvement and New Ideas Review
The review SHALL assess the arXiv HTML feature as a product surface, not only as code.

#### Scenario: Improvement ideas are assessed
- **WHEN** the feature is reviewed
- **THEN** the report SHALL include concrete ideas such as better search/filtering, category facets, score-range filters, keyword highlighting, history navigation, reading status, paper collection, comparison across days, better empty/loading states, sharing links, and mobile reading improvements where relevant.

#### Scenario: Ideas are prioritized
- **WHEN** new ideas are listed
- **THEN** each idea SHALL be labeled by recommended priority or phase, expected benefit, implementation complexity, and main risk.

### Requirement: Maintainability Review
The review SHALL inspect whether the current HTML generation architecture is easy to maintain and extend.

#### Scenario: Maintainability issues are assessed
- **WHEN** architecture and code organization are reviewed
- **THEN** the report SHALL cover inline CSS/JS, duplicated interaction logic, static resource fallback, template ownership, frontend/backend responsibility boundaries, and whether future UI features should stay in Python string injection or move into static assets.

### Requirement: No Online Side Effects
The review SHALL avoid production side effects.

#### Scenario: Review validation runs
- **WHEN** validation commands or smoke checks are executed
- **THEN** they SHALL NOT call DeepSeek, send Feishu messages, mutate production JSON/HTML outputs, or require production secrets.

## MODIFIED Requirements
### Requirement: Existing arXiv Daily Review Scope
The existing arXiv daily review scope is extended by this focused HTML/UI review, but this change does not reopen completed `review-arxiv-daily-logic` or `fix-arxiv-daily-review-issues` tasks.

## REMOVED Requirements
None.
