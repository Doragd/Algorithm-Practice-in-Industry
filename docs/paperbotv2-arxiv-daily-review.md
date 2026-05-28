# paperBotV2.arxiv_daily 逻辑 Review 报告

## 结论摘要

`paperBotV2.arxiv_daily` 已经是当前 arXiv 每日论文链路的主线实现，负责从 arXiv API 抓取论文、调用 DeepSeek 做粗排和精排、写入 JSON、生成 GitHub Pages 页面，并通过独立 workflow 发送飞书通知。整体链路可运行，工作流入口也已经从旧脚本迁移到 `paperBotV2`。

本次 review 未发现 P0 阻断问题，但发现 3 个 P1 和 2 个 P2 风险。最优先需要处理的是：跨日去重路径拼错、HTML 渲染未启用转义、`generate_arxiv_html.py --output` 参数必然报错。其次建议补强飞书失败观测和 arXiv 请求超时控制。

## 当前主线入口

| 入口 | 触发方式 | 主要职责 | 输出或副作用 |
| --- | --- | --- | --- |
| `.github/workflows/arxiv_daily_full.yml` | 每天 UTC 04:00 定时，或手动触发 | 安装依赖，执行 arXiv 抓取与排序，生成 HTML，提交数据并部署 Pages | `paperBotV2/arxiv_daily/data/*.json`、`paperBotV2/arxiv_daily/output/*.html`、`gh-pages/arxiv_daily` |
| `.github/workflows/arxiv_feishu_msg.yml` | `arxiv_daily_full` 成功后触发，或手动触发 | 读取当天 JSON，筛选精排论文，发送飞书模板卡片 | 飞书 webhook 消息 |
| `legacy/workflows/push_arxiv_daily.yml` | 已移入 `legacy/workflows/` | 旧 arXiv workflow 归档 | 不会被 GitHub Actions 自动识别为线上 workflow |
| `legacy/workflows/push_arxiv_daily_cl.yml` | 已移入 `legacy/workflows/` | 旧 arXiv CL workflow 归档 | 不会被 GitHub Actions 自动识别为线上 workflow |

## arxiv.py 当前逻辑

文件：`paperBotV2/arxiv_daily/arxiv.py`

### 配置读取

`arxiv.py` 在模块加载阶段读取以下环境变量：

| 环境变量 | 默认值 | 作用 |
| --- | --- | --- |
| `FEISHU_URL` | 空 | 旧内置飞书函数仍会读取，但当前主流程不再调用该函数 |
| `DEEPSEEK_API_KEY` | `None` | DeepSeek Chat Completion API Key |
| `TARGET_CATEGORYS` | `cs.IR,cs.CL,cs.CV` | arXiv 分类列表，逗号分隔 |
| `MAX_PAPERS` | `100` | 每个分类最多拉取论文数 |
| `ROUGH_SCORE_THRESHOLD` | `4` | 粗排过滤阈值 |
| `RETURN_PAPERS` | `20` | 精排和飞书通知数量上限 |

### 主处理流程

`process_papers()` 是主入口，执行顺序如下：

1. `get_papers_from_all_categories()`：遍历 `TARGET_CATEGORYS`，调用 arXiv API 获取论文，并初始化 `is_filtered=False`、`is_fine_ranked=False`。
2. `perform_rough_ranking()`：调用 `rough_rank_papers()`，基于标题使用 `PRERANK_PROMPT` 进行粗排，过滤低于 `ROUGH_SCORE_THRESHOLD` 的论文。
3. `perform_fine_ranking()`：调用 `fine_rank_papers()`，对粗排前 `RETURN_PAPERS` 篇论文使用标题和原始摘要做精排，写入 `summary`、`translation`、`rerank_relevance_score`、`rerank_reasoning` 等字段。
4. `save_results_to_json()`：将当天结果写入 `paperBotV2/arxiv_daily/data/YYYYMMDD.json`，并增量合并到 `paperBotV2/arxiv_daily/data/results.json`。

### 抓取逻辑

`get_daily_arxiv_papers()` 查询 `http://export.arxiv.org/api/query`，使用 `cat:<category> AND submittedDate:[yesterday_utc TO now_utc]` 作为搜索条件，按 `submittedDate` 降序排序。每篇论文会被转成以 `arxiv_id` 为 key 的字典，核心字段包括：

