# PaperBotV2 项目梳理与重构报告

## 结论摘要

本仓库从“搜广推工业实践文章收集”起步，随后扩展出 arXiv 每日论文推送、顶会论文汇总、行业实践网页和 GitHub Actions 自动化。当前代码同时保留顶层旧脚本和 `paperBotV2/` 新结构，维护边界不清晰。

综合 README、脚本目录和工作流调用关系，当前主线应以 `paperBotV2` 为准：arXiv 每日处理、HTML 页面生成、飞书消息补发和行业实践页面更新均已迁入 `paperBotV2`；README 中顶会论文列表也指向 `paperBotV2/conf_summary/data/papers/`。但部分 GitHub Actions 仍会调用顶层旧脚本，说明旧代码尚未完全下线，后续重构需要分阶段迁移和验证，不能直接删除。

## 实施基础状态

Task 1 已从 `main...origin/main` 创建并切换到 `refactor/paperbotv2-safe-migration` 分支。创建前的 `git status --short --branch` 显示存在未跟踪的 `.trae/` 与 `docs/`，本次只记录状态并保留这些现有改动，不执行清理、重置或覆盖操作。

本次安全迁移的计划修改范围限定为 GitHub Actions 入口、`legacy/` 归档目录、实施报告和必要的最小验证记录。线上无损原则是：旧脚本只做目录级归档、不修改脚本内容，不删除历史数据，不改变已生效的 `paperBotV2` 输出目录，不触发真实线上 webhook，不让 README 顶会链接回退到顶层 `papers/`。

### 实施状态更新

截至 2026-05-28，Task 2 和 Task 3 已完成可安全迁移部分：旧 arXiv 手动工作流已归档到 `legacy/workflows/`，线上只保留 `arxiv_daily_full.yml` 与 `arxiv_feishu_msg.yml`；`update_confs.yml` 已迁移到 `paperBotV2/conf_summary` 链路；`push_conf_daily.yml` 因新版尚未完全替代旧飞书日推和私有 `CONF_URL` 摘要补全能力，暂时保留 `legacy/conf.py` 兼容调用，但已停止运行会把 README 链接回退到顶层 `papers/` 的旧 `legacy/render.py`。

Task 4 已调整完成：顶层旧脚本不再通过修改源文件添加提示，而是以原始内容归档到 `legacy/` 目录；`README.md` 已补充 legacy 入口说明，明确当前主线入口为 `paperBotV2/arxiv_daily/`、`paperBotV2/conf_summary/` 和 `paperBotV2/industry_practice/`。本次未删除顶层历史数据文件或 `papers/` 历史产物，保留回滚与复核能力。

## 仓库功能全景

### 主要功能

| 功能 | 当前承载位置 | 输入 | 输出 | 说明 |
| --- | --- | --- | --- | --- |
| 行业实践文章收集 | `paperBotV2/industry_practice/`、`README.md`、`source.xlsx` | GitHub Issue、文章元数据 | `README.md` 表格、`article.json`、`article.csv`、HTML 页面 | 原始能力来自顶层 `maintain.py` 和 `source.xlsx`，新实现已迁入 `paperBotV2/industry_practice/` |
| arXiv 每日论文 | `paperBotV2/arxiv_daily/` | arXiv API、DeepSeek、环境变量 | 日级 JSON、全量 `results.json`、HTML 页面、飞书卡片 | 新版以多分类抓取、粗排、精排、页面生成为主线 |
| 顶会论文汇总 | `paperBotV2/conf_summary/`、顶层旧脚本 | DBLP、会议配置、摘要源 | `data/results.json`、会议 Markdown、README 顶会表格 | 新目录已有爬取、摘要补全、Markdown 转换、README 更新工具，但部分工作流仍调用顶层旧脚本 |
| GitHub Pages | `paperBotV2/arxiv_daily/output/`、`paperBotV2/industry_practice/output/` | JSON 数据、Jinja2 模板、静态资源 | `gh-pages` 下 `arxiv_daily/` 和 `industry_practice/` | arXiv 和行业实践都有网页化产物 |
| 自动化入口 | `.github/workflows/` | schedule、workflow_dispatch、issues labeled、workflow_run | 数据提交、Pages 部署、飞书通知 | 入口混合了新旧脚本，是当前重构重点 |

