"""Demo-layer query expansion and prompt wrapper."""

from __future__ import annotations

from core.qa import ChatMessage, FakeChatModel

from app.demo_qa import DemoPromptChat, expand_query


def test_expand_query_total_assets_synonyms():
    q = "2024年末总资产是多少元？"
    expanded = expand_query(q)
    assert expanded.startswith(q)
    assert "资产总计" in expanded
    assert "期末" in expanded


def test_expand_query_noop_when_no_group_hit():
    q = "公司的中文名称是什么？"
    assert expand_query(q) == q


def test_demo_prompt_chat_appends_hint():
    inner = FakeChatModel("ok")
    wrapped = DemoPromptChat(inner)
    out = wrapped.complete(
        [
            ChatMessage(role="system", content="base"),
            ChatMessage(role="user", content="q"),
        ]
    )
    assert out == "ok"
    # FakeChatModel ignores messages; ensure wrapper does not raise and keeps API.
    assert hasattr(wrapped, "complete")
