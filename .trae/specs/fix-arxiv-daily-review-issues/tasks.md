# Tasks
- [x] Task 1: 修复 arXiv 主流程稳定性：修正跨日去重路径，并为 arXiv API 请求增加 timeout。
  - [x] SubTask 1.1: 将前一天文件路径改为 `paperBotV2/arxiv_daily/data/YYYYMMDD.json`。
  - [x] SubTask 1.2: 为 `requests.get` 增加连接和读取超时。
- [x] Task 2: 修复 HTML 生成安全与 CLI：启用转义、URL 白名单，并修复 `--output` 参数。
  - [x] SubTask 2.1: 使用安全的 Jinja2 Environment 或等价机制启用 HTML 转义。
  - [x] SubTask 2.2: 对分类标签和论文 URL 做安全处理。
  - [x] SubTask 2.3: 修复指定 `--output` 时 `output_dir` 未定义的问题。
- [x] Task 3: 修复飞书通知失败处理：让 webhook 失败可观测并能让脚本失败。
  - [x] SubTask 3.1: 检查 HTTP 非 2xx 并记录响应摘要。
  - [x] SubTask 3.2: 检查飞书业务返回码，汇总失败数量。
  - [x] SubTask 3.3: 有失败时抛出异常或非 0 退出。
- [x] Task 4: 加强 workflow 保护：为 arXiv workflow 增加超时和并发控制。
  - [x] SubTask 4.1: `arxiv_daily_full.yml` 设置 job 超时和 concurrency。
  - [x] SubTask 4.2: `arxiv_feishu_msg.yml` 设置 job 超时和 concurrency。
- [x] Task 5: 验证并更新文档：执行无线上副作用测试，更新 review 报告修复状态。
  - [x] SubTask 5.1: 执行 py_compile 和安全 smoke 验证。
  - [x] SubTask 5.2: 验证 HTML 恶意样本已被转义，`--output` 可用。
  - [x] SubTask 5.3: 验证飞书失败 mock 会导致脚本可感知失败。
  - [x] SubTask 5.4: 更新 `docs/paperbotv2-arxiv-daily-review.md` 的修复记录。

# Task Dependencies
- Task 2 depends on Task 1.
- Task 3 can run after Task 1.
- Task 4 can run in parallel with Task 1-3.
- Task 5 depends on Task 1, Task 2, Task 3, and Task 4.