### 顶层目录与文件

| 路径 | 用途判断 | 当前状态 |
| --- | --- | --- |
| `README.md` | 项目首页，包含仓库介绍、论文推送 Bot、顶会论文表和行业实践文章表 | 仍是核心展示文件，顶会链接已指向 `paperBotV2/conf_summary/data/papers/` |
| `requirements.txt` | Python 依赖，包含 `feedparser`、`openai`、`tenacity`、`tqdm`、`beautifulsoup4`、`aiohttp`、`requests`、`jinja2` | 新旧脚本共用 |
| `source.xlsx` | 早期行业实践文章数据源，README 提到可执行自定义排序 | 旧数据源，`paperBotV2/industry_practice` 已有 JSON/CSV 数据源 |
| `arxiv.json` | 顶层旧 arXiv 脚本缓存翻译结果 | 旧数据产物，仍可能被手动旧工作流使用 |
| `results.json` | 顶层旧顶会脚本缓存会议论文与摘要 | 旧数据产物，仍可能被旧会议工作流使用 |
| `papers/` | 顶层旧 `render.py` 生成的会议 Markdown | 历史产物，README 当前主链接转向 `paperBotV2/conf_summary/data/papers/` |
| `搜广推优质博主文章.md`、`搜广推算法系列串讲.md` | 手工维护的扩展内容 | 可保留为内容资产 |
| `.trae/specs/document-paperbotv2-refactor/` | 本次文档任务的 spec、checklist、tasks | 任务管理资料 |

### 顶层旧脚本

| 脚本 | 职责 | 被引用情况 | 与新版关系 |
| --- | --- | --- | --- |
| `legacy/arxiv.py` | 查询单个 arXiv 分类，翻译摘要，推送飞书或 ServerChan，并维护 `arxiv.json` | 原 `push_arxiv_daily.yml`、`push_arxiv_daily_cl.yml` 已归档到 `legacy/workflows/`，不在线触发 | 被 `paperBotV2/arxiv_daily/arxiv.py` 替代；新版支持多分类、LLM 粗排/精排、HTML 数据 |
| `conf.py` | 基于 `results.json` 补全顶会摘要、翻译并推送飞书 | `push_conf_daily.yml` 手动触发调用 | 被 `paperBotV2/conf_summary` 的数据结构和处理脚本逐步替代 |
| `crawler.py` | 从 DBLP 抓取会议论文列表并写入 `results.json` | `update.py` 间接调用 | `paperBotV2/conf_summary/crawler.py` 是增强版，支持更多会议与重试策略 |
| `citer.py` | 基于 DOI/Crossref 补充引用数 | `update.py` 间接调用 | 新版会议数据不再以引用数为核心字段，保留为历史能力 |
| `render.py` | 将顶层 `results.json` 渲染为 `papers/` 下 Markdown，并更新 README 顶会表 | `push_conf_daily.yml`、`update_confs.yml` 调用 | 新版应由 `paperBotV2/conf_summary/convert_to_md.py` 和 `update_readme_papers.py` 替代 |
| `update.py` | 解析 Issue 中的会议参数，触发 `crawler.py`、`citer.py` | `update_confs.yml` 调用 | 需要迁移到 `paperBotV2/conf_summary` 入口 |
| `maintain.py` | 早期行业实践 Issue 解析、更新 `source.xlsx`/README、飞书通知 | 未被当前工作流调用 | 被 `paperBotV2/industry_practice/maintain.py` 替代 |
| `translate.py` | DeepSeek/Caiyun 翻译客户端 | 顶层旧 `arxiv.py`、`conf.py` 使用 | 可迁移为公共工具，或限定为 legacy 依赖 |

## PaperBotV2 模块盘点

### `paperBotV2/arxiv_daily`

