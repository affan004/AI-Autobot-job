import traceback

from custom_exception import JobSkipException
from job_portals.base_job_portal import BaseJobPage
from logger import logger
from utils import browser_utils, time_utils


class WorkdayJobPagePlaywright(BaseJobPage):
    def __init__(self, driver):
        super().__init__(driver)

    def goto_job_page(self, job):
        try:
            self.driver.goto(job.link, wait_until="domcontentloaded", timeout=60000)
            browser_utils.handle_security_checks(self.driver)
            time_utils.medium_sleep()
            logger.debug(f"Navigated to Workday job link: {job.link}")
        except Exception as exc:
            logger.error(
                f"Failed to navigate to Workday job link: {job.link}, "
                f"error: {exc}\n{traceback.format_exc()}"
            )
            raise JobSkipException(f"Failed to load Workday job page: {job.link}") from exc

    def get_apply_button(self, job_context):
        raise NotImplementedError

    def click_apply_button(self, job_context) -> None:
        selectors = [
            "button[data-automation-id='applyNowButton']",
            "button[data-automation-id='applyButton']",
            "button:has-text('Apply')",
            "a:has-text('Apply')",
        ]

        try:
            for selector in selectors:
                button = self.driver.locator(selector).first
                if button.count() == 0:
                    continue
                if button.is_visible():
                    button.scroll_into_view_if_needed()
                    button.click(timeout=20000)
                    browser_utils.handle_security_checks(self.driver)
                    return
            raise ValueError("Workday apply button not found")
        except Exception as exc:
            logger.error(
                f"Failed to click Workday apply button: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Failed to click Workday apply button") from exc

    def get_location(self) -> str:
        selectors = [
            "[data-automation-id='locations']",
            "[data-automation-id='location']",
            "div[data-automation-id='jobPostingHeader'] li",
            "[data-automation-id='primaryLocation']",
        ]
        try:
            for selector in selectors:
                el = self.driver.locator(selector).first
                if el.count() > 0 and el.is_visible():
                    text = (el.inner_text() or "").strip()
                    if text:
                        # Workday sometimes renders label + value in the same block.
                        parts = [part.strip() for part in text.splitlines() if part.strip()]
                        if len(parts) > 1 and parts[0].lower() in {
                            "location",
                            "locations",
                        }:
                            return parts[-1]
                        return text
            return ""
        except Exception as exc:
            logger.error(
                f"Failed to get Workday location: {exc}\n{traceback.format_exc()}"
            )
            return ""

    def get_job_categories(self) -> dict:
        categories = {}
        try:
            location = self.get_location()
            if location:
                categories["location"] = location

            job_family = self.driver.locator(
                "[data-automation-id='jobFamily'], [data-automation-id='jobFamilyGroup']"
            ).first
            if job_family.count() > 0 and job_family.is_visible():
                value = (job_family.inner_text() or "").strip()
                if value:
                    categories["department"] = value

            employment_type = self.driver.locator(
                "[data-automation-id='timeType'], [data-automation-id='workerSubType']"
            ).first
            if employment_type.count() > 0 and employment_type.is_visible():
                value = (employment_type.inner_text() or "").strip()
                if value:
                    categories["commitment"] = value
            return categories
        except Exception as exc:
            logger.error(
                f"Failed to get Workday categories: {exc}\n{traceback.format_exc()}"
            )
            return categories

    def get_job_description(self, job) -> str:
        selectors = [
            "[data-automation-id='jobPostingDescription']",
            "[data-automation-id='jobDetails']",
            "main",
        ]
        try:
            for selector in selectors:
                container = self.driver.locator(selector).first
                if container.count() > 0 and container.is_visible():
                    text = (container.inner_text() or "").strip()
                    if text:
                        return text
            return ""
        except Exception as exc:
            logger.error(
                f"Error getting Workday job description: {exc}\n{traceback.format_exc()}"
            )
            return ""

    def get_recruiter_link(self) -> str:
        return ""
