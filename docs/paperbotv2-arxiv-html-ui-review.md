# PaperBotV2 arXiv HTML UI Review

## 结论摘要

本次 review 聚焦 `paperBotV2/arxiv_daily/generate_arxiv_html.py` 及其生成的 arXiv 每日 HTML 页面。当前链路已经具备每日论文展示、精选优先、普通论文折叠、低分论文隐藏、摘要详情、统计卡片、日期日历和静态资源 fallback 等能力，且输出路径支持 `--output`，可以用临时目录做无副作用验证。

主要风险集中在前端状态与后端注入逻辑交错：日历会被过期 `localStorage` 影响，筛选和折叠逻辑分散在 `app.js` 与内联脚本中，低分论文分割线位置不符合文案语义，部分空值 fallback 与评分展示仍有体验问题。建议优先修正日历选中态和交互职责边界，再逐步补充搜索、筛选、历史浏览和阅读状态能力。

## 当前逻辑梳理

### 输入与数据转换

- `main()` 从 `paperBotV2/arxiv_daily/data/` 读取指定 `--date` 的 `YYYYMMDD.json`，未指定时按文件名倒序选择最新 JSON。
- `get_latest_json_file()` 排除 `results.json`，直接按文件名排序选最新文件；`get_json_file_by_date()` 只接受 `YYYYMMDD`。
- `load_paper_data()` 将 JSON 字典转换为论文列表，并向每个 `paper_info` 原地写入 `arxiv_id`。
- `generate_html()` 统计总论文数、精选论文数和平均分；精选判断使用 `is_fine_ranked`，评分优先 `rerank_relevance_score`，否则 `relevance_score`。
- `generate_papers_html()` 先按精选优先排序，再按评分降序排序；精选论文使用 `selected_paper_template.html`，普通论文使用 `normal_paper_template.html`。

### 模板渲染与展示

- 模板渲染使用 Jinja2 `Environment` 和默认 autoescape，正文、标题、作者、摘要等文本会被转义。
- URL 只允许 `http/https` 且 host 属于 arXiv 白名单，路径必须以 `/abs/`、`/pdf/` 或 `/html/` 开头，异常 URL 回退到 `https://arxiv.org/abs/{arxiv_id}` 或 `https://arxiv.org`。
- 分类标签由 `build_category_tags()` 生成，分类文本逐项转义后以 `Markup` 注入模板。
- 作者超过 `MAX_AUTHORS_DISPLAY_LENGTH` 后截断，标题优先展示 `translation`，摘要优先 `abstract`，原始摘要优先 `ori_summary`。
- `summary` 非空时展示“核心总结”；推荐理由优先 `rerank_reasoning`，否则 `reasoning`，默认值为“无”。

### 静态资源与输出

- 默认输出为 `paperBotV2/arxiv_daily/output/arxiv_YYYYMMDD.html`，指定 `--output` 时会以输出文件所在目录作为临时 `output_dir`。
- 若 `frontend/` 存在则复制其中 `styles.css`、`tailwind.config.js`、`app.js`、`index.html` 和模板；当前仓库主要使用 `output/static/` 作为 fallback 来源。
- 输出页面中的 `../frontend/styles.css`、`../frontend/tailwind.config.js`、`../frontend/app.js` 会被改写为 `static/...`。
- 每次生成具体日期 HTML 后，会在同一输出目录写入 `index.html`，通过 meta refresh 指向 `arxiv_YYYYMMDD.html`。

### 日历逻辑

- 后端扫描 `script_dir/data/*.json`，注入 `availableDates` 数组，过滤 `results.json` 和非 `YYYYMMDD.json` 文件。
- 前端从 `#current-date` 文本解析当前日期，初始化 `displayYear` 和 `displayMonth`。
- 日历按钮控制 `#date-picker` 的 `hidden` class，支持上月和下月切换。
- 有数据日期可点击，点击后写入 `localStorage.selectedDate/selectedYear/selectedMonth`，并跳转到 `arxiv_YYYYMMDD.html`。
- 无数据日期置灰不可点击；当天日期使用 `bg-primary` 高亮，选中日期使用边框和阴影高亮。

### 页面交互

- 精选论文默认完全展开，普通论文按评分分为 `collapsed-level-1` 和 `collapsed-level-2`。
- `collapsed-level-1` 只隐藏 `.paper-details`，标题仍可见；`collapsed-level-2` 整卡默认隐藏。
- 内联 `collapse_js` 会插入“展开/折叠全部非精选论文”按钮，给普通论文标题加眼睛图标，并处理“全部论文/仅显示精选”的实际过滤。
- `app.js` 也绑定了 `show-all` 和 `show-selected`，但只更新按钮样式；摘要详情主要依赖原生 `<details>`。

## 问题清单