`arxiv.py` 是新版 arXiv 主处理入口。它从环境变量读取 `TARGET_CATEGORYS`、`MAX_PAPERS`、`ROUGH_SCORE_THRESHOLD`、`RETURN_PAPERS`、`DEEPSEEK_API_KEY` 和 `FEISHU_URL`，按分类查询 arXiv API，使用 DeepSeek 做粗排和精排，并将结果写入 `paperBotV2/arxiv_daily/data/YYYYMMDD.json` 与 `paperBotV2/arxiv_daily/data/results.json`。

`generate_arxiv_html.py` 读取 JSON 数据和静态模板，生成日级 HTML 与索引页面，输出到 `paperBotV2/arxiv_daily/output/`。输出目录含 `static/`、模板、样式与历史日级页面，是 GitHub Pages 发布源。

`arxiv_feishu_msg.py` 从 `data/` 中选择最新日级 JSON，校验日期为当天后，根据精排分数选取论文并发送飞书消息。它将“数据处理/网页生成”和“消息发送”拆成两个自动化阶段，避免页面未部署时提前推送。

`prompts.py` 保存粗排和精排提示词，是新版筛选逻辑的核心配置文件。

### `paperBotV2/conf_summary`

`crawler.py` 从 DBLP 按会议和年份抓取论文列表，当前字段更贴近推荐展示：论文名、链接、作者、摘要、作者机构、标题翻译、推荐分和推荐理由。相比顶层 `crawler.py`，新版支持 `nips/neurips` 路径、重试、随机延迟和更丰富的会议范围。

`get_free_abstract.py` 面向 ACL/NAACL/EMNLP/ICLR 等开放页面补全摘要，支持按会议模式和数量限制筛选空摘要论文，是对旧 `conf.py` 中通过私有 `CONF_URL` 补摘要方式的替代方向。

`convert_to_md.py` 将 `data/results.json` 转成 `data/papers/<conf>/<conf><year>.md`，生成包含序号、标题、推荐理由、推荐度、摘要、作者、组织的 Markdown 表格，并对部分会议摘要做动态截断，控制文件大小。

`update_readme_papers.py` 扫描 `data/papers/`，重建 README 的顶会论文矩阵。README 当前顶会链接已经指向该目录，说明展示层已向 `paperBotV2` 靠拢。

### `paperBotV2/industry_practice`

`maintain.py` 是当前行业实践 Issue 入口。它解析 Issue 文章元数据，更新 `data/article.json` 和 `data/article.csv`，向 README 的行业实践表插入新文章，发送飞书通知，并调用 `generate_industry_html.py` 刷新网页。

`generate_industry_html.py` 读取 `data/article.json`，转换中英文键名，按日期倒序排序，生成公司和标签筛选数据，再基于 Jinja2 模板输出 `paperBotV2/industry_practice/output/index.html`。该输出目录被 `update_content.yml` 部署到 GitHub Pages 的 `industry_practice/`。

`data/` 是结构化文章数据源，`output/` 是网页产物。相比顶层 `maintain.py` 依赖 `source.xlsx`，新版更适合自动化和网页化。

## GitHub Actions 调用关系

