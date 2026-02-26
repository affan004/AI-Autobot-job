from __future__ import annotations

import asyncio
import time

from logger import logger


async def wait_until_cloudflare_resolved(
    page, timeout: int = 120, poll_interval: float = 1.0
) -> bool:
    """
    Wait for Cloudflare challenge pages (including Turnstile) to clear.
    Returns True when no challenge is detected.
    """
    if not await cf_challenge(page):
        return True

    logger.info("Cloudflare challenge detected, waiting for resolution...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        await _try_click_turnstile(page)
        if await no_cf_challenge(page):
            logger.info("Cloudflare challenge appears resolved.")
            return True
        await asyncio.sleep(poll_interval)

    logger.warning("Timed out waiting for Cloudflare challenge resolution.")
    return False


async def cf_challenge(page) -> bool:
    title = await page.title()
    if title.strip() == "Just a moment...":
        return True

    turnstile = page.locator(".cf-turnstile").first
    if await turnstile.count():
        hidden = page.locator("input[name='cf-turnstile-response']").first
        if await hidden.count():
            token = await hidden.input_value()
            if token:
                return False
        return True

    content = await page.content()
    challenge_signals = [
        "challenge-platform",
        "cf-chl-widget",
        "checking your browser before accessing",
    ]
    return any(signal in content.lower() for signal in challenge_signals)


async def no_cf_challenge(page) -> bool:
    return not await cf_challenge(page)


async def _try_click_turnstile(page) -> None:
    """
    Best-effort click for Turnstile iframe checkbox.
    """
    try:
        iframe = page.frame_locator("iframe[title*='Widget containing a Cloudflare security challenge']")
        checkbox = iframe.locator("input[type='checkbox']").first
        if await checkbox.count() and await checkbox.is_visible():
            await checkbox.click(timeout=2000)
            return
    except Exception:
        pass

