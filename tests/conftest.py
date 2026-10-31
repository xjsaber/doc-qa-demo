"""Synthetic PDFs for offline tests (fake embedding, no network)."""

from __future__ import annotations

import pymupdf
import pytest


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("RETRIEVER", "memory")
    monkeypatch.setenv("EMBEDDING_BACKEND", "fake")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("DOC_QA_FAKE_CHAT_REPLY", raising=False)


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "synthetic.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 60), "第一节 公司概况", fontname="china-s", fontsize=18)
        text = "公司主营业务为自主研发的软件产品与技术服务。" + "持续投入研发。" * 40
        remaining = page.insert_textbox((50, 100, 540, 700), text, fontname="china-s", fontsize=11)
        assert remaining >= 0
        pdf.save(path)
    return path


def make_pdf(path, title: str, body: str):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 60), title, fontname="china-s", fontsize=18)
        remaining = page.insert_textbox(
            (50, 100, 540, 700), body + ("补充说明。" * 30), fontname="china-s", fontsize=11
        )
        assert remaining >= 0
        pdf.save(path)
    return path
