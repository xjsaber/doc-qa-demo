"""Demo-layer query rewrite and softer table-reading prompt (does not modify core)."""

from __future__ import annotations

from typing import Sequence

from core.qa import AnswerResult, ChatMessage, answer_question, build_chat_model

# Small synonym groups for query expansion only (retrieval rewrite).
_SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("总资产", "资产总计", "资产合计"),
    ("年末", "期末"),
    ("营业收入", "营业总收入"),
    ("净利润", "归属于上市公司股东的净利润"),
)

# Appended to core system prompt when the real chat model answers.
_TABLE_HINT = (
    " 财务报表或主要会计数据表常把年份表头与指标数值拆到相邻片段："
    "请结合同页相邻片段按列对齐解读「年末/期末」对应数值；"
    "片段中已出现指标名与对应数值即可作答，勿因表头与数值不在同一片段而拒答。"
)


def expand_query(question: str) -> str:
    """Append synonym terms found via group membership; original wording kept first."""
    q = (question or "").strip()
    if not q:
        return q
    extras: list[str] = []
    for group in _SYNONYM_GROUPS:
        if any(term in q for term in group):
            for term in group:
                if term not in q and term not in extras:
                    extras.append(term)
    if not extras:
        return q
    return f"{q} {' '.join(extras)}".strip()


class DemoPromptChat:
    """Wrap a ChatModel to append demo-only table-reading hint on the system message."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def complete(self, messages: Sequence[ChatMessage]) -> str:
        rewritten: list[ChatMessage] = []
        for message in messages:
            if message.role == "system":
                rewritten.append(
                    ChatMessage(role="system", content=(message.content or "") + _TABLE_HINT)
                )
            else:
                rewritten.append(message)
        return self._inner.complete(rewritten)


def answer_question_demo(
    question: str,
    *,
    retriever,
    chat_model=None,
    doc_ids: Sequence[str] | None = None,
    top_k: int = 8,
    mode: str = "hybrid",
    auto_build_model: bool = True,
    embedder=None,
    min_vector_score: float | None = None,
) -> AnswerResult:
    """Like core answer_question, with demo query expansion + table-reading hint."""
    original = (question or "").strip()
    search_q = expand_query(original)

    model = chat_model
    build = auto_build_model
    if model is not None:
        model = DemoPromptChat(model)
        build = False
    elif build:
        built = build_chat_model()
        if built is not None:
            model = DemoPromptChat(built)
            build = False

    result = answer_question(
        search_q,
        retriever=retriever,
        chat_model=model,
        doc_ids=doc_ids,
        top_k=top_k,
        mode=mode,
        auto_build_model=build,
        embedder=embedder,
        min_vector_score=min_vector_score,
    )
    result.question = original or question or ""
    return result