| 严重度 | 类型 | 问题 | 证据 | 影响 | 建议 |
| --- | --- | --- | --- | --- | --- |
| P1 | 日历状态 | 过期 `localStorage` 会覆盖当前页面日期和月份 | `initCalendar()` 只要存在 `savedDate` 就使用保存值设置 `selectedDateText`、`displayYear`、`displayMonth` | 从新日期页面进入时，按钮文本和日历选中态可能停留在上次点击日期，用户误以为当前页面不是实际日期 | 页面加载时应以 `currentDateStr` 为权威，只在打开日历或跨页回访时校验保存日期是否等于当前页面日期；不一致时清理或覆盖 `localStorage` |
| P2 | 日历兼容性 | 当前日期解析依赖 DOM 文本和 `new Date()` 宽松解析 | `currentDateStr` 通过替换中文字符得到 `YYYY-MM-DD`，再传入 `new Date(currentDateStr)` | 部分浏览器或异常模板空值下可能得到 `Invalid Date`，导致月份渲染异常 | 直接由后端注入安全的 `currentDate = {year, month, day, ymd}`，避免从展示文本反解析 |
| P2 | 页面交互 | 低分论文分割线插在普通论文最后之后，而不是低分论文之前 | `normalPapers[normalPapers.length - 1]` 后插入 divider；但低分论文默认 `display:none` | “点击展开更多论文（评分较低）”的位置可能出现在所有可见普通论文之后，低分论文展开后追加在分割线之前或附近，层级语义不清 | 按 `collapsed-level-2` 的第一个元素插入分割线，或将低分论文包进单独容器 |
| P2 | 可维护性 | `app.js` 与内联 `collapse_js` 同时绑定筛选按钮 | `app.js` 绑定 `show-all/show-selected` 仅更新样式，内联脚本再次绑定并执行实际显示/隐藏 | 双重监听增加未来改动时的竞态和认知成本，按钮 class 可能被两个来源覆盖 | 将筛选、折叠、日历统一迁移到静态 `app.js`，Python 只负责注入数据 JSON 或 `data-*` 配置 |
| P2 | 数据副作用 | `load_paper_data()` 原地修改 JSON 解析出的 `paper_info` | 循环中执行 `paper_info['arxiv_id'] = arxiv_id` | 当前影响有限，但函数调用方复用原始对象时会出现隐式变异，不利于测试和推理 | 改为 `paper = {**paper_info, "arxiv_id": arxiv_id}`，保持输入对象不可变 |
| P3 | 展示体验 | 评分展示直接 `int(score)` 会截断小数 | 评分 8.7 展示为 `8/10`，平均分却保留 1 位小数 | 高分论文的细粒度差异被抹平，用户可能不理解排序差异 | 评分 badge 建议保留 1 位小数或统一整数规则并说明 |
| P3 | 展示体验 | `summary` 为空时核心总结区直接缺失 | 模板仅 `{% if SUMMARY %}` 才展示核心总结 | 普通论文可能只剩推荐理由和摘要入口，信息层次不稳定 | 非精选论文可显示“暂无核心总结”，或将摘要首句作为兜底 |
| P3 | 历史导航 | `availableDates` 只用于日历，没有最近有数据日期快捷入口 | 用户必须逐月翻日历寻找可点击日期 | 历史浏览效率低，跨日回看成本高 | 增加最近 7/30 个有数据日期列表、月份热力图或历史 Top 入口 |

## 功能与体验改进

### 近期可做

| Idea | 收益 | 复杂度 | 风险 | 建议 |
| --- | --- | --- | --- | --- |
| 修复日历状态以当前页面日期为准 | 避免日期错乱，提升基础可信度 | 低 | 需要处理旧 `localStorage` 兼容 | 页面加载覆盖 stale 状态，跳转点击后再保存 |
| 分类筛选与分数区间筛选 | 快速定位 `cs.IR`、`cs.CL`、高分论文 | 中 | 需要维护计数和按钮状态 | 使用前端 DOM data 属性或后端注入 JSON 配置 |
| 搜索标题/摘要/作者 | 提升每日论文发现效率 | 中 | 大页面 DOM 搜索性能需关注 | 先做本页轻量搜索和关键词高亮 |
| 统一交互脚本到 `app.js` | 降低维护成本 | 中 | 迁移时可能影响现有页面 | Python 只注入 `window.__ARXIV_PAGE_DATA__` |
| 改善空状态与 fallback 文案 | 数据不完整时页面更稳定 | 低 | 文案需要统一 | 为 summary、reasoning、authors、categories 建立统一 fallback |

### 中期增强

| Idea | 收益 | 复杂度 | 风险 | 建议 |
| --- | --- | --- | --- | --- |
| 最近有数据日期列表 | 快速回看历史日报 | 中 | 需要控制列表长度 | 后端注入按日期倒序的最近 N 天 |
| 阅读状态：已读/未读/稍后看 | 适合每天持续阅读 | 中 | localStorage 数据结构需要迁移 | 用 arXiv ID 做 key，先本地保存 |
| 收藏论文与导出列表 | 支持二次阅读和分享 | 中 | 跨设备同步暂不可用 | 本地收藏 + 复制 Markdown/BibTex 入口 |
| 主题聚合与关键词聚类 | 降低大批量论文浏览成本 | 高 | 需要额外 NLP 或 LLM 结果 | 先基于 categories 和关键词做轻量聚合 |
| 跨日 Top 论文入口 | 提升历史发现能力 | 中 | 需要读取多日数据 | 静态生成 `history_top.html` 或本页链接 |