- `title`
- `url`
- `arxiv_id`
- `authors`
- `categories`
- `pub_date`
- `ori_summary`
- `summary`
- `translation`
- `relevance_score`
- `reasoning`
- `rerank_relevance_score`
- `rerank_reasoning`

### LLM 调用逻辑

`call_deepseek_api()` 使用 OpenAI SDK 兼容 DeepSeek API，请求 `deepseek-chat`，并设置 `response_format={'type': 'json_object'}`。函数通过 `tenacity` 对 `APIConnectionError`、`RateLimitError`、`APIStatusError` 做最多 5 次指数退避重试。

当前行为特点：

- 没有 `DEEPSEEK_API_KEY` 时直接返回 `None`，不会发起 API 请求。
- LLM 返回非 JSON 或字段缺失时，函数会捕获异常并返回 `None`。
- 粗排或精排单篇失败时，该论文不会进入对应成功列表。

### 数据落盘逻辑

`save_results_to_json()` 只在 `all_papers` 非空时写文件。输出包括：

- 天级文件：`paperBotV2/arxiv_daily/data/YYYYMMDD.json`
- 全量文件：`paperBotV2/arxiv_daily/data/results.json`

全量文件只新增不存在的 `arxiv_id`，不会覆盖已有论文字段。这能降低历史数据被重写的风险，但也意味着 LLM prompt 或评分策略升级后，历史数据不会自动刷新。

## generate_arxiv_html.py 当前逻辑

文件：`paperBotV2/arxiv_daily/generate_arxiv_html.py`

### 输入选择

`main()` 默认从 `paperBotV2/arxiv_daily/data/` 中选择最新日期 JSON，排除 `results.json`。也支持：

- `--date YYYYMMDD`：指定某一天的 `data/YYYYMMDD.json`。
- `--output path`：指定 HTML 输出文件路径。

### 页面生成流程

`generate_html()` 的主要步骤：

1. 计算展示日期、论文总数、精选论文数量、平均分。
2. 准备 `paperBotV2/arxiv_daily/output/` 与 `output/static/templates/`。
3. 复制 `frontend` 下的 `styles.css`、`tailwind.config.js`、`app.js`、`index.html` 和模板文件到 `output/static/`。
4. 调用 `generate_papers_html()` 渲染精选和普通论文卡片。
5. 将统计数据、日期选择器、论文 HTML 注入页面模板。
6. 注入折叠/展开逻辑、日历逻辑和 cache-busting 时间戳。
7. 写入 `output/arxiv_YYYYMMDD.html` 和 `output/index.html`。

### 卡片排序和展示逻辑

`generate_papers_html()` 会先按是否精选排序，再按 `rerank_relevance_score` 或 `relevance_score` 降序排序。精选论文使用 `selected_paper_template.html`，普通论文使用 `normal_paper_template.html`。

非精选论文会按分数折叠：

- 精选论文：默认完全展开。
- 普通论文且分数 > 1：默认只展示标题，详情折叠。
- 普通论文且分数 <= 1：默认隐藏在低分区域后。

## arxiv_feishu_msg.py 当前逻辑

文件：`paperBotV2/arxiv_daily/arxiv_feishu_msg.py`

### 输入和跳过条件

`main()` 读取 `paperBotV2/arxiv_daily/data/` 下最新日期 JSON，且要求文件名日期等于运行当天日期。若最新文件不是当天，会直接退出，避免手动或后置触发时重复发送历史论文。

飞书发送前还会检查：

- `FEISHU_URL` 是否为空。
- 是否加载到论文数据。
- 是否存在 `is_fine_ranked=True` 且包含 `rerank_relevance_score` 的论文。

### 消息选择和格式

脚本筛选精排论文后按 `rerank_relevance_score` 降序排序，最多发送 `RETURN_PAPERS` 篇。飞书卡片使用模板：

- `template_id`: `AAqxH62u1uNko`
- `template_version_name`: `1.0.8`

模板变量包括：

- `paper`: Markdown 论文链接
- `translation`: 中文标题或翻译
- `score`: 星级和分数标签
- `summary`: 论文总结
- `date`: 当前日期

## Workflow 当前逻辑

### arxiv_daily_full.yml

当前主流程如下：

