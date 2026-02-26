from __future__ import annotations

import asyncio
import inspect
import os
import time
from collections.abc import Callable
from typing import Any, Optional

import undetected_chromedriver as uc
from loguru import logger


chromeProfilePath = os.path.join(os.getcwd(), "chrome_profile", "linkedin_profile")


def ensure_chrome_profile() -> str:
    logger.debug(f"Ensuring browser profile exists at path: {chromeProfilePath}")
    profile_dir = os.path.dirname(chromeProfilePath)
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
        logger.debug(f"Created directory for browser profile: {profile_dir}")
    if not os.path.exists(chromeProfilePath):
        os.makedirs(chromeProfilePath)
        logger.debug(f"Created browser profile directory: {chromeProfilePath}")
    return chromeProfilePath


def chrome_browser_options() -> uc.ChromeOptions:
    """
    Backward-compatible Selenium options used by the existing ATS flow.
    """
    ensure_chrome_profile()
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if chromeProfilePath:
        options.add_argument(f"--user-data-dir={os.path.dirname(chromeProfilePath)}")
        options.add_argument(f"--profile-directory={os.path.basename(chromeProfilePath)}")
    else:
        options.add_argument("--incognito")

    return options


def script_value(response: dict) -> Any:
    """
    Kept for compatibility with smart-apply utility semantics.
    """
    return response.get("result", {}).get("result", {}).get("value")


async def launch_playwright_context(headless: bool = False):
    """
    Launch a stealth Playwright persistent context that can be used for
    anti-bot navigation (Cloudflare/DataDome style checks).
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth_async
    except Exception as exc:
        raise RuntimeError(
            "Playwright runtime is not available. Install playwright and "
            "playwright-stealth, then run 'playwright install chromium'."
        ) from exc

    ensure_chrome_profile()
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=chromeProfilePath,
        headless=headless,
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ],
        viewport=None,
    )
    page = context.pages[0] if context.pages else await context.new_page()
    await stealth_async(page)
    return playwright, context, page


def launch_playwright_sync(headless: bool = False):
    """
    Launch a stealth Playwright persistent context for synchronous code paths.
    Returns a Playwright Page object with attached context/process handles.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(
            "Playwright runtime is not available. Install playwright and "
            "run 'playwright install chromium'."
        ) from exc

    ensure_chrome_profile()
    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=chromeProfilePath,
        headless=headless,
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ],
        viewport=None,
    )
    page = context.pages[0] if context.pages else context.new_page()

    # Keep references so caller can shutdown gracefully later.
    setattr(page, "_aihawk_playwright_context", context)
    setattr(page, "_aihawk_playwright_runtime", playwright)

    try:
        from playwright_stealth import stealth_sync

        stealth_sync(page)
    except Exception:
        # Stealth is best-effort; keep browser usable if package/API differs.
        logger.debug("playwright-stealth not applied (best-effort).")

    return page


def close_browser(browser: Any) -> None:
    """
    Close Selenium driver or Playwright context/page safely.
    """
    try:
        context = getattr(browser, "_aihawk_playwright_context", None)
        runtime = getattr(browser, "_aihawk_playwright_runtime", None)
        if context is not None and runtime is not None:
            context.close()
            runtime.stop()
            return
    except Exception as exc:
        logger.warning(f"Failed to close Playwright browser cleanly: {exc}")

    try:
        if hasattr(browser, "quit"):
            browser.quit()
    except Exception as exc:
        logger.warning(f"Failed to close Selenium browser cleanly: {exc}")


async def wait_for_network_idle(page, timeout: int = 30, idle_time: float = 1.0) -> None:
    """
    Wait until no network activity occurs for `idle_time` seconds.
    """
    start_time = time.time()
    last_activity_time = time.time()

    def mark_activity(*_args):
        nonlocal last_activity_time
        last_activity_time = time.time()

    page.on("requestfinished", mark_activity)
    page.on("requestfailed", mark_activity)

    try:
        while True:
            await asyncio.sleep(0.25)
            now = time.time()
            if now - start_time > timeout:
                logger.warning("Timeout reached while waiting for network to be idle.")
                break
            if now - last_activity_time >= idle_time:
                logger.debug("Network is idle.")
                break
    finally:
        page.remove_listener("requestfinished", mark_activity)
        page.remove_listener("requestfailed", mark_activity)


async def wait_until(
    condition: Callable[[], Any], timeout: int = 30, interval: float = 0.2
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = condition()
        if inspect.isawaitable(result):
            result = await result
        if result:
            return
        await asyncio.sleep(interval)
    raise TimeoutError("wait_until() timeout")


async def site_available(page) -> bool:
    current_url = page.url
    if current_url.startswith("chrome-error://"):
        return False

    content = await page.content()
    error_signals = [
        "ERR_NAME_NOT_RESOLVED",
        "ERR_CONNECTION_REFUSED",
        "ERR_CONNECTION_TIMED_OUT",
        "ERR_INTERNET_DISCONNECTED",
        "This site can't be reached",
        "DNS_PROBE_FINISHED_NXDOMAIN",
    ]
    return not any(signal in content for signal in error_signals)


async def accept_cookie_consent(page) -> bool:
    """
    Best-effort cookie consent acceptance for common button labels.
    """
    selectors = [
        "button:has-text('Accept')",
        "button:has-text('I agree')",
        "button:has-text('Allow all')",
        "[role='button']:has-text('Accept')",
    ]

    for selector in selectors:
        locator = page.locator(selector).first
        if await locator.count() and await locator.is_visible():
            await locator.click(timeout=2000)
            return True

    return False
