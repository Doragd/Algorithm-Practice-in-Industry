# Tasks
- [ ] Task 1: 梳理 arxiv_daily 当前逻辑：阅读 `paperBotV2/arxiv_daily/` 和相关 workflow，确认实际入口、环境变量、数据输入输出和执行顺序。
  - [ ] SubTask 1.1: 梳理 `arxiv.py` 的抓取、过滤、粗排、精排、翻译和数据落盘流程。
  - [ ] SubTask 1.2: 梳理 `generate_arxiv_html.py` 的 HTML 生成逻辑和输出目录。
  - [ ] SubTask 1.3: 梳理 `arxiv_feishu_msg.py` 的通知触发、消息格式和跳过条件。
  - [ ] SubTask 1.4: 梳理 `arxiv_daily_full.yml`、`arxiv_feishu_msg.yml` 和 legacy arXiv workflow 的命令差异。
- [ ] Task 2: Review 缺陷与改进点：从逻辑正确性、健壮性、安全、性能、可维护性和线上无损角度检查 arxiv_daily 链路。
  - [ ] SubTask 2.1: 标注明确 bug 或高风险行为，给出文件、逻辑位置和影响。
  - [ ] SubTask 2.2: 标注中低风险改进点，说明收益和实施成本。
  - [ ] SubTask 2.3: 区分必须修复、建议优化和可暂缓问题。
- [ ] Task 3: 执行安全验证：使用不触发真实线上副作用的命令验证关键结论。
  - [ ] SubTask 3.1: 对相关 Python 文件执行语法或导入级检查。
  - [ ] SubTask 3.2: 对 arXiv 主流程使用空密钥或低风险参数做 smoke test。
  - [ ] SubTask 3.3: 对 HTML 生成和飞书通知做安全验证，并记录未真实执行的边界。
- [ ] Task 4: 产出 docs 报告：在 `docs/` 目录新增结构化 Markdown 文档。
  - [ ] SubTask 4.1: 报告包含当前逻辑梳理。
  - [ ] SubTask 4.2: 报告包含问题清单、严重度、证据、影响和建议方案。
  - [ ] SubTask 4.3: 报告包含验证命令、验证结果和后续实施建议。

# Task Dependencies
- Task 2 depends on Task 1.
- Task 3 depends on Task 2.
- Task 4 depends on Task 1, Task 2, and Task 3.
