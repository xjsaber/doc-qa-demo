"""Capture real Streamlit screenshots with Playwright (no staged image edits).

Usage (repo root, venv active):

    python scripts/screenshots.py

Uses two on-the-fly synthetic PDFs under output/ (gitignored). For cited-answer
shots, sets DOC_QA_FAKE_CHAT_REPLY so the UI path runs offline without API_KEY.
Retrieval-only shot clears API_KEY. Prefers system Chrome/Edge.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parents[1]
IMAGES = REPO / "docs" / "images"
OUTPUT = REPO / "output"


def _make_pdf(path: Path, title: str, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 60), title, fontname="china-s", fontsize=18)
        remaining = page.insert_textbox(
            (50, 100, 540, 740),
            body + ("补充段落用于切块。" * 40),
            fontname="china-s",
            fontsize=11,
        )
        assert remaining >= 0
        pdf.save(path)
    return path


def _start_streamlit(port: int, env: dict) -> subprocess.Popen:
    log_dir = OUTPUT
    log_dir.mkdir(parents=True, exist_ok=True)
    log = open(log_dir / f"streamlit-{port}.log", "w", encoding="utf-8")  # noqa: SIM115
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(REPO / "app" / "app.py"),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    merged = os.environ.copy()
    merged.update(env)
    merged.setdefault("PYTHONUNBUFFERED", "1")
    return subprocess.Popen(cmd, cwd=str(REPO), env=merged, stdout=log, stderr=subprocess.STDOUT)


def _wait_http(url: str, timeout: float = 120.0) -> None:
    import urllib.request

    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1.0)
    raise RuntimeError(f"Streamlit not ready at {url}: {last_err}")


def _launch_browser(playwright):
    last_err: Exception | None = None
    for channel in ("chrome", "msedge", None):
        try:
            if channel:
                return playwright.chromium.launch(headless=True, channel=channel)
            return playwright.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    raise RuntimeError(f"Unable to launch browser: {last_err}")


_IDLE_JS = """
() => {
  const status = document.querySelector('[data-testid="stStatusWidget"]');
  const running = status && status.offsetParent !== null && /Running|Stop|运行/i.test(status.innerText || "");
  const stopBtn = Array.from(document.querySelectorAll('header button, [data-testid="stToolbar"] button'))
    .some(b => /^\\s*Stop\\s*$/i.test(b.innerText || ""));
  const stale = document.querySelectorAll('[data-stale="true"], .stale-element').length > 0;
  return !running && !stopBtn && !stale;
}
"""


def wait_idle(page, timeout: float = 120.0, settle_ms: int = 1500) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page.evaluate(_IDLE_JS):
            page.wait_for_timeout(settle_ms)
            if page.evaluate(_IDLE_JS):
                return
        page.wait_for_timeout(500)
    raise RuntimeError("Streamlit still running — not capturing")


def _upload(page, pdf: Path) -> None:
    locator = page.locator('input[type="file"]')
    locator.wait_for(state="attached", timeout=60_000)
    locator.set_input_files(str(pdf))
    page.wait_for_timeout(800)
    page.get_by_role("button", name="解析并入库").click()
    page.get_by_text(f"已入库 {pdf.name}", exact=False).wait_for(timeout=180_000)
    wait_idle(page)



def capture_all(port: int = 8511) -> None:
    from playwright.sync_api import sync_playwright

    pdf_a = _make_pdf(
        OUTPUT / "shot-a.pdf",
        "第一节 产品说明",
        "甲型设备的额定功率为一百瓦，仅出现在文档甲。甲型设备支持本地部署。",
    )
    pdf_b = _make_pdf(
        OUTPUT / "shot-b.pdf",
        "第一节 产品说明",
        "乙型设备的额定功率为二百瓦，仅出现在文档乙。乙型设备侧重可视化。",
    )

    # --- cited + expand (fake chat, multi-doc filter) ---
    env_cited = {
        "RETRIEVER": "memory",
        "EMBEDDING_BACKEND": "fake",
        "DOC_QA_FAKE_CHAT_REPLY": "甲型设备额定功率为一百瓦。[shot-a.pdf p1]",
    }
    env_cited.pop("API_KEY", None)
    # Ensure empty key for auto_build path when fake reply unset; here fake is set.
    proc = _start_streamlit(port, env_cited)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_http(url)
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(1500)
            _upload(page, pdf_a)
            _upload(page, pdf_b)
            # filter to A if multiselect visible
            try:
                page.get_by_text("提问范围", exact=False).wait_for(timeout=5_000)
                # open multiselect and pick first option containing shot-a
                combo = page.locator('[data-baseweb="select"]').first
                if combo.count():
                    combo.click()
                    page.get_by_text("shot-a", exact=False).first.click()
                    page.keyboard.press("Escape")
                    wait_idle(page)
            except Exception:  # noqa: BLE001
                pass

            page.get_by_test_id("stMain").get_by_label("提问", exact=True).fill("甲型设备的额定功率是多少？")
            page.get_by_role("button", name="检索并回答").click()
            page.get_by_text("命中原文", exact=True).wait_for(timeout=180_000)
            wait_idle(page)
            page.screenshot(path=str(IMAGES / "qa-multidoc-cited.png"))

            # expand first citation for page preview
            exp = page.locator('[data-testid="stExpander"]').first
            if exp.count():
                exp.click()
                page.get_by_text("本页原文", exact=False).wait_for(timeout=30_000)
                wait_idle(page)
            page.screenshot(path=str(IMAGES / "qa-cite-expand.png"))
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    # --- retrieval only ---
    env_ro = {
        "RETRIEVER": "memory",
        "EMBEDDING_BACKEND": "fake",
    }
    # clear fake reply and API_KEY
    proc2 = _start_streamlit(port + 1, env_ro)
    # Force no key in child: strip from inherited env inside helper by setting empty
    # Re-start with explicit cleared vars
    proc2.terminate()
    try:
        proc2.wait(timeout=5)
    except Exception:  # noqa: BLE001
        proc2.kill()

    clean = os.environ.copy()
    clean.update(env_ro)
    clean["API_KEY"] = ""
    clean.pop("DOC_QA_FAKE_CHAT_REPLY", None)
    log = open(OUTPUT / f"streamlit-{port+1}.log", "w", encoding="utf-8")  # noqa: SIM115
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(REPO / "app" / "app.py"),
        "--server.port", str(port + 1), "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    proc3 = subprocess.Popen(cmd, cwd=str(REPO), env=clean, stdout=log, stderr=subprocess.STDOUT)
    url2 = f"http://127.0.0.1:{port+1}"
    try:
        _wait_http(url2)
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url2, wait_until="networkidle")
            page.wait_for_timeout(1500)
            _upload(page, pdf_a)
            page.get_by_test_id("stMain").get_by_label("提问", exact=True).fill("甲型设备的额定功率是多少？")
            page.get_by_role("button", name="检索并回答").click()
            page.get_by_text("未配置模型，仅展示检索结果", exact=False).wait_for(timeout=180_000)
            wait_idle(page)
            page.screenshot(path=str(IMAGES / "qa-retrieval-only.png"))
            browser.close()
    finally:
        proc3.terminate()
        try:
            proc3.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc3.kill()


def main() -> int:
    IMAGES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in ("qa-multidoc-cited.png", "qa-cite-expand.png", "qa-retrieval-only.png"):
        target = IMAGES / name
        if target.exists():
            target.unlink()
    print("Capturing screenshots…")
    capture_all()
    print("Wrote docs/images/qa-multidoc-cited.png, qa-cite-expand.png, qa-retrieval-only.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