| 工作流 | 触发方式 | 当前调用 | 新旧归属 | 影响 |
| --- | --- | --- | --- | --- |
| `arxiv_daily_full.yml` | schedule 每天 UTC 4:00、手动 | `python -m paperBotV2.arxiv_daily.arxiv`，随后 `cd paperBotV2/arxiv_daily && python generate_arxiv_html.py`，提交并部署 Pages | 新版主线 | 当前 arXiv 日常处理和网页发布的实际主入口 |
| `arxiv_feishu_msg.yml` | `arxiv_daily_full` 成功后、手动 | `cd paperBotV2/arxiv_daily && python arxiv_feishu_msg.py` | 新版主线 | 当前 arXiv 飞书通知的实际主入口 |
| `update_content.yml` | Issue 标记 `require to update content`、手动 | `python paperBotV2/industry_practice/maintain.py --issue ...`，再部署 `paperBotV2/industry_practice/output` | 新版主线 | 当前行业实践更新入口 |
| `legacy/workflows/push_arxiv_daily.yml` | 已归档，不在 `.github/workflows/` 中触发 | `python -m paperBotV2.arxiv_daily.arxiv`，`TARGET_CATEGORYS=cs.IR` | legacy 归档 | 原旧 arXiv IR 手动入口已移出线上 workflow 目录 |
| `legacy/workflows/push_arxiv_daily_cl.yml` | 已归档，不在 `.github/workflows/` 中触发 | `python -m paperBotV2.arxiv_daily.arxiv`，`TARGET_CATEGORYS=cs.CL` | legacy 归档 | 原旧 arXiv CL 手动入口已移出线上 workflow 目录 |
| `push_conf_daily.yml` | 手动；schedule 已注释 | `python legacy/conf.py`，随后运行 `paperBotV2/conf_summary/convert_to_md.py` 与 `update_readme_papers.py` | 混合兼容 | 暂保留旧飞书日推能力，但不再运行 `legacy/render.py` 回写 README |
| `update_confs.yml` | Issue 标记 `require to update confs`、手动 | `python paperBotV2/conf_summary/update_from_issue.py --issue ...`，随后转换 Markdown 并更新 README | 新版主线 | Issue 触发的顶会新增/更新流程已迁入 `paperBotV2/conf_summary` |

自动化证据表明：arXiv 日常计划任务、arXiv 飞书后置通知、行业实践 Pages 部署和顶会 Issue 更新已经是 `paperBotV2` 路径；旧 arXiv 手动工作流已归档到 `legacy/workflows/`，不再作为线上可触发 workflow。会议日推送 `push_conf_daily.yml` 仍保留 `legacy/conf.py` 兼容调用，是后续需要补齐新版飞书日推能力后再完全迁移的遗留入口。

## 新旧代码关系

### arXiv 路径

旧 `arxiv.py` 以单分类查询、摘要翻译、飞书推送为中心，数据缓存写入顶层 `arxiv.json`。两个旧手动 workflow 已归档到 `legacy/workflows/`，不再位于 `.github/workflows/` 线上触发目录；当前线上 arXiv 主入口保留 `arxiv_daily_full.yml` 和 `arxiv_feishu_msg.yml`。

新版 `paperBotV2/arxiv_daily/arxiv.py` 支持 `cs.IR,cs.CL,cs.CV` 等多分类，使用 DeepSeek 对论文做相关性粗排和摘要精排，输出日级 JSON 和全量 JSON，再由 `generate_arxiv_html.py` 发布页面，由 `arxiv_feishu_msg.py` 发送消息。它是当前自动日更和页面发布的实际生效路径。

结论：旧 arXiv 脚本属于兼容遗留代码，已以原始内容归档到 `legacy/`，README 标注当前主线。后续可在确认无人工依赖后删除归档副本。

### 会议论文路径

旧会议路径由 `legacy/update.py`、`legacy/crawler.py`、`legacy/citer.py`、`legacy/conf.py`、`legacy/render.py` 和顶层 `results.json`/`papers/` 组成，侧重 DBLP 抓取、Crossref 引用数、私有摘要接口和 README 表格更新。Task 3 后，`update_confs.yml` 已迁入 `paperBotV2/conf_summary`；`push_conf_daily.yml` 暂保留 `legacy/conf.py` 用于旧飞书日推兼容，但不再调用会重写 README 的 `legacy/render.py`。

新版 `paperBotV2/conf_summary` 已具备 DBLP 抓取、开放摘要补全、Markdown 转换和 README 表格更新能力，README 顶会链接也已转向 `paperBotV2/conf_summary/data/papers/`。

结论：会议模块处于“Issue 更新和展示产物已迁入 `paperBotV2`，日推通知仍保留旧兼容脚本”的过渡态。下一步应补齐 `paperBotV2/conf_summary` 的飞书日推替代能力，再移除 `push_conf_daily.yml` 对 `legacy/conf.py` 的依赖。