1. `actions/checkout@v3`，已开启 `lfs: true`。
2. 设置 Python 3.8。
3. 安装 `requirements.txt`。
4. 执行 `python -m paperBotV2.arxiv_daily.arxiv`。
5. 进入 `paperBotV2/arxiv_daily` 执行 `python generate_arxiv_html.py`。
6. 检查 `output/` 和 `data/`。
7. 如有 diff，提交并 push。
8. 使用 `peaceiris/actions-gh-pages@v3` 部署 `paperBotV2/arxiv_daily/output` 到 `gh-pages` 的 `arxiv_daily` 目录。

### arxiv_feishu_msg.yml

当前通知流程如下：

1. 在 `arxiv_daily_full` workflow 成功后自动触发，也支持手动触发。
2. `actions/checkout@v3`，已开启 `lfs: true`。
3. 设置 Python 3.8 并安装依赖。
4. 进入 `paperBotV2/arxiv_daily` 执行 `python arxiv_feishu_msg.py`。

## 问题清单

### P1: 前一天数据路径拼错，跨日去重实际失效

- 位置：`paperBotV2/arxiv_daily/arxiv.py` 的 `get_papers_from_all_categories()`。
- 证据：`current_dir` 已经是 `paperBotV2/arxiv_daily`，但 `yesterday_file` 拼成了 `current_dir/arxiv_daily/YYYYMMDD.json`。
- 实际保存路径：`paperBotV2/arxiv_daily/data/YYYYMMDD.json`。
- 影响：前一天论文 ID 集合几乎永远为空，跨日重复论文不会被过滤。
- 风险：重复推送、重复 LLM 调用、成本增加、用户体验下降。
- 建议：改成 `os.path.join(current_dir, "data", f"{yesterday:%Y%m%d}.json")`，并补一个临时前一天 JSON 的去重测试。

### P1: HTML 渲染未启用自动转义，存在页面注入风险

- 位置：`paperBotV2/arxiv_daily/generate_arxiv_html.py` 的 `render_template()` 和 `generate_papers_html()`。
- 证据：代码使用 `Template(template_content)`，Jinja2 默认 `autoescape=False`。
- 输入来源：arXiv feed 的标题、作者、摘要、分类，以及 DeepSeek 生成的 summary/reasoning/translation。
- 影响：如果上游文本含 HTML、事件属性或恶意 URL，可能被原样写入 GitHub Pages 页面。
- 验证：构造包含 `<img src=x onerror=alert(1)>` 和 `javascript:alert(1)` 的论文样本时，渲染结果中 payload 未被转义。
- 建议：使用 `jinja2.Environment(autoescape=select_autoescape(['html', 'xml']))`；对手工拼接的 `CATEGORY_TAGS` 使用 `html.escape`；对 URL 做协议白名单校验，只允许 `https://arxiv.org/`、`https://www.alphaxiv.org/` 等可信域名。

### P1: `generate_arxiv_html.py --output` 会触发 `output_dir` 未定义

- 位置：`paperBotV2/arxiv_daily/generate_arxiv_html.py` 的 `generate_html()`。
- 证据：只有 `output_file is None` 时才定义 `output_dir`，但后续无条件执行 `static_dir = os.path.join(output_dir, "static")`。
- 影响：CLI 暴露了 `--output` 参数，但任何指定输出路径的调用都会触发 `UnboundLocalError`。
- 风险：手动生成指定路径页面、调试脚本或未来 workflow 使用该参数时失败。
- 建议：函数开头统一计算 `output_dir`：如果指定 `output_file`，使用 `os.path.dirname(os.path.abspath(output_file))`；否则使用默认 `script_dir/output`。

### P2: 飞书 webhook 非 2xx 或业务失败不会让 workflow 失败

- 位置：`paperBotV2/arxiv_daily/arxiv_feishu_msg.py` 的 `send_papers_to_feishu()`。
- 证据：`requests.post()` 后只打印 `status_code`，没有 `raise_for_status()`，也没有解析飞书业务错误码。
- 影响：webhook 失效、限流、模板变量错误、权限错误时，workflow 仍可能显示成功，但用户收不到消息。
- 建议：对 HTTP 非 2xx 调用 `raise_for_status()`；记录响应体摘要；解析飞书返回的业务 code；汇总失败 webhook 数量，必要时以非 0 退出。

### P2: arXiv HTTP 请求没有 timeout

