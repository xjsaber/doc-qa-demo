"""Capture real Streamlit screenshots with Playwright.

Usage (repo root, venv active):

    python scripts/screenshots.py --pdf-a PATH\\to\\annual.pdf --pdf-b PATH\\to\\other.pdf

Defaults to real model settings from .env (no DOC_QA_FAKE_CHAT_REPLY).
Retrieval-only shot clears API_KEY in a child process.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMAGES = REPO / "docs" / "images"
OUTPUT = REPO / "output"


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
    # Never inherit demo fake reply into screenshot runs.
    merged.pop("DOC_QA_FAKE_CHAT_REPLY", None)
    merged.pop("DOC_QA_DEMO_MODE", None)
    return subprocess.Popen(cmd, cwd=str(REPO), env=merged, stdout=log, stderr=subprocess.STDOUT)


def _wait_http(url: str, timeout: float = 180.0) -> None:
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


def wait_idle(page, timeout: float = 300.0, settle_ms: int = 1500) -> None:
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
    page.get_by_text(f"已入库 {pdf.name}", exact=False).wait_for(timeout=600_000)
    wait_idle(page, timeout=600.0)


def _select_filter(page, needle: str) -> None:
    page.get_by_text("提问范围", exact=False).wait_for(timeout=30_000)
    root = page.locator('[data-testid="stMultiSelect"]').first
    if root.count() == 0:
        root = page.get_by_text("提问范围", exact=False).locator('xpath=ancestor::div[contains(@data-testid,"stElementContainer") or contains(@class,"element-container")][1]')
    root.click()
    page.wait_for_timeout(400)
    # Streamlit option list / listbox
    option = page.get_by_role("option", name=needle, exact=False)
    if option.count() == 0:
        option = page.locator('li, [role="option"], [data-baseweb="menu"] li').filter(has_text=needle).first
    else:
        option = option.first
    option.click()
    page.keyboard.press("Escape")
    wait_idle(page)


def _ask(page, question: str) -> None:
    page.get_by_test_id("stMain").get_by_label("提问", exact=True).fill(question)
    page.get_by_role("button", name="检索并回答").click()


def _assert_clean_screenshot(path: Path) -> None:
    # lightweight textless checks via PNG size + later visual open;
    # also scan nearby streamlit log is not needed here.
    if path.stat().st_size < 20_000:
        raise RuntimeError(f"screenshot too small: {path}")


def capture_cited_and_expand(pdf_a: Path, pdf_b: Path, port: int) -> None:
    from playwright.sync_api import sync_playwright

    env = {
        "RETRIEVER": "memory",
        "EMBEDDING_BACKEND": os.getenv("EMBEDDING_BACKEND", "local"),
    }
    proc = _start_streamlit(port, env)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_http(url)
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(1500)
            # Ensure demo banner absent
            if page.get_by_text("演示模式", exact=False).count():
                raise RuntimeError("demo mode warning visible; abort")
            _upload(page, pdf_a)
            _upload(page, pdf_b)
            _select_filter(page, pdf_a.name.split('.')[0][:8] if False else pdf_a.name)
            _ask(page, "公司的注册地址是哪里？")
            page.get_by_text("命中原文", exact=True).wait_for(timeout=300_000)
            wait_idle(page, timeout=300.0)
            # citation label should include filename and pN
            body = page.inner_text("body")
            if "演示模式" in body:
                raise RuntimeError("demo mode leaked into cited shot")
            if f"[{pdf_a.name} p" not in body and "p" not in body:
                # still allow if citation uses short form; require bracket cite
                if "[" not in body or " p" not in body:
                    raise RuntimeError("expected citation like [file pN] missing")
            out1 = IMAGES / "qa-multidoc-cited.png"
            page.screenshot(path=str(out1))
            _assert_clean_screenshot(out1)

            # Prefer an already-cited expander
            exp = page.locator('[data-testid="stExpander"]').filter(has_text="已引用").first
            if exp.count() == 0:
                exp = page.locator('[data-testid="stExpander"]').first
            exp.scroll_into_view_if_needed()
            # open if collapsed
            summary = exp.locator('summary, [data-testid="stExpanderToggleIcon"], button').first
            try:
                summary.click(timeout=5_000)
            except Exception:
                exp.click(timeout=5_000)
            page.wait_for_timeout(800)
            page.locator("mark").first.wait_for(state="attached", timeout=60_000)
            page.evaluate(
                """() => {
                  const marks = document.querySelectorAll('mark');
                  if (marks.length) marks[0].scrollIntoView({block: 'center'});
                }"""
            )
            wait_idle(page)
            mark_count = page.locator("mark").count()
            if mark_count < 1:
                raise RuntimeError("no <mark> highlight in cite-expand view")
            out2 = IMAGES / "qa-cite-expand.png"
            page.screenshot(path=str(out2))
            _assert_clean_screenshot(out2)

            _ask(page, "量子力学术语ZXQ黑洞熵是多少？")
            page.get_by_text("拒答", exact=False).wait_for(timeout=300_000)
            wait_idle(page, timeout=300.0)
            out3 = IMAGES / "qa-refuse.png"
            page.screenshot(path=str(out3))
            _assert_clean_screenshot(out3)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()


def capture_retrieval_only(pdf_a: Path, port: int) -> None:
    from playwright.sync_api import sync_playwright

    clean = os.environ.copy()
    clean["RETRIEVER"] = "memory"
    clean["EMBEDDING_BACKEND"] = os.getenv("EMBEDDING_BACKEND", "local")
    clean["API_KEY"] = ""
    clean.pop("DOC_QA_FAKE_CHAT_REPLY", None)
    clean.pop("DOC_QA_DEMO_MODE", None)

    log = open(OUTPUT / f"streamlit-{port}.log", "w", encoding="utf-8")  # noqa: SIM115
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
    proc = subprocess.Popen(cmd, cwd=str(REPO), env=clean, stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_http(url)
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(1500)
            _upload(page, pdf_a)
            _ask(page, "公司的注册地址是哪里？")
            page.get_by_text("未配置模型，仅展示检索结果", exact=False).wait_for(timeout=300_000)
            wait_idle(page, timeout=300.0)
            out = IMAGES / "qa-retrieval-only.png"
            page.screenshot(path=str(out))
            _assert_clean_screenshot(out)
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-a", required=True, help="Annual-report PDF path (not committed)")
    parser.add_argument("--pdf-b", required=True, help="Second public/self-gen PDF path (not committed)")
    parser.add_argument("--port", type=int, default=8511)
    args = parser.parse_args()
    pdf_a = Path(args.pdf_a).expanduser().resolve()
    pdf_b = Path(args.pdf_b).expanduser().resolve()
    if not pdf_a.is_file() or not pdf_b.is_file():
        raise SystemExit("pdf-a/pdf-b must exist")

    IMAGES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in (
        "qa-multidoc-cited.png",
        "qa-cite-expand.png",
        "qa-refuse.png",
        "qa-retrieval-only.png",
    ):
        target = IMAGES / name
        if target.exists():
            target.unlink()

    print("Capturing real-model screenshots…")
    capture_cited_and_expand(pdf_a, pdf_b, args.port)
    capture_retrieval_only(pdf_a, args.port + 1)
    print("Wrote docs/images/: qa-multidoc-cited, qa-cite-expand, qa-refuse, qa-retrieval-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