### 行业实践路径

旧 `legacy/maintain.py` 依赖 `source.xlsx`，直接插入 README 表格并推送飞书。当前工作流没有调用该归档脚本。

新版 `paperBotV2/industry_practice/maintain.py` 以 `article.json`/`article.csv` 为结构化数据源，仍更新 README，同时生成 HTML 页面并部署 Pages。`update_content.yml` 已调用新版入口。

结论：行业实践模块已基本迁移完成，`legacy/maintain.py` 与 `source.xlsx` 可作为历史数据和回滚资产暂存，后续确认后删除归档副本或归档旧数据。

## 当前实际生效路径

当前应按以下路径理解仓库主线：

1. arXiv 日常任务：`arxiv_daily_full.yml` 调用 `paperBotV2/arxiv_daily/arxiv.py` 生成 JSON，再调用 `paperBotV2/arxiv_daily/generate_arxiv_html.py` 生成页面并部署。
2. arXiv 飞书通知：`arxiv_feishu_msg.yml` 在 `arxiv_daily_full` 成功后调用 `paperBotV2/arxiv_daily/arxiv_feishu_msg.py`。
3. 行业实践更新：`update_content.yml` 调用 `paperBotV2/industry_practice/maintain.py`，该脚本会更新数据、README、飞书消息和 HTML 页面。
4. 顶会展示：README 链接已指向 `paperBotV2/conf_summary/data/papers/`，说明展示产物以 `paperBotV2` 为准。
5. 顶会更新入口：`update_confs.yml` 已调用 `paperBotV2/conf_summary/update_from_issue.py`、`convert_to_md.py` 和 `update_readme_papers.py`；`push_conf_daily.yml` 暂时保留 `legacy/conf.py` 作为旧飞书日推兼容入口，但输出转换和 README 更新已使用 `paperBotV2/conf_summary`。

## 遗留风险

| 风险 | 影响 | 建议 |
| --- | --- | --- |
| 旧 arXiv 工作流归档后仍存在历史文件 | 维护者可能误以为 `legacy/workflows/` 内文件仍会在线触发 | 旧文件已移出 `.github/workflows/`，GitHub Actions 不会识别为线上 workflow |
| `push_conf_daily.yml` 仍调用 `legacy/conf.py` | 会议日推送仍可能写入顶层 `results.json`，与新版会议数据分叉 | 补齐 `paperBotV2/conf_summary` 飞书日推能力后再替换 `legacy/conf.py` |
| `legacy/render.py` 会重写 README 顶会区块 | 手工运行旧脚本可能覆盖 `paperBotV2/conf_summary` 生成的链接结构 | 工作流已停止调用 `legacy/render.py`，改用 `update_readme_papers.py` |
| 多套数据源并存 | `source.xlsx`、`article.json`、`arxiv.json`、多个 `results.json` 容易混淆 | 建立数据源归属表，保留一套 canonical 数据 |
| 工作流提交条件中存在旧式 `set-output` 和 shell 细节 | 后续 GitHub Actions 兼容性和可维护性较差 | 重构时同步升级为 `$GITHUB_OUTPUT` 并修正 shell 判断 |
| 脚本相对路径不一致 | 从仓库根或子目录运行时输出位置不同 | 为每个入口统一基于 `__file__` 的路径解析 |

## 重构升级方案

### 代码分类

| 类别 | 范围 | 处理策略 |
| --- | --- | --- |
| 保留主线 | `paperBotV2/arxiv_daily/`、`paperBotV2/industry_practice/`、`paperBotV2/conf_summary/`、`requirements.txt` | 作为唯一演进方向，补充入口文档和验证脚本 |
| 迁移入口 | `update_confs.yml`、`push_conf_daily.yml`、旧 arXiv 手动 workflow | 已将旧 arXiv workflow 归档到 `legacy/workflows/`；其余入口改为调用 `paperBotV2` 下模块，或改造成兼容 wrapper |
| 归档数据 | 顶层 `arxiv.json`、`results.json`、`papers/`、`source.xlsx` | 先冻结，确认无工作流写入后移到 `legacy/` 或文档注明只读 |
| 删除候选 | 顶层 `arxiv.py`、`conf.py`、`crawler.py`、`citer.py`、`render.py`、`update.py`、`maintain.py`、`translate.py` | 迁移完成且连续多轮自动化验证通过后删除 |
| 内容资产 | `搜广推优质博主文章.md`、`搜广推算法系列串讲.md` | 保留，必要时迁入 `docs/` 或 `paperBotV2/industry_practice` 内容目录 |