- 位置：`paperBotV2/arxiv_daily/arxiv.py` 的 `get_daily_arxiv_papers()`。
- 证据：`requests.get(base_url, params=query_params)` 未设置 `timeout`。
- 影响：arXiv API 网络半开或服务长时间无响应时，GitHub Actions 任务可能挂到默认超时，阻塞后续 HTML 部署和飞书通知。
- 建议：设置 `timeout=(5, 30)`，并配合有限重试；workflow 层增加 `timeout-minutes` 和 `concurrency`，避免定时任务堆积。

## 改进建议

### 必须优先修复

1. 修复前一天去重路径，避免重复论文跨日进入 LLM 和飞书链路。
2. 修复 HTML 转义和 URL 白名单，避免公开页面注入风险。
3. 修复 `--output` 参数，保证 CLI 行为与帮助说明一致。

### 建议尽快优化

1. 飞书发送失败应显式失败或至少汇总失败数，避免“workflow 成功但消息没发出”。
2. arXiv API 请求设置 timeout 和 retry，workflow 设置 `timeout-minutes` 与 `concurrency`。
3. 将 `arxiv.py` 内已废弃的 `send_papers_to_feishu()` 删除或迁移到公共通知模块，避免两个飞书模板版本并存。
4. 对 LLM 返回字段做 schema 校验，缺字段时保留原论文并标记失败原因，而不是静默丢失到成功列表之外。

### 可暂缓优化

1. `save_results_to_json()` 当前不会刷新历史全量结果，可后续增加手动 refresh 模式。
2. `generate_arxiv_html.py` 中大量内联 CSS/JS 可以后续拆回前端资源，降低维护成本。
3. `get_latest_json_file()` 仅按文件名排序，建议后续对 `YYYYMMDD.json` 做格式过滤，避免误选非日期 JSON。

## 验证记录

本次 review 使用无线上副作用方式验证，不使用真实 `DEEPSEEK_API_KEY`、不使用真实 `FEISHU_URL`、不触发真实飞书发送。

### 已执行验证

```bash
python3 - <<'PY'
import os, py_compile, tempfile
files = [
    'paperBotV2/arxiv_daily/__init__.py',
    'paperBotV2/arxiv_daily/prompts.py',
    'paperBotV2/arxiv_daily/arxiv.py',
    'paperBotV2/arxiv_daily/arxiv_feishu_msg.py',
    'paperBotV2/arxiv_daily/generate_arxiv_html.py',
]
with tempfile.TemporaryDirectory(prefix='arxiv_daily_pycompile_') as td:
    for path in files:
        cfile = os.path.join(td, path.replace('/', '__') + '.pyc')
        py_compile.compile(path, cfile=cfile, doraise=True)
        print(f'OK py_compile {path}')
PY
```

结果：5 个 arXiv daily Python 文件均可编译。

```bash
env -u FEISHU_URL -u DEEPSEEK_API_KEY RETURN_PAPERS=1 PYTHONPATH="$PWD" python3 - <<'PY'
from pathlib import Path
from paperBotV2.arxiv_daily import arxiv, arxiv_feishu_msg, generate_arxiv_html

post_calls = []
def fail_post(*args, **kwargs):
    post_calls.append((args, kwargs))
    raise AssertionError('requests.post should not be called in empty-key smoke')

arxiv.requests.post = fail_post
arxiv_feishu_msg.requests.post = fail_post
assert arxiv.call_deepseek_api('{"ping": true}', api_key='') is None
arxiv.send_papers_to_feishu([{'title':'T','url':'https://www.alphaxiv.org/abs/1','rerank_relevance_score':1,'summary':'S'}], feishu_urls=[])
arxiv_feishu_msg.send_papers_to_feishu([{'title':'T','url':'https://www.alphaxiv.org/abs/1','rerank_relevance_score':1,'summary':'S'}], feishu_urls=[])
arxiv_feishu_msg.main()
script_dir = Path('paperBotV2/arxiv_daily').resolve()
papers = generate_arxiv_html.load_paper_data(script_dir / 'data' / '20260526.json')[:1]
html = generate_arxiv_html.generate_papers_html(papers, str(script_dir / 'frontend'), str(script_dir / 'output' / 'static'))
assert html and '<script id="papers-data"' not in html
assert not post_calls, post_calls
print('OK empty-key smoke')
PY
```

结果：空 DeepSeek key 会短路；空飞书 URL 不发送；最新 JSON 非当天时飞书主流程退出；HTML 论文列表可只读渲染。

