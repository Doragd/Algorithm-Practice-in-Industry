# Tasks
- [x] Task 1: 梳理仓库功能与入口：阅读 `README.md`、顶层脚本、`paperBotV2/` 和 `.github/workflows/`，确认各模块职责与自动化入口。
  - [x] SubTask 1.1: 盘点顶层脚本、数据文件和历史目录的用途。
  - [x] SubTask 1.2: 盘点 `paperBotV2` 的 arXiv、会议论文、行业实践模块。
  - [x] SubTask 1.3: 盘点 GitHub Actions 对脚本的实际调用关系。
- [x] Task 2: 分析新旧代码关系：判断为什么顶层存在旧脚本、哪些可能仍被引用、哪些已被 `paperBotV2` 替代。
  - [x] SubTask 2.1: 对比同名或相近功能脚本的职责差异。
  - [x] SubTask 2.2: 标注当前实际生效路径和潜在遗留风险。
- [x] Task 3: 制定重构升级方案：输出以 `paperBotV2` 为主线的清理、迁移和验证计划。
  - [x] SubTask 3.1: 划分保留、迁移、归档、删除的代码类别。
  - [x] SubTask 3.2: 设计分阶段重构步骤，降低自动化任务和数据产物风险。
  - [x] SubTask 3.3: 给出验证清单和后续实施建议。
- [x] Task 4: 产出 Markdown 报告：在 `docs/` 目录创建项目梳理与重构报告。
  - [x] SubTask 4.1: 创建 `docs/` 目录。
  - [x] SubTask 4.2: 写入结构化 Markdown 报告。
  - [x] SubTask 4.3: 确认报告内容覆盖用户提出的四个目标。

# Task Dependencies
- Task 2 depends on Task 1.
- Task 3 depends on Task 2.
- Task 4 depends on Task 3.
