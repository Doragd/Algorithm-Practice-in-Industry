# PaperBotV2 安全重构实施 Spec

## Why
上一阶段报告已经确认 `paperBotV2` 是当前主线，但部分 GitHub Actions 和顶层旧脚本仍可能被手动或 Issue 触发，存在重复推送、数据分叉和 README 被旧格式覆盖的风险。本次需要按重构计划开始实施，同时保证每个改动可回溯、可验证，并尽量不影响线上自动化。

## What Changes
- 在新分支上实施改动，保留 Git 历史和可回溯记录。
- 优先迁移或冻结仍指向顶层旧脚本的自动化入口，避免线上流程继续写入旧数据路径。
- 将旧 arXiv 手动工作流归档到 `legacy/workflows/`，线上仅保留 `arxiv_daily_full.yml` 与 `arxiv_feishu_msg.yml`。
- 将会议更新工作流迁移到 `paperBotV2/conf_summary` 已有链路，避免 README 和会议 Markdown 回退到顶层 `papers/`。
- 将顶层旧脚本以原始内容移动到 `legacy/` 目录，并通过文档说明替代入口；本阶段不修改旧脚本内容、不删除历史数据。
- 对每个工作流和脚本入口做静态验证、dry-run 或最小化本地验证，证明对线上计划任务无损。

## Impact
- Affected specs: `document-paperbotv2-refactor` 报告中的实施阶段。
- Affected code: `.github/workflows/`、顶层旧脚本说明、`paperBotV2/conf_summary/`、`paperBotV2/arxiv_daily/`、`docs/`。

## ADDED Requirements
### Requirement: 新分支实施与可回溯记录
系统 SHALL 在开始修改前创建或切换到新的重构分支，并记录当前基础分支、工作区状态和变更范围。

#### Scenario: 开始实施重构
- **WHEN** 执行本次重构任务
- **THEN** 所有改动位于新分支，且能通过 Git diff 查看完整变更

### Requirement: 线上无损验证
系统 SHALL 为每类改动提供验证方式，至少包括 workflow 语法/引用检查、脚本入口可导入或可执行检查、关键产物路径不变检查。

#### Scenario: 验证 workflow 改动
- **WHEN** 修改 GitHub Actions 调用入口
- **THEN** 能证明 schedule、workflow_dispatch、Issue label 触发路径不会调用已废弃脚本，且输出目录仍指向线上使用的路径

### Requirement: arXiv 入口归档
系统 SHALL 将旧 arXiv 手动工作流移出 `.github/workflows/` 并归档到 `legacy/workflows/`，避免继续提供重复的线上触发入口。

#### Scenario: 查看线上 arXiv workflow
- **WHEN** 维护者查看 `.github/workflows/`
- **THEN** arXiv 线上入口只包含 `arxiv_daily_full.yml` 和 `arxiv_feishu_msg.yml`

### Requirement: 会议入口迁移
系统 SHALL 将会议相关自动化入口迁移到 `paperBotV2/conf_summary`，并保证 README 顶会链接和会议 Markdown 产物保持新版目录结构。

#### Scenario: Issue 触发会议更新
- **WHEN** Issue 带有会议更新标签
- **THEN** 工作流调用 `paperBotV2/conf_summary` 的爬取、转换和 README 更新链路，不再生成顶层 `papers/` 作为主产物

### Requirement: Legacy 目录归档
系统 SHALL 将仍暂时保留的顶层旧脚本移动到 `legacy/` 目录，并在文档中提供清晰的 legacy/deprecated 说明，指导后续使用者转向 `paperBotV2`。

#### Scenario: 维护者查找旧脚本
- **WHEN** 维护者在仓库根目录查找旧脚本
- **THEN** 旧脚本位于 `legacy/` 目录，且相关文档明确说明后续功能应在 `paperBotV2` 内演进

## MODIFIED Requirements
### Requirement: 项目自动化入口
项目自动化入口 SHALL 以 `paperBotV2` 为主线；旧脚本只能作为临时兼容或历史参考，不再作为线上主路径。

## REMOVED Requirements
### Requirement: 直接删除旧脚本
**Reason**: 直接删除旧脚本风险较高，可能破坏手动回滚、历史数据复核或未识别的人工调用。
**Migration**: 本阶段先迁移入口并将旧脚本归档到 `legacy/`；待新路径连续验证通过后，再在后续变更中删除归档副本或归档旧数据。
