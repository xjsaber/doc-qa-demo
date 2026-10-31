# AGENTS.md（给 Codex / 助手的开发约定）

## 红线
- 核心能力只通过 `doc2report-agent` v1.0.0 的公开 core 接口获得，见上游 `docs/core-api.md`。不要复制 core 源码，也不要改 `doc2report-agent` 仓库。
- 只用公开文档或本仓库测试现场生成的小 PDF；不引用任何机构内部代码、模板、提示词或数据。
- 不提交 `.env`、API key、PDF、向量库文件、模型权重、`output/`。提交前 `git status` 自查。
- README / 代码 / devlog 不出现银行、金融、客户、本职单位名称；不出现本机用户目录路径。

## 工作方式
1. 本仓库是薄 Demo：Streamlit 问答页 + 测试 + 文档。缺上游接口时在 `docs/devlog/` 记「需要 core 新增什么」，本仓用最小包装绕开。
2. 每个任务单独 commit 并 push；冲突先 `pull --rebase`，不得强推；不打 tag。
3. 测试默认 `EMBEDDING_BACKEND=fake` + `FakeChatModel`，不联网、不下模型。
4. 效果数字只写本机实测；截图必须来自真实页面，不做示意拼图。