### 分阶段计划

第一阶段：文档与冻结。

将顶层旧脚本以原始内容移动到 `legacy/`，补充 README 或 `docs/` 入口说明，明确 `paperBotV2` 是主线。禁止新功能继续写入顶层 `arxiv.json`、`results.json` 和 `papers/`。将旧手动工作流名称或描述改为 deprecated，避免误触发。

第二阶段：迁移会议自动化。

`update_confs.yml` 已迁移为 `paperBotV2/conf_summary/update_from_issue.py`、`convert_to_md.py` 和 `update_readme_papers.py` 链路，输出保持在 `paperBotV2/conf_summary/data/`。`push_conf_daily.yml` 暂时保留 `legacy/conf.py` 用于日推兼容，但已改用 `paperBotV2/conf_summary` 生成 Markdown 和 README，避免链接回退到顶层 `papers/`。

第三阶段：统一 arXiv 与行业实践入口。

`push_arxiv_daily.yml`、`push_arxiv_daily_cl.yml` 已移出 `.github/workflows/` 并归档到 `legacy/workflows/`。线上 arXiv 入口仅保留 `arxiv_daily_full.yml` 和 `arxiv_feishu_msg.yml`；行业实践继续以 `paperBotV2/industry_practice/maintain.py` 为主入口。

第四阶段：数据归档与兼容窗口。

对顶层历史数据做一次只读归档，记录最新迁移日期、数据来源和是否仍被 README 引用。保留一个发布周期的回滚分支或 tag，确认 Pages、README 和飞书无异常后移除旧脚本。

第五阶段：清理依赖和质量提升。

统一 Python 包结构，补齐 `paperBotV2` 根包初始化，抽取通用飞书发送、日期处理、文件路径和 LLM 客户端。升级 GitHub Actions 的 checkout/setup-python 版本，替换废弃的 `::set-output`。

## 验证清单

| 场景 | 验证命令或方式 | 期望结果 |
| --- | --- | --- |
| arXiv 数据处理 | 手动运行 `arxiv_daily_full.yml` 或本地以测试环境变量执行 `python -m paperBotV2.arxiv_daily.arxiv` | `paperBotV2/arxiv_daily/data/YYYYMMDD.json` 与 `results.json` 更新 |
| arXiv 页面生成 | 在 `paperBotV2/arxiv_daily` 下运行 `python generate_arxiv_html.py` | `output/` 下生成最新 `arxiv_YYYYMMDD.html` 和索引页 |
| arXiv 飞书消息 | 手动运行 `arxiv_feishu_msg.yml`，使用测试 webhook | 仅在最新 JSON 日期为当天时发送，不重复发送旧数据 |
| 行业实践更新 | 使用测试 Issue body 调用 `python paperBotV2/industry_practice/maintain.py --issue ...` | `article.json`、`article.csv`、README 和 `output/index.html` 更新 |
| 顶会 Markdown | 在 `paperBotV2/conf_summary` 下运行转换脚本 | `data/papers/<conf>/<conf><year>.md` 生成且 README 链接稳定 |
| README 稳定性 | 对迁移前后 README diff 做人工审查 | 顶会表、行业实践表不被旧格式覆盖 |
| Pages 发布 | 检查 `peaceiris/actions-gh-pages` 发布目录 | `arxiv_daily/` 与 `industry_practice/` 页面可访问 |

### Task 5 最小化验证记录

