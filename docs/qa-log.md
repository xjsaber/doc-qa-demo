# 人工问答记录（代理初判，待作者复核）

模型：deepseek-flash；嵌入：local / BAAI/bge-small-zh-v1.5；日期：2026-11-02。
文档 A：公开年报 PDF；文档 B：现场生成开源产品说明 PDF（均不入库）。

| 问题 | 筛选范围 | 回答摘要 | 引用页 | 判断（代理初判，待作者复核） | 备注 |
| --- | --- | --- | --- | --- | --- |
| 公司的股票代码是多少？ | 年报 | 公司股票代码是 002161 [public-annual-report-2024.pdf p6]。 | public-annual-report-2024.pdf p6, public-annual-report-2024.pdf p23, public-annual-report-2024.pdf p19, public-annual-report-2024.pdf p24, public-annual-report-2024.pdf p175, public-annual-report-2024.pdf p7, public-annual-report-2024.pdf p169 | 正确 |  |
| 公司的法定代表人是谁？ | 年报 | 公司法定代表人是孙迎军 [public-annual-report-2024.pdf p88]。 | public-annual-report-2024.pdf p38, public-annual-report-2024.pdf p34, public-annual-report-2024.pdf p4, public-annual-report-2024.pdf p60, public-annual-report-2024.pdf p88, public-annual-report-2024.pdf p51, public-annual-report-2024.pdf p169 | 正确 |  |
| 公司的注册地址是哪里？ | 年报 | 公司的注册地址是：深圳市南山区粤海街道高新南十道63号高新区联合总部大厦27、28楼 [public-annual-report-2024.pdf p88] [public-annual-report-2024.pdf p6]。 | public-annual-report-2024.pdf p88, public-annual-report-2024.pdf p6, public-annual-report-2024.pdf p4, public-annual-report-2024.pdf p89, public-annual-report-2024.pdf p7, public-annual-report-2024.pdf p63 | 正确 |  |
| 公司的中文名称是什么？ | 年报 | 公司的中文名称是：深圳市远望谷信息技术股份有限公司 [public-annual-report-2024.pdf p6]。 | public-annual-report-2024.pdf p6, public-annual-report-2024.pdf p5, public-annual-report-2024.pdf p42, public-annual-report-2024.pdf p24, public-annual-report-2024.pdf p10, public-annual-report-2024.pdf p4, public-annual-report-2024.pdf p40, public-annual-report-2024.pdf p19 | 正确 |  |
| 2024年营业收入是多少元？ | 年报 | 2024年营业收入为 545,680,493.10 元 [public-annual-report-2024.pdf p7]。同一数据亦见 [public-annual-report-2024.pdf p18]。 | public-annual-report-2024.pdf p7, public-annual-report-2024.pdf p22, public-annual-report-2024.pdf p18, public-annual-report-2024.pdf p71, public-annual-report-2024.pdf p152, public-annual-report-2024.pdf p184 | 正确 |  |
| 2024年末总资产是多少元？ | 年报 | 资料中未找到依据 |  | 误拒 | 不应拒答 |
| 量子力学术语ZXQ黑洞熵是多少？ | 年报 | 资料中未找到依据 |  | 正确拒答 |  |
| 公司在火星设立了几个分公司？ | 年报 | 资料中未找到依据 |  | 正确拒答 |  |
| 开源文档助手的核心能力包括哪些？ | 文档B | 开源文档助手的核心能力包括：  1. 本地解析：支持常见 PDF 文本层提取，并保留页码元数据 [opensource-product-note.pdf p1]。 2. 混合检索：向量召回与关键词召回可并行，结果按分数合并 [opensource-product-note.pdf p1]。 3. 引用约束：回答必须附带 | opensource-product-note.pdf p1, opensource-product-note.pdf p3, opensource-product-note.pdf p2 | 正确 |  |
| 开源文档助手默认在 Windows 上使用什么检索后端？ | 仅年报(应拒答) | 资料中未找到依据 |  | 正确拒答 |  |

### 第3轮复测（2026-11-02）

误拒原因：**已召回但仍拒答**（top-k 含「总资产」与 2,699,505,021.46；core 提示下模型输出「资料中未找到依据」）。demo 层修复后追加一行如下（保留上方原「误拒」记录）。

| 问题 | 筛选范围 | 回答摘要 | 引用页 | 判断（代理初判，待作者复核） | 备注 |
| --- | --- | --- | --- | --- | --- |
| 2024年末总资产是多少元？（第3轮复测） | 年报 | 2024年末总资产为 2,699,505,021.46 元。[public-annual-report-2024.pdf p7] | public-annual-report-2024.pdf p7 | 正确 | 第3轮复测：只检索已召回含「总资产」与数值；原误拒为模型读拆段表失败。demo 层同义词改写+表格提示后复测通过 |

## 统计（代理初判）

- 正确：6
- 部分：0
- 错误：0
- 正确拒答：3
- 误拒：1（原记录保留）
- 第3轮复测新增：正确 1（原误拒题，不计入上方合计重算）
- 合计：10（第2轮）+ 复测 1
