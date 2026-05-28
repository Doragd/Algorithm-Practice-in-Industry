# paperBotV2 arxiv_daily 逻辑 Review Spec

## Why
`paperBotV2.arxiv_daily` 已成为当前 arXiv 主线入口，需要系统梳理现有流程、识别潜在缺陷和改进点，避免后续线上定时任务、飞书推送和页面产物出现隐性回归。

## What Changes
- 产出一份新的 Markdown 评审报告到 `docs/` 目录。
- 报告先梳理 `paperBotV2.arxiv_daily` 当前完整逻辑，包括抓取、过滤、排序、翻译、落盘、HTML 生成和飞书通知。
- 报告列出各流程中的缺陷、bug 风险、健壮性问题、性能问题和更好的解决方案。
- 报告给出优先级、影响范围、验证建议和后续重构路线。
- 不直接修改 `paperBotV2.arxiv_daily` 代码；本次先产出 review 文档供后续实施使用。

## Impact
- Affected specs: arXiv 每日论文处理、arXiv HTML 页面生成、arXiv 飞书通知、GitHub Actions arXiv workflow。
- Affected code: `paperBotV2/arxiv_daily/`、`.github/workflows/arxiv_daily_full.yml`、`.github/workflows/arxiv_feishu_msg.yml`、`legacy/workflows/` 中旧 arXiv workflow。
- Affected docs: `docs/` 新增 arXiv daily review Markdown 报告。

## ADDED Requirements
### Requirement: arxiv_daily 流程梳理报告
系统 SHALL 在 `docs/` 目录新增 Markdown 报告，清晰说明 `paperBotV2.arxiv_daily` 当前实际逻辑和自动化入口。

#### Scenario: 成功产出流程梳理
- **WHEN** 开发者阅读新增报告
- **THEN** 能理解 arXiv daily 从 workflow 触发到数据、页面、飞书通知的完整链路

### Requirement: arxiv_daily 缺陷与改进评审
系统 SHALL 在报告中列出可复核的问题清单，并按严重度或优先级说明影响、证据和建议方案。

#### Scenario: 成功定位风险
- **WHEN** 开发者根据报告查看某个问题
- **THEN** 能找到相关文件、逻辑位置、潜在影响和推荐修复方向

### Requirement: 无线上副作用验证
系统 SHALL 使用静态阅读和安全命令验证 review 结论，不触发真实飞书发送、不调用生产密钥、不破坏现有数据文件。

#### Scenario: 安全验证
- **WHEN** 执行本次 review 验证
- **THEN** 不产生线上推送、不依赖真实 secrets，且报告记录验证边界

## MODIFIED Requirements
### Requirement: 现有重构报告补充关系
本次 review 报告 SHALL 与已有 `docs/paperbotv2-refactor-report.md` 保持互补关系，聚焦 `paperBotV2.arxiv_daily` 内部逻辑，不重复整体仓库重构报告。

## REMOVED Requirements
### Requirement: 直接修改 arxiv_daily 源代码
**Reason**: 用户当前要求是仔细 review、梳理逻辑和产出 docs 报告，未要求立即修复代码。
**Migration**: 将修复建议写入报告，后续如需实施再创建单独变更任务。