验证日期：2026-05-28。本次只做本地静态检查、依赖安装后的导入/编译检查和空密钥分支验证，未使用真实 webhook 或生产密钥，未触发 GitHub Actions、Pages 发布、arXiv/DeepSeek 线上抓取或飞书真实发送。

| 检查项 | 命令 | 结果 |
| --- | --- | --- |
| 本地解释器确认 | `python - <<'PY' ...` | 失败，`zsh:1: command not found: python`；本机仅使用 `python3` 继续验证 |
| YAML 语法 | `python3 - <<'PY' ... yaml.safe_load(.github/workflows/*.yml) ... PY` | 原验证通过；归档旧 arXiv workflow 后需重新验证线上 `.github/workflows/` 剩余 5 个 YAML |
| 旧脚本引用 | `python3 - <<'PY' ... scan python arxiv.py/conf.py/update.py/crawler.py ... PY` | 通过：旧脚本已归档到 `legacy/`，当前仅保留 `.github/workflows/push_conf_daily.yml -> python legacy/conf.py` 的兼容调用 |
| 输出路径 | `python3 - <<'PY' ... check paperBotV2/... output/data paths ... PY` | 通过，`paperBotV2/arxiv_daily/output`、`paperBotV2/industry_practice/output`、`paperBotV2/conf_summary/data/papers` 均存在引用，README 未回退到顶层 `papers/` 链接 |
| 依赖准备 | `python3 -m pip install -r requirements.txt` | 通过，按 `requirements.txt` 安装到用户 site-packages；pip 提示脚本目录不在 `PATH`，不影响本次 Python 模块验证 |
| Python 编译 | `python3 -m py_compile paperBotV2/arxiv_daily/arxiv.py paperBotV2/arxiv_daily/arxiv_feishu_msg.py paperBotV2/arxiv_daily/generate_arxiv_html.py paperBotV2/industry_practice/maintain.py paperBotV2/conf_summary/update_from_issue.py paperBotV2/conf_summary/update_readme_papers.py paperBotV2/conf_summary/convert_to_md.py` | 通过，无语法错误 |
| Python 导入 | `python3 - <<'PY' ... importlib.import_module(...) ... PY` | 通过，`paperBotV2.arxiv_daily.arxiv`、`arxiv_feishu_msg`、`generate_arxiv_html`、`industry_practice.maintain`、`conf_summary.update_readme_papers` 均可导入 |
| 入口帮助与空密钥分支 | `python3 paperBotV2/industry_practice/maintain.py --help && python3 paperBotV2/conf_summary/update_from_issue.py --help && python3 - <<'PY' ... call_deepseek_api('', api_key=''); send_papers_to_feishu([], feishu_urls=[]) ... PY` | 通过，两个 CLI 帮助可运行；空 API key 返回错误提示且不请求 DeepSeek，空 webhook 列表打印跳过发送 |

残余风险：

- `push_conf_daily.yml` 仍保留对 `legacy/conf.py` 的兼容调用，虽然后续 Markdown/README 已转向 `paperBotV2/conf_summary`，但日推入口仍可能写入顶层会议中间数据。
- 本次未真实运行 GitHub Actions、Pages 发布、arXiv 抓取、DeepSeek 调用或飞书 webhook，仅覆盖静态和最小化本地分支。
- 本地为 Python 3.9，workflow 配置为 Python 3.8；依赖安装和导入在本机通过，但仍建议在 CI 的 Python 3.8 环境复核。
- 导入时出现 `urllib3` 关于 LibreSSL 的 `NotOpenSSLWarning`，未阻断验证，但线上运行环境如升级 urllib3/OpenSSL 仍需关注。
- `paperBotV2/conf_summary/convert_to_md.py` 含顶层文件读取/写入逻辑，本次仅做 `py_compile`，未在真实 `data/results.json` 输入上执行转换。

### Legacy 目录归档调整记录

