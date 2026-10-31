"""Multi-doc library: filter by doc_ids, empty list, and dedupe ingest."""

from __future__ import annotations

from pathlib import Path

from core.index import get_retriever
from core.parse.store import clear_documents
from core.qa import FakeChatModel, answer_question
from core.tools.parse_document import ParseDocumentInput, parse_document

from tests.conftest import make_pdf


def _ingest(path: Path):
    parsed = parse_document(ParseDocumentInput(file_path=str(path)))
    assert parsed.ok and parsed.data is not None
    return parsed.data


def test_filter_to_doc_a_only(tmp_path):
    clear_documents()
    pdf_a = make_pdf(
        tmp_path / "doc_a.pdf",
        "第一节 产品说明",
        "甲型设备的额定功率为一百瓦，仅出现在文档甲。",
    )
    pdf_b = make_pdf(
        tmp_path / "doc_b.pdf",
        "第一节 产品说明",
        "乙型设备的额定功率为二百瓦，仅出现在文档乙。",
    )
    data_a = _ingest(pdf_a)
    data_b = _ingest(pdf_b)
    retriever = get_retriever("memory")
    retriever.index_chunks(data_a.chunks + data_b.chunks)

    fake = FakeChatModel("甲型设备额定功率为一百瓦。[doc_a.pdf p1]")
    result = answer_question(
        "甲型设备的额定功率是多少",
        retriever=retriever,
        chat_model=fake,
        doc_ids=[data_a.doc_id],
        top_k=6,
    )
    assert result.refused is False
    assert result.citations
    assert all(c.doc_id == data_a.doc_id for c in result.citations)
    assert all(c.file == "doc_a.pdf" for c in result.citations)


def test_empty_doc_ids_matches_nothing(tmp_path):
    clear_documents()
    pdf_a = make_pdf(
        tmp_path / "only_a.pdf",
        "第一节 概况",
        "公司主营业务为自主研发的软件产品与技术服务。",
    )
    data_a = _ingest(pdf_a)
    retriever = get_retriever("memory")
    retriever.index_chunks(data_a.chunks)
    fake = FakeChatModel("不应命中")
    result = answer_question(
        "主营业务是什么",
        retriever=retriever,
        chat_model=fake,
        doc_ids=[],
    )
    assert result.refused is True
    assert result.answer is None


def test_no_filter_searches_all(tmp_path):
    clear_documents()
    pdf_a = make_pdf(
        tmp_path / "alpha.pdf",
        "第一节 概况",
        "阿尔法产品线专注边缘计算网关。",
    )
    pdf_b = make_pdf(
        tmp_path / "beta.pdf",
        "第一节 概况",
        "贝塔产品线专注数据可视化看板。",
    )
    data_a = _ingest(pdf_a)
    data_b = _ingest(pdf_b)
    retriever = get_retriever("memory")
    retriever.index_chunks(data_a.chunks + data_b.chunks)
    fake = FakeChatModel("贝塔产品线专注数据可视化看板。[beta.pdf p1]")
    result = answer_question(
        "贝塔产品线做什么",
        retriever=retriever,
        chat_model=fake,
        doc_ids=None,
        top_k=8,
    )
    assert result.refused is False
    assert any(c.doc_id == data_b.doc_id for c in result.citations)


def test_duplicate_ingest_same_doc_id(tmp_path):
    clear_documents()
    pdf = make_pdf(
        tmp_path / "same.pdf",
        "第一节 概况",
        "重复入库检测用的正文，内容保持不变。",
    )
    first = _ingest(pdf)
    copy = tmp_path / "same_copy.pdf"
    copy.write_bytes(pdf.read_bytes())
    second = _ingest(copy)
    assert first.doc_id == second.doc_id
    # App-level dedupe: tracking set behaves like session_state.documents
    seen = {first.doc_id: {"file": "same.pdf", "pages": first.pages, "chunks": len(first.chunks)}}
    assert second.doc_id in seen
