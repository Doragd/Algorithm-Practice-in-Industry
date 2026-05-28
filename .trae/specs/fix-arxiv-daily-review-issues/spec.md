# 修复 arxiv_daily Review 问题 Spec

## Why
`paperBotV2.arxiv_daily` review 已确认存在跨日去重失效、HTML 注入、CLI 参数异常、飞书失败不可观测和外部请求无超时等问题。需要按报告建议实施修复，降低线上定时任务、GitHub Pages 和飞书通知风险。

## What Changes
- 修复 `arxiv.py` 前一天 JSON 路径，恢复跨日论文去重。
- 为 arXiv API 请求设置 timeout，并保留失败时跳过该分类的安全行为。
- 修复 `generate_arxiv_html.py --output` 指定输出路径时的 `output_dir` 未定义问题。
- 为 HTML 渲染启用安全转义，并对 URL 做基础白名单/协议校验。
- 强化 `arxiv_feishu_msg.py` 飞书发送失败处理，HTTP 或业务失败时可观测并返回失败。
- 为 arXiv workflow 增加 `timeout-minutes` 和 `concurrency`，避免任务堆积。
- 补充无线上副作用验证，更新 docs review 报告的修复状态。

## Impact
- Affected specs: arXiv 每日论文处理、arXiv HTML 生成、arXiv 飞书通知、arXiv GitHub Actions。
- Affected code: `paperBotV2/arxiv_daily/arxiv.py`、`paperBotV2/arxiv_daily/generate_arxiv_html.py`、`paperBotV2/arxiv_daily/arxiv_feishu_msg.py`、`.github/workflows/arxiv_daily_full.yml`、`.github/workflows/arxiv_feishu_msg.yml`。
- Affected docs: `docs/paperbotv2-arxiv-daily-review.md`。

## ADDED Requirements
### Requirement: 安全 HTML 渲染
系统 SHALL 对 arXiv/LLM 文本进行 HTML 转义，并阻止不可信 URL scheme 进入最终页面链接。

#### Scenario: 恶意论文字段渲染
- **WHEN** 论文标题、摘要、理由或作者包含 HTML payload
- **THEN** 生成的页面显示为文本而不是可执行 HTML

### Requirement: 可观测飞书失败
系统 SHALL 在飞书 webhook HTTP 或业务返回失败时记录失败，并通过非 0 退出码让 workflow 可感知失败。

#### Scenario: 飞书 webhook 返回失败
- **WHEN** 飞书 webhook 返回非 2xx 或业务错误码
- **THEN** 脚本汇总失败并抛出错误

## MODIFIED Requirements
### Requirement: arXiv 主流程稳定性
系统 SHALL 使用正确的数据目录读取前一天 JSON，并对 arXiv API 请求设置超时，避免重复论文和任务长时间挂起。

### Requirement: HTML CLI 输出
系统 SHALL 支持 `generate_arxiv_html.py --output <path>` 正常生成文件，并在指定输出目录下准备静态资源和 `index.html`。

### Requirement: Workflow 运行保护
系统 SHALL 为 arXiv workflow 设置合理超时和并发控制，避免外部依赖异常时任务堆积。

## REMOVED Requirements
### Requirement: 未转义渲染上游文本
**Reason**: 上游 arXiv/LLM 文本不应被信任为安全 HTML。
**Migration**: 默认按文本转义，仅允许代码生成的少量安全 HTML 片段。
