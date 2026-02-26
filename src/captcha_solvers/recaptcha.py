from __future__ import annotations

import asyncio
import time

from logger import logger


async def page_has_recaptcha(page) -> bool:
    markers = ["grecaptcha", "recaptcha/api.js", "recaptcha__", "g-recaptcha"]
    content = await page.content()
    lowered = content.lower()
    return any(marker in lowered for marker in markers)


async def solve_recaptcha_if_present(page, timeout: int = 45) -> bool:
    """
    Best-effort reCAPTCHA checkbox click solver.
    Returns True if solved/dismissed, False if unresolved.
    """
    if not await page_has_recaptcha(page):
        return True

    logger.info("reCAPTCHA detected, attempting checkbox flow.")
    frame = page.frame_locator("iframe[title='reCAPTCHA']")
    checkbox = frame.locator("#recaptcha-anchor").first

    try:
        if await checkbox.count() and await checkbox.is_visible():
            await checkbox.click(timeout=3000)
    except Exception as exc:
        logger.warning(f"Could not click reCAPTCHA checkbox: {exc}")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if await recaptcha_solved(page):
            logger.info("reCAPTCHA marked as solved.")
            return True
        if await recaptcha_detected_bot(page):
            logger.warning("reCAPTCHA returned automated-traffic warning.")
            return False
        await asyncio.sleep(1)

    logger.warning("Timed out waiting for reCAPTCHA completion.")
    return False


async def recaptcha_solved(page) -> bool:
    try:
        frame = page.frame_locator("iframe[title='reCAPTCHA']")
        anchor = frame.locator("#recaptcha-anchor").first
        if not await anchor.count():
            return False
        aria_checked = await anchor.get_attribute("aria-checked")
        return aria_checked == "true"
    except Exception:
        return False


async def recaptcha_detected_bot(page) -> bool:
    try:
        challenge_frame = page.frame_locator("iframe[title*='recaptcha challenge']")
        warning = challenge_frame.locator(".rc-doscaptcha-header-text").first
        return await warning.count() > 0 and await warning.is_visible()
    except Exception:
        return False

