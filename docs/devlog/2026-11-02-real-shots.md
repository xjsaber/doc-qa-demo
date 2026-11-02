# real-shots（2026-11-02）

## 决策
- scripts/screenshots.py 改为参数传入 --pdf-a / --pdf-b，默认读 .env 真实模型；去掉 DOC_QA_FAKE_CHAT_REPLY。
- 文档 A：公开年报 public-annual-report-2024.pdf（与 doc2report 实跑同份，不提交）。
- 文档 B：现场生成 3 页开源产品说明 opensource-product-note.pdf（主题不同，不提交）。
- 重拍：qa-multidoc-cited / qa-cite-expand / qa-refuse / qa-retrieval-only，1440×900。
- 嵌入：doc2report-agent v1.0.0 仅 local|fake；本次 EMBEDDING_BACKEND=local + 本机已缓存 BAAI/bge-small-zh-v1.5，未 --download-model，无 API 嵌入后端可用。

## 坑
- Streamlit 1.66 多选框不再是 [data-baseweb=select]，改用 [data-testid=stMultiSelect]。
- 展开引用后页面上有多处「本页原文」，get_by_text 需避免 strict mode；改为等 mark 并滚动到高亮。
- 年报 185 页入库较慢（解析+本地向量）。

## 环境
- Windows 11 / Python 3.12.10 / 本地嵌入自动选设备
- 模型：deepseek-flash

## 人工确认
- 四张图已打开检查：无演示模式横幅、无用户名路径；筛选可见年报；expand 有高亮；refuse 与只检索文案正确。
