"""
Browser-driven smoke tests for the Streamlit app: launch it for real and click
through the Interactive Function Executor on the Image and Network tabs.

Unlike the presenter-level tests, these exercise the actual Streamlit
session_state / st.rerun() round-trip (app_func_img.py, app_func_net.py),
which is where UI-only bugs (e.g. state lost across a rerun) show up.

Requires Playwright's Chromium browser to be installed once:
    playwright install chromium
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

playwright_sync_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_sync_api.sync_playwright

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

read_image_fixture = os.path.join(repo_root, "runs", "Pak2D_240x200x1_5um.dat")
network_fixture = os.path.join(repo_root, "runs", "run_tst_SNM", "Pak2DExtruded_240x200x28_5p0um_ms.xmf")


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def streamlit_server():
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "porgui/app.py",
            "--server.port", str(port),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60
    up = False
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            urllib.request.urlopen(base_url, timeout=1)
            up = True
            break
        except Exception:
            time.sleep(0.5)
    if not up:
        proc.terminate()
        out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
        pytest.fail(f"streamlit server never came up on {base_url}:\n{out[-4000:]}")

    yield base_url

    os.killpg(os.getpgid(proc.pid), 15)
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--no-sandbox"])
        except Exception as e:
            pytest.skip(f"Chromium not available for Playwright ({e}); run `playwright install chromium`.")
        yield b
        b.close()


@pytest.fixture
def page(browser, streamlit_server):
    pg = browser.new_page(viewport={"width": 1600, "height": 1400})
    console_errors = []
    pg.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    pg.on("pageerror", lambda exc: console_errors.append(str(exc)))
    pg.goto(streamlit_server, wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(1500)
    pg.console_errors = console_errors
    yield pg
    pg.close()


def _select_function(page, name):
    combo = page.get_by_role("combobox", name="Function to Execute:")
    combo.click()
    page.wait_for_timeout(300)
    page.keyboard.type(name)
    page.wait_for_timeout(400)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)


@pytest.mark.skipif(not os.path.exists(read_image_fixture), reason=f"{read_image_fixture} does not exist")
def test_image_tab_run_function(page):
    page.get_by_text("Image Processing", exact=False).first.click()
    page.wait_for_timeout(1500)

    # Default function is read_image with the fixture file prefilled.
    page.get_by_role("button", name="Run Function").click()
    page.wait_for_timeout(5000)

    assert page.get_by_text("Executed", exact=False).count() > 0
    assert page.get_by_text("Execution Output", exact=False).count() > 0

    # Non-image result path: otsu_threshold returns a stats array, not an image.
    _select_function(page, "otsu_threshold")
    page.get_by_role("button", name="Run Function").click()
    page.wait_for_timeout(5000)

    assert page.get_by_text("Function Result", exact=False).count() > 0
    assert page.console_errors == []


@pytest.mark.skipif(not os.path.exists(network_fixture), reason=f"{network_fixture} does not exist")
def test_network_tab_run_function(page):
    page.get_by_text("Network Analysis", exact=False).first.click()
    page.wait_for_timeout(1500)

    # Default function (render_xdmf_3dl) has the fixture .xmf prefilled.
    page.get_by_role("button", name="Run Function").click()
    page.wait_for_timeout(6000)

    assert page.get_by_text("Executed", exact=False).count() > 0
    assert page.get_by_text("Execution Output", exact=False).count() > 0
    assert page.console_errors == []
