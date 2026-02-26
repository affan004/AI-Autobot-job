import traceback

from custom_exception import JobSkipException
from job_portals.base_job_portal import BaseJobPage
from logger import logger
from utils import browser_utils, time_utils


class LeverJobPagePlaywright(BaseJobPage):
    def __init__(self, driver):
        super().__init__(driver)

    def goto_job_page(self, job):
        try:
            self.driver.goto(job.link, wait_until="domcontentloaded", timeout=60000)
            browser_utils.handle_security_checks(self.driver)
            time_utils.medium_sleep()
            logger.debug(f"Navigated to job link: {job.link}")
        except Exception as exc:
            logger.error(
                f"Failed to navigate to job link: {job.link}, error: {exc}\n{traceback.format_exc()}"
            )
            raise JobSkipException(f"Failed to load job page: {job.link}") from exc

    def get_apply_button(self, job_context):
        raise NotImplementedError

    def click_apply_button(self, job_context) -> None:
        try:
            apply_button = self.driver.locator(
                "a.postings-btn.template-btn-submit"
            ).first
            if apply_button.count() == 0:
                raise ValueError("Apply button not found")
            apply_button.scroll_into_view_if_needed()
            apply_button.click(timeout=15000)
            browser_utils.handle_security_checks(self.driver)
        except Exception as exc:
            logger.error(
                f"Failed to click apply button: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Failed to click apply button") from exc

    def get_location(self) -> str:
        try:
            location = self.driver.locator(
                "div.location.posting-category"
            ).first
            if location.count() == 0:
                return ""
            return location.inner_text().strip()
        except Exception as exc:
            logger.error(f"Failed to get location: {exc}\n{traceback.format_exc()}")
            return ""

    def get_job_categories(self) -> dict:
        try:
            categories = {}
            elements = self.driver.locator(
                "div.posting-categories div.posting-category"
            )
            count = elements.count()

            for idx in range(count):
                element = elements.nth(idx)
                class_attr = element.get_attribute("class") or ""
                class_list = [part for part in class_attr.split() if part]
                if not class_list:
                    continue

                category_key = class_list[-1]
                category_value = element.inner_text().strip().rstrip("/").strip()
                if category_value:
                    categories[category_key] = category_value

            return categories
        except Exception as exc:
            logger.error(
                f"Failed to get job categories: {exc}\n{traceback.format_exc()}"
            )
            return {}

    def get_job_description(self, job) -> str:
        selectors = [
            "[data-qa='job-description']",
            "div.posting-page",
            "div.section-wrapper.page-full-width",
            "main",
        ]
        try:
            for selector in selectors:
                section = self.driver.locator(selector).first
                if section.count() == 0 or not section.is_visible():
                    continue
                text = (section.inner_text() or "").strip()
                if text:
                    return text
            return ""
        except Exception as exc:
            logger.error(
                f"Error getting job description: {exc}\n{traceback.format_exc()}"
            )
            return ""

    def get_recruiter_link(self) -> str:
        return ""
