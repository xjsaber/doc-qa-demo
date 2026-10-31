"""Streamlit document Q&A page powered by doc2report-agent core."""

from __future__ import annotations

from pathlib import Path
import os
import tempfile

import streamlit as st

from core.index import get_retriever
from core.qa import FakeChatModel, answer_question, load_dotenv_config
from core.qa.answer import Citation, split_cited_citations
from core.tools.parse_document import ParseDocumentInput, parse_document


def _init_state() -> None:
    if "retriever" not in st.session_state:
        # Read RETRIEVER from env via factory; do not hard-code memory.
        st.session_state.retriever = get_retriever()
    if "documents" not in st.session_state:
        st.session_state.documents = {}  # doc_id -> meta


def _ingest_pdf(path: Path) -> str:
    result = parse_document(ParseDocumentInput(file_path=str(path)))
    if not result.ok or result.data is None:
        return result.error or "解析失败"
    data = result.data
    if data.doc_id in st.session_state.documents:
        meta = st.session_state.documents[data.doc_id]
        return f"已存在：{meta['file']}（doc_id={data.doc_id[:12]}…），跳过重复入库"
    st.session_state.retriever.index_chunks(data.chunks)
    st.session_state.documents[data.doc_id] = {
        "file": path.name,
        "pages": data.pages,
        "chunks": len(data.chunks),
        "doc_id": data.doc_id,
    }
    return f"已入库 {path.name}：{data.pages} 页，{len(data.chunks)} 个片段（doc_id={data.doc_id[:12]}…）"


def _optional_fake_chat():
    """Screenshots / offline demos may inject a fixed reply via env."""
    reply = os.getenv("DOC_QA_FAKE_CHAT_REPLY")
    if reply:
        return FakeChatModel(reply)
    return None


def _render_citation(citation: Citation, *, cited: bool) -> None:
    tag = "已引用 · " if cited else ""
    with st.expander(f"{tag}{citation.label}  score={citation.score:.4f}"):
        if citation.section:
            st.caption(f"章节：{citation.section} · doc_id={citation.doc_id}")
        else:
            st.caption(f"doc_id={citation.doc_id}")
        st.write(citation.text)


def _render_hits(answer: str | None, citations: list[Citation]) -> None:
    if not citations:
        return
    cited, uncited = split_cited_citations(answer, citations)
    st.subheader("命中原文")
    for citation in cited:
        _render_citation(citation, cited=True)
    if uncited:
        st.caption(f"以下 {len(uncited)} 条为召回但回答未引用的片段")
        for citation in uncited:
            _render_citation(citation, cited=False)


def main() -> None:
    load_dotenv_config()
    st.set_page_config(page_title="文档问答 Demo", layout="wide")
    st.title("文档问答 Demo")
    st.caption("依赖 doc2report-agent v1.0.0 core：上传或填路径入库 → 提问 → 带引用回答")
    _init_state()

    with st.sidebar:
        st.header("文档入库")
        uploaded = st.file_uploader("上传 PDF（公开或自有文档）", type=["pdf"])
        ingest_clicked = st.button("解析并入库", type="primary", disabled=uploaded is None)
        existing = st.text_input("或填写本机已有 PDF 路径")
        path_clicked = st.button("从路径入库", disabled=not existing)
        message_slot = st.empty()
        st.divider()
        st.subheader("已入库文档")
        docs_slot = st.empty()

        if ingest_clicked and uploaded is not None:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = Path(tmp.name)
            try:
                display = Path(uploaded.name).name
                target = tmp_path.with_name(display)
                if target != tmp_path:
                    target.write_bytes(tmp_path.read_bytes())
                    tmp_path.unlink(missing_ok=True)
                    tmp_path = target
                st.session_state.ingest_message = _ingest_pdf(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
        if path_clicked and existing:
            path = Path(existing).expanduser()
            st.session_state.ingest_message = (
                _ingest_pdf(path) if path.is_file() else "文件不存在"
            )

        message = st.session_state.get("ingest_message")
        if message:
            ok = message.startswith("已入库") or message.startswith("已存在")
            (message_slot.success if ok else message_slot.error)(message)
        if not st.session_state.documents:
            docs_slot.write("暂无文档")
        else:
            docs_slot.markdown(
                "\n".join(
                    f"- {meta['file']}（{meta['pages']} 页 / {meta['chunks']} 块）"
                    for meta in st.session_state.documents.values()
                )
            )

    question = st.text_input("提问", placeholder="例如：主营业务是什么？")
    top_k = st.slider("召回条数", min_value=1, max_value=20, value=8)
    if st.button("检索并回答", type="primary"):
        fake = _optional_fake_chat()
        result = answer_question(
            question,
            retriever=st.session_state.retriever,
            top_k=top_k,
            chat_model=fake,
            auto_build_model=fake is None,
        )
        if result.refused:
            st.warning(result.message or "无法回答")
            st.caption("拒答时不展示命中原文，避免误当作有效依据。")
        elif result.retrieval_only:
            st.info("未配置模型，仅展示检索结果")
            st.caption(result.message or "")
            _render_hits(None, list(result.citations))
        else:
            st.markdown(result.answer or "")
            _render_hits(result.answer, list(result.citations))


if __name__ == "__main__":
    main()