### 远期探索

| Idea | 收益 | 复杂度 | 风险 | 建议 |
| --- | --- | --- | --- | --- |
| 趋势面板 | 观察主题热度和评分变化 | 高 | 数据聚合与展示设计成本高 | 先生成周/月聚合 JSON |
| 个性化阅读队列 | 更贴合个人兴趣 | 高 | 需要用户偏好和隐私设计 | 本地偏好优先，不引入线上依赖 |
| 单篇分享页 | 方便传播重点论文 | 高 | 静态站路由和 SEO 需要设计 | 可先支持 hash 定位和复制链接 |
| 移动端沉浸阅读模式 | 提升手机阅读体验 | 中 | 需要重新组织卡片密度 | 增加一键展开摘要和粘性筛选栏 |

## 验证记录

验证均使用本地命令和临时目录完成，不触发 DeepSeek、不发送飞书、不依赖生产 secrets、不覆盖线上 JSON/HTML 输出。

| 验证项 | 命令或方式 | 结果 |
| --- | --- | --- |
| Python 语法检查 | `python3 -m py_compile paperBotV2/arxiv_daily/generate_arxiv_html.py` | 通过 |
| 临时目录 HTML 生成 | 直接导入 `generate_html()`，输出到 `/var/folders/.../arxiv_html_ui_task6_5kbafj9a/arxiv_20260526.html` | 通过 |
| 静态资源复制 | 检查临时目录存在 `static/app.js`、`static/styles.css`、`static/tailwind.config.js`、`static/templates/` | 通过 |
| 首页重定向 | 检查临时目录 `index.html` 指向 `arxiv_20260526.html` | 通过 |
| 日历数据注入 | 检查生成 HTML 包含 `const availableDates = ...` 和 `20260526` | 通过 |
| 折叠 class 注入 | 检查生成 HTML 包含 `collapsed-level-1` 与 `collapsed-level-2` | 通过 |
| URL 安全兜底 | 构造 `javascript:alert(1)` 样本，检查未出现在 HTML 且回退到 arXiv URL | 通过 |
| 线上输出保护 | 生成命令只写入系统临时目录；验证后 `git status --short` 未出现 `paperBotV2/arxiv_daily/output/` 变更 | 通过 |

## 修复记录

本轮已按报告中的高优先级问题修复，并回溯重生成历史 HTML。

| 修复项 | 变更 | 验证 |
| --- | --- | --- |
| 日历 stale `localStorage` | 当前页面日期改为后端注入的 `currentDateConfig`，页面加载时始终以当前 HTML 日期为权威；只有保存日期等于当前页面日期时才恢复保存的月份视图 | 临时目录 smoke 和 120 个历史 HTML 全量断言均通过 |
| 日期解析兼容性 | 前端不再从 `#current-date` 展示文本反解析日期，也不再使用 `new Date('YYYY-MM-DD')` | `py_compile` 通过，生成 HTML 包含 `const currentDateConfig = ...` |
| 可用日期顺序 | `availableDates` 改为按日期升序注入 | `--all` 按日期升序生成，`index.html` 最终指向最新日期 |
| 低分论文展开 | 移除 `.collapsed-level-2` 的 `!important`，展开态可以正常覆盖隐藏态 | 全量 HTML 断言确认不存在 `display: none !important` |
| 低分分割线位置 | 分割线改为插入到第一篇 `collapsed-level-2` 低分论文之前 | 全量 HTML 断言确认使用 `firstLowScorePaper` 插入逻辑 |
| 全局收起一致性 | “展开/折叠全部”和“全部论文”会清理单篇详情的 inline display 状态 | 临时目录 smoke 覆盖脚本注入 |
| 数据副作用 | `load_paper_data()` 改为复制 `paper_info` 后追加 `arxiv_id`，不原地修改 JSON 子对象 | 临时样本验证源 JSON 文件内容未被修改 |
| 展示 fallback | 推荐理由改为 `rerank_reasoning or reasoning or '无'`，评分 badge 保留一位小数并去掉多余 `.0` | 临时样本验证 `8.7/10` 和空理由 fallback |
| 重复事件绑定 | `output/static/app.js` 移除筛选按钮事件绑定，避免与生成页内联筛选逻辑重复 | `app.js` diagnostics 无报错 |
| 回溯生成 | 新增 `generate_arxiv_html.py --all`，可批量生成 `data/*.json` 对应历史页面 | 已执行 `python3 generate_arxiv_html.py --all`，成功生成 `120/120` 个日期 |

## 后续建议

1. 下一步建议将筛选、折叠和日历逻辑继续迁移到静态 `app.js`，后端只注入结构化 JSON 配置，减少 Python 拼接大段 JS。
2. 为 `load_paper_data()`、`sanitize_url()`、`generate_html(--output)`、`availableDates` 注入和模板 fallback 增加正式单元测试。
3. 近期产品增强优先做搜索、分类筛选、分数筛选和最近有数据日期列表，收益明确且不依赖线上服务。
4. 中期可评估阅读状态、收藏、导出 Markdown/BibTeX 和跨日 Top 论文入口。