```bash
env -u FEISHU_URL -u DEEPSEEK_API_KEY PYTHONPATH="$PWD" python3 - <<'PY'
from pathlib import Path
from paperBotV2.arxiv_daily import generate_arxiv_html, arxiv_feishu_msg
root = Path('paperBotV2/arxiv_daily')
static_dir = root / 'output' / 'static'
malicious = '<img src=x onerror=alert(1)>'
paper = {
    'title': malicious,
    'translation': malicious,
    'summary': malicious,
    'ori_summary': malicious,
    'authors': malicious,
    'reasoning': malicious,
    'categories': ['cs.CL'],
    'url': 'javascript:alert(1)',
    'arxiv_id': '2501.00001',
    'rerank_relevance_score': 9,
    'is_fine_ranked': True,
}
html = generate_arxiv_html.generate_papers_html([paper], str(root / 'frontend'), str(static_dir))
print('HTML_UNESCAPED_PAYLOAD', malicious in html)
print('HTML_JAVASCRIPT_HREF', 'href="javascript:alert(1)"' in html)
PY
```

结果：`HTML_UNESCAPED_PAYLOAD=True`，`HTML_JAVASCRIPT_HREF=True`，确认 HTML 转义风险存在。

### 未执行验证

- 未运行真实 `python -m paperBotV2.arxiv_daily.arxiv` 全流程，因为会访问 arXiv、调用 DeepSeek 并写入当天 JSON。
- 未使用真实 `FEISHU_URL`，避免误发飞书。
- 未在 GitHub Actions Python 3.8 环境中复测，仅在本地 Python 环境完成静态和 smoke 验证。

## 修复记录

截至 2026-05-28，已按本报告的问题清单完成第一轮修复：

- 已修复跨日去重路径：`arxiv.py` 现在从 `paperBotV2/arxiv_daily/data/YYYYMMDD.json` 读取前一天数据。
- 已为 arXiv API 请求增加 `timeout=(5, 30)`，避免外部服务长时间无响应时拖垮 workflow。
- 已为 HTML 模板渲染启用 Jinja2 autoescape，并对分类标签做显式转义。
- 已增加论文 URL 白名单和 fallback；不可信 URL 会回退到 `https://arxiv.org/abs/<arxiv_id>`。
- 已修复 `generate_arxiv_html.py --output <path>`，指定输出目录时可正常生成页面、静态资源目录和 `index.html`。
- 已增强飞书 webhook 失败处理：HTTP 非 2xx、非 JSON 响应或飞书业务错误会汇总并抛出 `RuntimeError`。
- 已为 `arxiv_daily_full.yml` 和 `arxiv_feishu_msg.yml` 增加 workflow concurrency 与 job `timeout-minutes`。

修复验证采用无线上副作用方式完成：

- `py_compile` 通过：`arxiv.py`、`generate_arxiv_html.py`、`arxiv_feishu_msg.py`。
- YAML 解析通过：`arxiv_daily_full.yml`、`arxiv_feishu_msg.yml`。
- 静态检查通过：确认 `requests.get(..., timeout=(5, 30))` 和 `data/YYYYMMDD.json` 去重路径存在。
- HTML 恶意样本验证通过：`<img src=x onerror=alert(1)>` 被转义，`javascript:` URL 不会进入 href。
- `--output` 验证通过：临时目录中成功生成 `arxiv_20260526.html`、`static/templates/` 和 `index.html`。
- 飞书 mock 验证通过：成功响应不抛错，HTTP 500 与业务错误码均会抛出 `RuntimeError`，空 URL 仍跳过发送。
- `git diff --check` 通过。

## 后续优化路线

首轮修复已覆盖本报告中的 5 个主要问题。后续可继续做以下增强：

1. 为去重路径、HTML 转义、URL 白名单、`--output` 和飞书失败处理补充正式单元测试。
2. 为 arXiv 请求增加更细粒度 retry 策略和分类级失败统计。
3. 清理 `arxiv.py` 内废弃飞书函数，统一通知逻辑到 `arxiv_feishu_msg.py` 或公共模块。
4. 增加 `DRY_RUN` 或 `--dry-run` 参数，方便在 CI 和本地做无副作用验证。
5. 后续在 GitHub Actions Python 3.8 环境中手动触发一次 workflow，验证真实 secrets、Pages 部署和飞书模板兼容性。
