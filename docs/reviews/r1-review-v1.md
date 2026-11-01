# 第 1 轮评审 v1（scaffold / multi-doc / cite-preview）

评审对象：`ad040c6` `[scaffold]`、`029c79e` `[multi-doc]`、`01261ce` `[cite-preview]`（HEAD `01261ce`）
依赖：doc2report-agent `v1.0.0`（tag 已存在）

## 结论：7.8 / 10，代码可用，截图不达作品标准（1 个阻断）

骨架、依赖方式、多文档筛选、只检索模式、CI 都做对了；但三张截图用的是两份「补充段落用于切块」填充的 1 页小 PDF + 注入的固定回答，看不出这是一个能对真实文档问答的产品。作品 2 对外就靠 README 截图，这一项必须重做。

## 复现

- Linux（Python 3.12，新 venv，`pip install -e ".[dev]"`）：`8 passed`，1 条 jieba `pkg_resources` 警告。
- 依赖解析到 `doc2report-agent 1.0.0`（git tag），未复制 core 源码。
- GitHub Actions：三次 push 均 `success`。
- 敏感信息：未发现 PDF、`.env`、模型、output、本机用户路径、单位/客户名称。三个提交作者均为 noreply 邮箱（Initial commit 为 GitHub 网页创建，可忽略）。

## 做得好的

1. 薄仓库边界清楚：只用 `docs/core-api.md` 接口，缺口（`get_page_text`）记在 devlog，没去改上游。
2. `RETRIEVER` 走配置（`get_retriever()`），不再写死 memory。
3. 按 `doc_id` 去重入库并提示；`doc_ids` 筛选有「A 筛选时引用只来自 A」「空列表」「不筛选」测试。
4. 拒答时不展示命中原文；只检索模式提示文案明确。
5. 页原文高亮先 `html.escape` 再 `<mark>`，没有 XSS 口子。
6. Playwright 脚本等 idle 再截，选择器冲突的坑记录在 devlog。

## 阻断

**B1 截图不是真实文档问答场景**
- 文档是现场生成的 1 页 / 1 块填充 PDF（正文大段重复「补充段落用于切块」），截图里直接可见。
- 带引用回答来自 `DOC_QA_FAKE_CHAT_REPLY` 注入的固定字符串，不是模型生成。README 虽有说明，但效果上等同示意图。
- `qa-multidoc-cited.png` 里「提问范围」仍是空（Choose options），并没有展示多文档筛选；`qa-cite-expand.png` 只截到片段，没截到「本页原文」高亮。
- 要求：用 doc2report 那份公开年报 + 第二份公开 PDF（或明显不同主题的现场 PDF），配真实模型 Key（DeepSeek）跑出回答；筛选框里要能看到已选文档；原文展开截到 `<mark>` 高亮；Key 不入仓库、不入截图。

## 建议（非阻断）

1. `DOC_QA_FAKE_CHAT_REPLY` 留在正式 app 里不合适：改成仅在 `DOC_QA_DEMO_MODE=1` 时生效，并在页面顶部显示「演示模式：回答为预设文本」；README 截图不得用演示模式。
2. 只检索模式下仍显示「以下 1 条为召回但回答未引用的片段」，语义不对；没有回答时直接列「检索结果」。
3. README Windows 激活命令有多余空格：`.\ .venv\Scripts\Activate.ps1` → `.\.venv\Scripts\Activate.ps1`。
4. devlog 记录 Python 3.14.7，与 doc2report 约定的 3.12 不一致；README 写「≥3.12，已在 3.12 / 3.14 验证」或换回 3.12 venv。
5. 上传临时文件改名到 `tmp_path.with_name(display)`，同名并发上传会互相覆盖；改用 `TemporaryDirectory()` 下的原名文件。
6. 补 5～10 条人工问答记录（`docs/qa-log.md`：问题、回答摘要、引用页、是否正确、是否拒答），这是作品 2 的最小验收之一。
7. `test_page_text_and_highlight` 第二个断言 `"<mark>" in html2 or "软件" in html2` 恒为真，改成只断言 `<mark>`。
8. CI 里 `pip install` 加缓存（`actions/setup-python` 的 `cache: pip`）。
