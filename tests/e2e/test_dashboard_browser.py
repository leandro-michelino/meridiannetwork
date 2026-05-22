from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect
sync_playwright = playwright.sync_playwright


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_HTML = ROOT / "oci_network_monitor_dashboard_v2.html"
CHROME_CANDIDATES = (
    os.environ.get("MERIDIAN_E2E_BROWSER"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_url(url: str, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise TimeoutError(f"{url} did not become ready")


def browser_executable() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    pytest.skip("No Chrome/Chromium browser found. Set MERIDIAN_E2E_BROWSER to run dashboard E2E tests.")


class DashboardProxy(BaseHTTPRequestHandler):
    api_base = ""

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            body = DASHBOARD_HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if self.path.startswith("/api/") or self.path in {"/healthz", "/readyz", "/docs"}:
            self.proxy()
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path.startswith("/api/"):
            self.proxy()
            return
        self.send_error(404)

    def proxy(self) -> None:
        body = self.rfile.read(int(self.headers.get("content-length", "0") or "0"))
        headers = {key: value for key, value in self.headers.items() if key.lower() not in {"host", "content-length"}}
        request = urllib.request.Request(
            f"{self.api_base}{self.path}",
            data=body or None,
            method=self.command,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                self.write_proxy_response(response.status, response.headers, response.read())
        except urllib.error.HTTPError as exc:
            self.write_proxy_response(exc.code, exc.headers, exc.read())

    def write_proxy_response(self, status: int, headers: object, body: bytes) -> None:
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() not in {"transfer-encoding", "connection"}:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


@contextmanager
def uvicorn_server() -> str:
    port = free_port()
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            str(ROOT / "backend"),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        api_base = f"http://127.0.0.1:{port}"
        wait_for_url(f"{api_base}/healthz")
        yield api_base
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@contextmanager
def dashboard_server(api_base: str) -> str:
    port = free_port()
    handler = type("BoundDashboardProxy", (DashboardProxy,), {"api_base": api_base})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    try:
        thread = __import__("threading").Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(scope="module")
def dashboard_url() -> str:
    with uvicorn_server() as api_base, dashboard_server(api_base) as url:
        yield url


@pytest.fixture()
def page(dashboard_url: str):
    with sync_playwright() as runner:
        browser = runner.chromium.launch(executable_path=browser_executable(), headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        browser_page = context.new_page()
        browser_page.goto(dashboard_url, wait_until="networkidle")
        yield browser_page
        browser.close()


def selected_regions(page) -> list[str]:
    return page.evaluate(
        """() => [...document.querySelectorAll('#regionMenuList input[data-region-filter]:checked')]
          .map((input) => input.dataset.regionFilter)"""
    )


def horizontally_clipped_topology_nodes(page) -> list[str]:
    return page.evaluate(
        """() => {
          const topology = document.querySelector('#topology');
          const viewport = topology.getBoundingClientRect();
          return [...document.querySelectorAll('.topo-node')]
            .filter((node) => {
              const rect = node.getBoundingClientRect();
              return rect.left < viewport.left || rect.right > viewport.right;
            })
            .map((node) => node.dataset.nodeId);
        }"""
    )


def test_regions_menu_controls_api_and_demo_scope(page) -> None:
    page.evaluate("localStorage.removeItem('meridianRegionFilter')")
    page.reload(wait_until="networkidle")
    expect(page.locator("#dataModeBadge")).to_have_text("api", timeout=10_000)
    expect(page.locator("#collectionStatusPanel")).to_be_visible()
    expect(page.locator("#collectionStatusPanel")).to_contain_text("Collection status")
    expect(page.locator("#collectionStatusPanel")).to_contain_text("Resources")
    expect(page.locator("#collectionStatusPanel .cs-count-chip").first).to_contain_text("VCN")
    expect(page.locator('#collectionStatusPanel button[data-refresh-selected]')).to_be_visible()
    expect(page.locator('#collectionStatusPanel button[data-retry-failed]')).to_be_visible()
    expect(page.locator('#collectionStatusPanel button[data-clear-cache]')).to_be_visible()
    expect(page.locator("#collectionStatusPanel .cs-progress")).to_be_visible()
    expect(page.locator("#collectionStatusPanel")).to_contain_text("Full scan")
    expect(page.locator('#collectionStatusPanel button[data-refresh-region]').first).to_be_visible()
    expect(page.locator("#coveragePanel")).to_be_visible()
    expect(page.locator("#coveragePanel")).to_contain_text("Coverage")
    expect(page.locator('#coveragePanel button[data-coverage-filter="missing_vcns"]')).to_be_visible()
    expect(page.locator("#coveragePanel .coverage-row").first).to_contain_text("VCN")
    expect(page.locator('#collectionStatusPanel button[data-refresh-selected]')).to_be_enabled(timeout=10_000)

    page.click('#collectionStatusPanel button[data-refresh-selected]')
    expect(page.locator("#lastUpdated")).to_contain_text("Last refresh:", timeout=10_000)

    page.click("#regionMenuBtn")
    expect(page.locator("#regionMenuBtn")).to_contain_text("Regions 1/38")
    assert selected_regions(page) == ["eu-frankfurt-1"]
    assert page.locator("#kpiVcnSub").inner_text() == "1/38 selected regions"

    page.fill("#regionSearch", "madrid")
    page.locator('#regionMenuList input[data-region-filter="eu-madrid-1"]').check()
    expect(page.locator("#regionMenuBtn")).to_contain_text("Regions 2/38", timeout=10_000)
    assert page.locator("#kpiVcnSub").inner_text() == "2/38 selected regions"

    page.fill("#regionSearch", "")
    page.click("#regionClearAll")
    expect(page.locator("#regionMenuBtn")).to_contain_text("Regions 0/38")
    assert selected_regions(page) == []
    assert page.locator("#kpiVcnSub").inner_text() == "0/38 selected regions"
    assert "Select at least one subscribed region" in page.locator("#topologyNodes .empty").inner_text()

    page.click("#demoToggle")
    expect(page.locator("#dataModeBadge")).to_contain_text("demo", timeout=10_000)
    expect(page.locator("#regionMenuBtn")).to_contain_text("Regions 0/2")
    assert page.locator("#kpiVcns").inner_text() == "0"

    page.click("#regionMenuBtn")
    page.click("#regionSelectAll")
    expect(page.locator("#regionMenuBtn")).to_contain_text("Regions 2/2")
    assert set(selected_regions(page)) == {"eu-frankfurt-1", "eu-amsterdam-1"}
    assert page.locator("#kpiVcns").inner_text() == "2"
    expect(page.locator("#topologyBadge")).to_contain_text("overview / 8 nodes / 6 links")


def test_topology_layout_modes_do_not_clip_horizontally(page) -> None:
    expect(page.locator("#dataModeBadge")).to_have_text("api", timeout=10_000)
    page.click("#demoToggle")
    expect(page.locator("#dataModeBadge")).to_contain_text("demo", timeout=10_000)
    page.locator("#topologyPanel").scroll_into_view_if_needed()

    expect(page.locator("#topologyBadge")).to_contain_text("overview / 8 nodes / 6 links")
    assert horizontally_clipped_topology_nodes(page) == []

    page.click('[data-topology-mode="full"]')
    expect(page.locator("#topologyBadge")).to_contain_text("layers (gateways, routes) / 2 nodes / 0 links")
    assert horizontally_clipped_topology_nodes(page) == []

    page.locator("#topologyVcnScope").select_option("vcn-prod-fra")
    expect(page.locator("#topologyBadge")).to_contain_text("layers (gateways, routes) / 7 nodes / 7 links")
    assert horizontally_clipped_topology_nodes(page) == []

    page.fill("#topologySearch", "nat")
    expect(page.locator("#topologyBadge")).to_contain_text("layers (gateways, routes) / 1 nodes / 0 links")
    page.fill("#topologySearch", "")

    page.locator("#topologyConnectedOnly").check()
    expect(page.locator("#topologyBadge")).to_contain_text("layers (gateways, routes) / 6 nodes / 7 links")
    page.locator("#topologyConnectedOnly").uncheck()

    page.click('[data-topology-mode="vcn"]')
    expect(page.locator("#topologyBadge")).to_contain_text("vcn focus / 7 nodes / 8 links")
    assert page.locator("#topologyVcnScope").input_value() == "vcn-prod-fra"
    assert horizontally_clipped_topology_nodes(page) == []

    page.locator("#topologyVcnScope").select_option("vcn-dr-ams")
    expect(page.locator("#topologyBadge")).to_contain_text("vcn focus / 1 nodes / 0 links")
    page.locator("#topologyVcnScope").select_option("vcn-prod-fra")
    expect(page.locator("#topologyBadge")).to_contain_text("vcn focus / 7 nodes / 8 links")
    assert page.locator("#topologyVcnScope").input_value() == "vcn-prod-fra"
    assert horizontally_clipped_topology_nodes(page) == []

    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(500)
    page.locator("#topologyPanel").scroll_into_view_if_needed()
    assert horizontally_clipped_topology_nodes(page) == []
