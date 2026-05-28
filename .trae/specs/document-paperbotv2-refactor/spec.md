# PaperBotV2 项目梳理与重构报告 Spec

## Why
当前仓库同时存在顶层旧脚本与 `paperBotV2` 新结构，维护边界不清晰，后续开发需要一份可信的 Markdown 报告来说明项目功能、实际生效路径、遗留代码来源和重构升级方案。

## What Changes
- 梳理整个仓库的功能模块、数据流、自动化流程与产物目录。
- 解释顶层脚本文件与 `paperBotV2` 并存的原因，并标明当前实际生效的是 `paperBotV2`。
- 给出从旧脚本迁移到 `paperBotV2` 的重构策略，包括保留、迁移、删除、兼容和验证建议。
- 在 `docs/` 目录产出 Markdown 报告，供后续开发、清理和升级使用。
- 不直接删除旧代码；本次变更先产出分析报告和重构路线。

## Impact
- Affected specs: 项目文档、重构规划、维护指南。
- Affected code: `README.md`、顶层 Python 脚本、`paperBotV2/`、`.github/workflows/`、数据目录与输出目录。

## ADDED Requirements
### Requirement: 仓库功能全景报告
系统 SHALL 产出一份 Markdown 报告，覆盖仓库主要功能模块、目录结构、脚本职责、数据输入输出和自动化工作流。

#### Scenario: 完整理解项目功能
- **WHEN** 维护者阅读报告
- **THEN** 能理解仓库提供的 arXiv 每日论文、顶会论文汇总、行业实践文章、HTML 页面生成和 GitHub Actions 自动化能力

### Requirement: 新旧脚本关系说明
系统 SHALL 说明顶层脚本与 `paperBotV2` 的关系，识别旧脚本可能的历史作用、当前入口和仍被引用的风险点。

#### Scenario: 判断实际生效路径
- **WHEN** 维护者需要判断当前运行路径
- **THEN** 报告明确指出实际生效模块、工作流调用入口和旧脚本是否仍被自动化引用

### Requirement: PaperBotV2 升级重构方案
系统 SHALL 提供可执行的重构路线，目标是以 `paperBotV2` 为唯一主线，逐步去除老旧代码和重复逻辑。

#### Scenario: 后续执行重构
- **WHEN** 维护者准备清理旧代码
- **THEN** 报告提供分阶段任务、风险控制、验证方式和回滚建议

### Requirement: Markdown 报告落地
系统 SHALL 将报告以 Markdown 形式放入 `docs/` 目录，文件名清晰表达主题。

#### Scenario: 复用报告
- **WHEN** 后续开发者查找项目重构依据
- **THEN** 能在 `docs/` 下直接找到该报告并用于后续实施

## MODIFIED Requirements
### Requirement: 项目维护文档
现有项目文档能力 SHALL 增加一份面向重构和维护的专题报告，补足 `README.md` 对新旧结构关系说明不足的问题。

## REMOVED Requirements
### Requirement: 无
**Reason**: 本次为报告和重构规划产出，不直接移除功能或代码。
**Migration**: 后续按照报告中的阶段性方案执行迁移和删除。
