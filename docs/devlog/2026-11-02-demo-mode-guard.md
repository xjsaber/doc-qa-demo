# demo-mode-guard（2026-11-02）

## 决策
- DOC_QA_FAKE_CHAT_REPLY 仅在 DOC_QA_DEMO_MODE=1 时生效；页面顶部 st.warning 提示「演示模式：回答为预设文本，非模型生成」。
- 只检索模式标题改为「检索结果（N 条）」。
- 上传改用 	empfile.TemporaryDirectory()，目录内保留原文件名，退出即清理。
- 高亮断言改为只检查 <mark>；加强 _highlight_snippet 的空白不敏感匹配，避免弱断言。
- CI setup-python 增加 cache: pip。
- README Windows 激活改为 .\.venv\Scripts\Activate.ps1；写明 Python ≥3.12 与本机实测 3.12.10。

## 嵌入
- doc2report-agent v1.0.0 core 仅支持 EMBEDDING_BACKEND=local|fake，无 API 嵌入后端。
- 本机使用 EMBEDDING_BACKEND=local + 已缓存的 BAAI/bge-small-zh-v1.5（local_files_only=True），未执行 --download-model。
- DeepSeek 聊天：BASE_URL=https://api.deepseek.com，MODEL=deepseek-flash（Key 仅在本机 .env）。

## 环境
- 系统：Windows 11（NT 10.0.26300）
- Python：3.12.10（venv）
- GPU：加载本地嵌入时由 sentence-transformers 自动选择可用设备

## 人工确认
- 截图与真实模型问答留到后续任务。
