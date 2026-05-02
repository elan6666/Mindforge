"""Playwright smoke tests for the local Mindforge web app."""

from __future__ import annotations

import pytest
import requests
from playwright.sync_api import expect, sync_playwright


FRONTEND_URL = "http://127.0.0.1:5173/"
BACKEND_HEALTH_URL = "http://127.0.0.1:8000/api/health"


def _local_app_available() -> bool:
    try:
        frontend = requests.get(FRONTEND_URL, timeout=2)
        backend = requests.get(BACKEND_HEALTH_URL, timeout=2)
    except requests.RequestException:
        return False
    return frontend.ok and backend.ok


@pytest.mark.e2e
def test_local_web_app_smoke():
    """Open the real app and verify the main product surfaces are reachable."""
    if not _local_app_available():
        pytest.skip("Local frontend/backend servers are not running.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        page.goto(FRONTEND_URL, wait_until="networkidle")

        expect(page.get_by_role("heading", name="Mindforge 控制工作台")).to_be_visible()
        expect(page.get_by_label("任务描述")).to_be_visible()

        page.get_by_role("button", name="项目 空间").click()
        expect(page.get_by_role("heading", name="项目空间")).to_be_visible()

        page.get_by_role("button", name="工具 MCP/Skills").click()
        expect(page.get_by_role("heading", name="工具与 Skills 中心")).to_be_visible()

        browser.close()
