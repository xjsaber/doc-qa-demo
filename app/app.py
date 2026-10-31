"""Streamlit document Q&A page powered by doc2report-agent core."""

from __future__ import annotations

from pathlib import Path
import os
import tempfile

import streamlit as st

from core.index import get_retriever
from core.qa import FakeChatModel, answer_question, load_dotenv_config
from core.qa.answer import Citation, split_cited_citations
from core.parse.store import get_document
from core.tools.parse_document import ParseDocumentInput, parse_document


def _init_state() -> None:
    if "retriever" not in st.session_state:
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
    reply = os.getenv("DOC_QA_FAKE_CHAT_REPLY")
    if reply:
        return FakeChatModel(reply)
    return None


def _highlight_snippet(page_text: str, snippet: str) -> str:
    """Minimal HTML highlight of cited snippet inside page text (escape first)."""
    import html
    import re

    raw_page = page_text or ""
    raw_snip = (snippet or "").strip()
    safe = html.escape(raw_page)
    if not raw_snip:
        return f"<pre style='white-space:pre-wrap'>{safe}</pre>"

    # Prefer longest prefix of the citation that still appears in the page
    # (chunking may insert different newlines than page.text).
    needle_raw = None
    compact_page = re.sub(r"\s+", "", raw_page)
    for size in (len(raw_snip), 80, 40, 20, 12):
        if size > len(raw_snip):
            continue
        candidate = raw_snip[:size].strip()
        if candidate and candidate in raw_page:
            needle_raw = candidate
            break
        compact_cand = re.sub(r"\s+", "", candidate)
        if compact_cand and compact_cand in compact_page:
            # map compact match back to a short literal from the page
            # fall through to highlight the first 12 non-space chars via regex
            pattern = ".{0,2}".join(map(re.escape, list(compact_cand[:16])))
            m = re.search(pattern, raw_page)
            if m:
                needle_raw = m.group(0)
                break
    if not needle_raw:
        return f"<pre style='white-space:pre-wrap'>{safe}</pre>"
    needle = html.escape(needle_raw)
    if needle not in safe:
        return f"<pre style='white-space:pre-wrap'>{safe}</pre>"
    marked = safe.replace(needle, f"<mark>{needle}</mark>", 1)
    return f"<pre style='white-space:pre-wrap'>{marked}</pre>"


def _page_text(doc_id: str, page: int) -> str:
    document = get_document(doc_id)
    if document is None:
        return ""
    for p in document.pages:
        if p.page == page:
            return p.text or ""
    return ""


def _render_citation(citation: Citation, *, cited: bool) -> None:
    tag = "已引用 · " if cited else ""
    with st.expander(f"{tag}{citation.label}  score={citation.score:.4f}"):
        if citation.section:
            st.caption(f"章节：{citation.section} · doc_id={citation.doc_id}")
        else:
            st.caption(f"doc_id={citation.doc_id}")
        st.write(citation.text)
        page_body = _page_text(citation.doc_id, citation.page)
        if page_body:
            st.markdown("**本页原文**")
            st.markdown(_highlight_snippet(page_body, citation.text), unsafe_allow_html=True)


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

    selected_doc_ids: list[str] | None = None
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

        docs = st.session_state.documents
        if not docs:
            docs_slot.write("暂无文档")
            selected_doc_ids = None
        else:
            lines = [
                f"- {meta['file']}（{meta['pages']} 页 / {meta['chunks']} 块）"
                for meta in docs.values()
            ]
            docs_slot.markdown("\n".join(lines))
            options = {f"{m['file']}（{m['doc_id'][:8]}…）": did for did, m in docs.items()}
            chosen = st.multiselect(
                "提问范围（不选=全部）",
                options=list(options.keys()),
                default=[],
            )
            if chosen:
                selected_doc_ids = [options[label] for label in chosen]
            else:
                selected_doc_ids = None

    question = st.text_input("提问", placeholder="例如：主营业务是什么？")
    top_k = st.slider("召回条数", min_value=1, max_value=20, value=8)
    if st.button("检索并回答", type="primary"):
        fake = _optional_fake_chat()
        result = answer_question(
            question,
            retriever=st.session_state.retriever,
            top_k=top_k,
            doc_ids=selected_doc_ids,
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
