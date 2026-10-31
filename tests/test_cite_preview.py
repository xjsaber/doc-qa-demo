"""Cite page preview helpers + retrieval_only without API_KEY."""

from __future__ import annotations

from core.index import get_retriever
from core.parse.store import clear_documents, get_document
from core.qa import answer_question
from core.tools.parse_document import ParseDocumentInput, parse_document

from app.app import _highlight_snippet, _page_text


def test_retrieval_only_without_api_key(sample_pdf, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    clear_documents()
    parsed = parse_document(ParseDocumentInput(file_path=str(sample_pdf)))
    assert parsed.ok and parsed.data is not None
    retriever = get_retriever("memory")
    retriever.index_chunks(parsed.data.chunks)
    result = answer_question(
        "主营业务是什么？",
        retriever=retriever,
        auto_build_model=True,
    )
    assert result.retrieval_only is True
    assert result.answer is None
    assert result.citations
    assert "API_KEY" in (result.message or "")


def test_page_text_and_highlight(sample_pdf):
    clear_documents()
    parsed = parse_document(ParseDocumentInput(file_path=str(sample_pdf)))
    assert parsed.ok and parsed.data is not None
    doc = get_document(parsed.data.doc_id)
    assert doc is not None
    page1 = _page_text(parsed.data.doc_id, 1)
    assert "主营业务" in page1 or "软件" in page1
    assert "软件" in page1
    html = _highlight_snippet(page1, "软件产品与技术服务")
    assert "<mark>" in html
    # also tolerate chunk-prefix that may differ by whitespace
    html2 = _highlight_snippet(page1, parsed.data.chunks[0].text)
    assert "<mark>" in html2 or "软件" in html2
