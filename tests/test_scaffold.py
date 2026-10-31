"""Scaffold: ingest one synthetic PDF, cited answer, and refuse off-topic."""

from __future__ import annotations

from core.index import get_retriever
from core.parse.store import clear_documents
from core.qa import FakeChatModel, answer_question
from core.tools.parse_document import ParseDocumentInput, parse_document


def test_ingest_and_answer_with_citation(sample_pdf):
    clear_documents()
    parsed = parse_document(ParseDocumentInput(file_path=str(sample_pdf)))
    assert parsed.ok and parsed.data is not None
    data = parsed.data
    retriever = get_retriever("memory")
    retriever.index_chunks(data.chunks)

    fake = FakeChatModel("主营业务为软件产品与技术服务。[synthetic.pdf p1]")
    result = answer_question("主营业务是什么？", retriever=retriever, chat_model=fake, top_k=4)
    assert result.refused is False
    assert result.retrieval_only is False
    assert result.answer and "[synthetic.pdf p1]" in result.answer
    assert result.citations
    assert any(c.file == "synthetic.pdf" and c.page == 1 for c in result.citations)


def test_refuse_unrelated_question(sample_pdf):
    clear_documents()
    parsed = parse_document(ParseDocumentInput(file_path=str(sample_pdf)))
    assert parsed.ok and parsed.data is not None
    retriever = get_retriever("memory")
    retriever.index_chunks(parsed.data.chunks)

    fake = FakeChatModel("不应被采用")
    result = answer_question(
        "量子力学术语ZXQ黑洞熵是多少",
        retriever=retriever,
        chat_model=fake,
        min_vector_score=0.35,
    )
    assert result.refused is True
    assert result.answer is None
    assert "依据" in (result.message or "") or "无法" in (result.message or "")