按“冻结旧脚本不用改动源文件，直接放进 `legacy/` 文件夹”的要求，已撤销脚本头部 `LEGACY NOTICE` 方案，改为将 8 个旧脚本以 `HEAD` 中原始内容归档到 `legacy/`：`arxiv.py`、`conf.py`、`crawler.py`、`citer.py`、`render.py`、`update.py`、`maintain.py`、`translate.py`。顶层同名脚本已移除，`push_conf_daily.yml` 的兼容调用改为 `python legacy/conf.py`。

补充验证结果：`missing_legacy=[]`、`still_top=[]`、`legacy_notice=[]`；7 个 workflow YAML 均可解析；`legacy/conf.py`、`legacy/translate.py`、`paperBotV2/conf_summary/update_from_issue.py` 均通过 `py_compile`。

### Legacy Workflow 归档调整记录

按“已有 `arxiv_daily_full.yml`，其他 arXiv workflow 也变成 legacy”的要求，已将 `.github/workflows/push_arxiv_daily.yml` 与 `.github/workflows/push_arxiv_daily_cl.yml` 移动到 `legacy/workflows/`。线上 `.github/workflows/` 中当前仅保留两个 arXiv 相关 workflow：`arxiv_daily_full.yml` 和 `arxiv_feishu_msg.yml`。

补充验证结果：`active_arxiv_workflows=['arxiv_daily_full.yml', 'arxiv_feishu_msg.yml']`；`legacy_workflows=['push_arxiv_daily.yml', 'push_arxiv_daily_cl.yml']`；线上 5 个 workflow YAML 与 legacy 下 2 个归档 YAML 均可解析。

### 全量命令复测记录

按“所有改动都测试跑一次，包括之前老的 YAML 命令”的要求，已完成无线上副作用复测：

- 当前 `.github/workflows/` 下 5 个 workflow 和 `legacy/workflows/` 下 2 个归档 workflow 均通过 YAML 解析。
- 所有项目 Python 脚本均通过 `py_compile`，共 22 个脚本。
- `python -m paperBotV2.arxiv_daily.arxiv` 使用 `MAX_PAPERS=0`、空 `DEEPSEEK_API_KEY`、空 `FEISHU_URL` 完成 smoke test；未写入新 JSON。
- `paperBotV2/arxiv_daily/generate_arxiv_html.py` 可执行；测试生成的 HTML 时间戳副作用已恢复。
- `paperBotV2/arxiv_daily/arxiv_feishu_msg.py` 在无 webhook 且最新数据非当天时正确退出，未发送飞书。
- `paperBotV2/conf_summary/conf_daily.py` 使用临时 results JSON 和 `DRY_RUN=true` 通过，不请求 `CONF_URL`、不写生产数据、不发送飞书。
- `paperBotV2/conf_summary/convert_to_md.py` 使用临时有效 results JSON 通过，并生成测试 Markdown。
- `paperBotV2/conf_summary/update_from_issue.py --help` 通过。
- `paperBotV2/industry_practice/maintain.py` 的 issue parser 通过，`generate_industry_html.py` 可执行；测试生成的 HTML 时间戳副作用已恢复。
- `git diff --check` 通过，`GetDiagnostics` 无诊断问题。

本机环境没有 `git-lfs`，因此 `paperBotV2/conf_summary/data/results.json` 在本地仍是 LFS pointer，不能直接对真实大文件运行 `convert_to_md.py`。已在所有 active workflow 的 `actions/checkout` 中设置 `lfs: true`，确保 GitHub Actions 环境拉取真实 LFS 内容后再执行会议链路。

## 后续实施建议

后续优先处理 `push_conf_daily.yml` 对 `legacy/conf.py` 的兼容依赖，因为它仍可能写入顶层会议数据。旧 arXiv 手动 workflow 已归档，`update_confs.yml` 已转向 `paperBotV2`，下一阶段应补齐真实 CI 验证记录，再归档旧数据，避免在自动化入口尚未完全替换前破坏回滚能力。

每次迁移只改一个自动化入口，并在 PR 中附上运行日志、关键产物 diff 和 README 链接检查结果。若需要保留人工兼容入口，建议将旧脚本改成薄 wrapper，只打印迁移提示并转调 `paperBotV2`，而不是继续维护两套逻辑。
