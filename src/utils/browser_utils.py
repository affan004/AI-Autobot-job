from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Optional

import pygame
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

import constants
from captcha_solvers.cloudflare_challenge import wait_until_cloudflare_resolved
from captcha_solvers.recaptcha import solve_recaptcha_if_present
from logger import logger

# Module-level default browser object. Can be Selenium WebDriver or Playwright Page.
__DEFAULT_DRIVER: Optional[Any] = None


def set_default_driver(driver: Any) -> None:
    global __DEFAULT_DRIVER
    __DEFAULT_DRIVER = driver
    logger.debug("Default browser object set for browser_utils.")


def _get_driver(driver: Optional[Any]) -> Any:
    if driver is not None:
        return driver
    if __DEFAULT_DRIVER is not None:
        return __DEFAULT_DRIVER
    raise RuntimeError("No browser object provided and no default browser is set.")


def is_scrollable(element) -> bool:
    scroll_height = element.get_attribute("scrollHeight")
    client_height = element.get_attribute("clientHeight")
    scrollable = int(scroll_height) > int(client_height)
    logger.debug(
        f"Element scrollable check: scrollHeight={scroll_height}, "
        f"clientHeight={client_height}, scrollable={scrollable}"
    )
    return scrollable


def scroll_slow(driver, scrollable_element, start=0, end=3600, step=300, reverse=False):
    logger.debug(
        f"Starting slow scroll: start={start}, end={end}, step={step}, reverse={reverse}"
    )

    if reverse:
        start, end = end, start
        step = -step

    if step == 0:
        raise ValueError("Step cannot be zero.")

    max_scroll_height = int(scrollable_element.get_attribute("scrollHeight"))
    current_scroll_position = int(float(scrollable_element.get_attribute("scrollTop")))

    if reverse:
        if current_scroll_position < start:
            start = current_scroll_position
    elif end > max_scroll_height:
        end = max_scroll_height

    script_scroll_to = "arguments[0].scrollTop = arguments[1];"

    try:
        if not scrollable_element.is_displayed():
            logger.warning("The element is not visible.")
            return

        if not is_scrollable(scrollable_element):
            logger.warning("The element is not scrollable.")
            return

        if (step > 0 and start >= end) or (step < 0 and start <= end):
            logger.warning("No scrolling will occur due to incorrect start/end values.")
            return

        position = start
        previous_position = None
        while (step > 0 and position < end) or (step < 0 and position > end):
            if position == previous_position:
                break

            driver.execute_script(script_scroll_to, scrollable_element, position)
            previous_position = position
            position += step
            step = max(10, abs(step) - 10) * (-1 if reverse else 1)
            time.sleep(random.uniform(0.6, 1.5))

        driver.execute_script(script_scroll_to, scrollable_element, end)
        time.sleep(0.5)
    except Exception as exc:
        logger.error(f"Exception occurred during scrolling: {exc}")


def remove_focus_active_element(driver) -> None:
    driver.execute_script("document.activeElement.blur();")
    logger.debug("Removed focus from active element.")


def handle_security_checks(driver=None):
    browser_obj = _get_driver(driver)
    if _is_playwright_sync_page(browser_obj):
        return _handle_playwright_security_checks_sync(browser_obj)
    if _is_playwright_async_page(browser_obj):
        return _run_async(_handle_playwright_security_checks(browser_obj))
    return _handle_selenium_security_checks(browser_obj)


def security_check(driver=None):
    browser_obj = _get_driver(driver)
    if _is_playwright_sync_page(browser_obj) or _is_playwright_async_page(browser_obj):
        logger.warning(
            "Manual security check prompt is Selenium-only. "
            "Playwright flow should rely on automated challenge solvers."
        )
        return

    browser_obj.switch_to.window(browser_obj.current_window_handle)
    logger.info("Playing notification sound...")
    pygame.mixer.init()
    pygame.mixer.music.load(constants.SECURITY_CHECK_ALERT_AUDIO)
    pygame.mixer.music.play()
    logger.info("Waiting for user to solve CAPTCHA...")
    input("Press Enter after solving the CAPTCHA to continue...")


def _handle_selenium_security_checks(driver):
    try:
        page_title = driver.title or ""
        if page_title.strip().lower() == "just a moment...":
            logger.info("Cloudflare interstitial detected. Switching to manual flow.")
            security_check(driver)
            return

        captcha_iframe = driver.find_element(By.XPATH, "//iframe[contains(@src, 'hcaptcha')]")
        driver.switch_to.frame(captcha_iframe)
        visible_elements = driver.find_elements(
            By.XPATH, "//*[contains(@style, 'visibility: visible')]"
        )
        driver.switch_to.default_content()

        if visible_elements:
            logger.info("CAPTCHA detected in Selenium flow.")
            security_check(driver)

    except NoSuchElementException:
        logger.debug("No CAPTCHA detected on the page.")
    except Exception as exc:
        logger.error(f"An error occurred while handling Selenium security checks: {exc}")


async def _handle_playwright_security_checks(page) -> None:
    try:
        cf_resolved = await wait_until_cloudflare_resolved(page)
        if not cf_resolved:
            logger.warning("Cloudflare challenge was not resolved in time.")

        recaptcha_resolved = await solve_recaptcha_if_present(page)
        if not recaptcha_resolved:
            logger.warning("reCAPTCHA remains unresolved.")
    except Exception as exc:
        logger.error(f"Error while handling Playwright security checks: {exc}")


def _handle_playwright_security_checks_sync(page) -> None:
    """
    Best-effort sync Playwright challenge handling.
    """
    try:
        title = page.title() or ""
        if title.strip().lower() == "just a moment...":
            logger.info("Cloudflare challenge detected. Waiting for resolution.")
            for _ in range(90):
                _try_click_turnstile_sync(page)
                page.wait_for_timeout(1000)
                if (page.title() or "").strip().lower() != "just a moment...":
                    break

        content = page.content().lower()
        if "recaptcha" in content:
            logger.warning(
                "reCAPTCHA detected in sync Playwright mode. "
                "Automated solving is best-effort and may require manual intervention."
            )
    except Exception as exc:
        logger.error(f"Error while handling sync Playwright security checks: {exc}")


def _try_click_turnstile_sync(page) -> None:
    try:
        frame = page.frame_locator(
            "iframe[title*='Cloudflare security challenge']"
        )
        checkbox = frame.locator("input[type='checkbox']").first
        if checkbox.count() > 0 and checkbox.is_visible():
            checkbox.click(timeout=1500)
    except Exception:
        pass


def _is_playwright_sync_page(browser_obj: Any) -> bool:
    # Heuristic check to avoid hard dependency on Playwright classes.
    return all(
        hasattr(browser_obj, attr) for attr in ("goto", "locator", "wait_for_load_state")
    )


def _is_playwright_async_page(browser_obj: Any) -> bool:
    return all(hasattr(browser_obj, attr) for attr in ("locator", "content", "title"))


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # If called from an existing loop, fire-and-forget to avoid blocking sync code.
    loop.create_task(coro)
    return None
