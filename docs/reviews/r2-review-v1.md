# 第 2 轮评审 v1（demo-mode-guard / real-shots / qa-log / miss-fix）

评审对象：`d7c0483` `[demo-mode-guard]`、`5575dd1` `[real-shots]`、`6c22a9b` `[qa-log]`、`e641757` `[miss-fix]`（HEAD `e641757`）

## 结论：8.6 / 10，r1 阻断 B1 已解除，无新阻断

截图换成了公开年报 + 真实模型（deepseek-flash），筛选框、引用高亮、拒答、只检索四个场景都拍到了，可以对外展示。扣分在 miss-fix：为修 1 条误拒加了「勿拒答」提示，却没回归拒答题，拒答能力可能被削弱，下一轮要补上。

## 复现

- Linux（Python 3.12，新 venv，`pip install -e ".[dev]"`）：`13 passed`，与 commit 一致。
- GitHub Actions：四次 push 均 `success`。
- 未提交 PDF、`.env`、模型、output；README / 代码未出现单位或客户名称、本机用户路径；四个提交作者均为 noreply。

## 做得好的

1. 演示模式收口：`DOC_QA_FAKE_CHAT_REPLY` 只在 `DOC_QA_DEMO_MODE=1` 时生效，有正反两条测试。
2. 截图真实：185 页 / 1646 块年报 + 3 页产品说明同时入库，「提问范围」已选年报；`qa-cite-expand.png` 能看到「本页原文」的黄色高亮；README 写明模型、日期。
3. 只检索模式改为「检索结果（N 条）」，上传改用临时目录。
4. qa-log 如实记录了误拒，没有删改原记录，复测另起一行，统计口径清楚。
5. 误拒排查先用只检索确认「已召回但模型拒答」，定位到表头与数值拆段，再在 demo 层修，没有去动 core。

## 阻断

无。

## 必须在下一轮处理

**M1 拒答回归缺失**
`_TABLE_HINT` 写的是「片段中已出现指标名与对应数值即可作答，勿因表头与数值不在同一片段而拒答」，加上之后只复测了总资产一题。原来 3 道正确拒答题（ZXQ 黑洞熵、火星分公司、筛选为年报时问文档 B）必须用同一模型重跑，结果写进 qa-log；如有任何一道不再拒答，就收窄提示，例如只在问题命中财务指标同义词组时才附加。

## 建议（非阻断）

1. `answer_question_demo` 把扩写后的问题（原问题 + 同义词）直接交给 `answer_question`，模型看到的用户问题也是扩写版。更干净的做法是只用扩写串检索，生成时传原问题；core 没有分开的参数，就在 devlog「缺的 core 接口」里记一条：`answer_question(..., search_query=...)`。
2. 同义词表（总资产 / 年末 / 营业收入 / 净利润）属于年报专用规则，README 已知局限写明「仅覆盖年报常见财务指标」，避免读者以为是通用改写。
3. `test_demo_prompt_chat_appends_hint` 没有真正验证提示被追加（FakeChatModel 不看消息）。改用一个记录入参的假模型，断言 system 消息以 `_TABLE_HINT` 结尾、user 消息不变。
4. `2026-11-02-miss-fix.md` 里有 PowerShell 反引号造成的控制字符（`\a` 吞掉了 `app/`、`answer_` 的首字母）。用 Python 重写该文件，并在 docs 卫生测试里加一条：devlog 不得含 `\x00-\x08`、`\x0b`、`\x0c`、`\x0e-\x1f` 控制字符。
5. README 截图说明里「本机 commit 以 git log 为准」改成写出具体提交号 `5575dd1`。
6. qa-log 「引用页」列现在是全部召回页，和「回答实际引用页」混在一起；拆成「回答引用」和「召回页」两列。

## 作品化状态

- 截图与问答记录已够挂客栈作品 2；建议 M1 回归通过、qa-log 作者复核后再挂，并在 README 顶部加一句与 doc2report-agent 的关系和在线截图入口。
- 下一轮完成后打 `v0.1.0` tag（由作者执行）。
