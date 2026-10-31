# 2026-11-01 cite-preview

## 环境
- 系统：Windows / PowerShell 5.1
- Python：3.14.7（venv 在 F:，junction 到仓库 `.venv`）
- GPU：未用（截图与测试均为 `EMBEDDING_BACKEND=fake`）

## 决策
- 引用展开：`get_document(doc_id).pages` 取页文本，`<mark>` 高亮命中片段（切块换行与页文本不一致时回退到最长可匹配前缀）
- 无 `API_KEY`：展示「未配置模型，仅展示检索结果」并用 `AnswerResult.retrieval_only`
- 截图：现场生成两份小 PDF（不提交）；带引用两张用 `DOC_QA_FAKE_CHAT_REPLY`；只检索清空 Key；1440×900；等 idle 再截

## 坑
- Playwright `get_by_text("已入库")` 与侧栏标题「已入库文档」冲突；改为匹配 `已入库 {filename}`
- `get_by_label("提问")` 与「提问范围」冲突；改为 `stMain` 内 exact label

## 测试
- 本机：`8 passed`

## 人工确认项
- 请在 GitHub Actions 确认本轮 workflow 绿

## 缺的 core 接口
- 可选：`get_page_text(doc_id, page) -> str`（当前用 `get_document` 包装）
- 可选：问答页一键 FakeChat / demo 开关（当前仅截图脚本用环境变量）
