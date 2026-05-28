# Tasks
- [x] Task 1: 建立可回溯实施分支：检查当前 Git 状态，创建或切换到新的安全重构分支，并记录基础状态。
  - [x] SubTask 1.1: 查看当前分支、未提交变更和远端状态，避免覆盖用户改动。
  - [x] SubTask 1.2: 创建形如 `refactor/paperbotv2-safe-migration` 的新分支。
  - [x] SubTask 1.3: 记录本次计划修改范围和线上无损原则。
- [x] Task 2: 归档旧 arXiv 手动工作流：线上只保留 `arxiv_daily_full.yml` 与 `arxiv_feishu_msg.yml`。
  - [x] SubTask 2.1: 检查 `push_arxiv_daily.yml` 与 `push_arxiv_daily_cl.yml` 的触发、环境变量和输出路径。
  - [x] SubTask 2.2: 将 `push_arxiv_daily.yml` 与 `push_arxiv_daily_cl.yml` 移动到 `legacy/workflows/`。
  - [x] SubTask 2.3: 保留归档文件供回溯，避免 GitHub Actions 继续识别为线上 workflow。
  - [x] SubTask 2.4: 验证 `.github/workflows/` 中只保留主线 arXiv workflow，且不会写入顶层 `arxiv.json`。
- [x] Task 3: 迁移会议更新入口：优先让会议相关 workflow 使用 `paperBotV2/conf_summary` 的新版脚本和产物目录。
  - [x] SubTask 3.1: 检查 `update_confs.yml`、`push_conf_daily.yml` 与 `paperBotV2/conf_summary` 已有脚本能力。
  - [x] SubTask 3.2: 将可安全迁移的步骤改为新版 crawler、Markdown 转换和 README 更新链路。
  - [x] SubTask 3.3: 若新版能力不足以完全替代旧逻辑，保留兼容说明并避免引入破坏性删除。
  - [x] SubTask 3.4: 验证 README 顶会链接仍指向 `paperBotV2/conf_summary/data/papers/`，不回退到顶层 `papers/`。
- [x] Task 4: 冻结旧脚本并补充迁移说明：将顶层旧脚本以原始内容移动到 `legacy/`，并在文档中说明主线入口。
  - [x] SubTask 4.1: 创建 `legacy/` 目录并移动旧脚本，避免修改旧脚本源文件内容。
  - [x] SubTask 4.2: 避免删除历史数据，保证可回滚和可复核。
  - [x] SubTask 4.3: 更新 `docs/paperbotv2-refactor-report.md` 的实施状态，记录本次已完成迁移。
- [x] Task 5: 做线上无损验证并记录结果：对所有改动做静态检查、引用检查和最小化运行验证。
  - [x] SubTask 5.1: 检查 YAML 语法和 workflow 中旧脚本引用是否已消除或有明确 legacy 标识。
  - [x] SubTask 5.2: 检查相关 Python 模块可导入或脚本帮助信息可运行，不依赖真实线上 webhook。
  - [x] SubTask 5.3: 检查关键输出路径仍为 `paperBotV2/arxiv_daily/output/`、`paperBotV2/industry_practice/output/`、`paperBotV2/conf_summary/data/papers/`。
  - [x] SubTask 5.4: 将验证命令、结果和残余风险写入报告或实施记录。

# Task Dependencies
- Task 2 depends on Task 1.
- Task 3 depends on Task 1.
- Task 4 depends on Task 2 and Task 3.
- Task 5 depends on Task 2, Task 3, and Task 4.
