import traceback

from custom_exception import JobSkipException
from job_portals.base_job_portal import BaseJobPage
from logger import logger
from utils import browser_utils, time_utils


class GreenhouseJobPagePlaywright(BaseJobPage):
    def __init__(self, driver):
        super().__init__(driver)

    def goto_job_page(self, job):
        try:
            self.driver.goto(job.link, wait_until="domcontentloaded", timeout=60000)
            browser_utils.handle_security_checks(self.driver)
            time_utils.medium_sleep()
            logger.debug(f"Navigated to Greenhouse job link: {job.link}")
        except Exception as exc:
            logger.error(
                f"Failed to navigate to Greenhouse job link: {job.link}, error: {exc}\n{traceback.format_exc()}"
            )
            raise JobSkipException(f"Failed to load Greenhouse job page: {job.link}") from exc

    def get_apply_button(self, job_context):
        raise NotImplementedError

    def click_apply_button(self, job_context) -> None:
        selectors = [
            "#application_button",
            "button#application_button",
            "a#application_button",
            "button:has-text('Apply for this job')",
            "a:has-text('Apply for this job')",
            "button:has-text('Apply')",
        ]

        try:
            for selector in selectors:
                button = self.driver.locator(selector).first
                if button.count() == 0:
                    continue
                if button.is_visible():
                    button.scroll_into_view_if_needed()
                    button.click(timeout=15000)
                    browser_utils.handle_security_checks(self.driver)
                    return
            raise ValueError("Greenhouse apply button not found")
        except Exception as exc:
            logger.error(
                f"Failed to click Greenhouse apply button: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Failed to click Greenhouse apply button") from exc

    def get_location(self) -> str:
        selectors = [
            "#header .location",
            ".opening .location",
            "[data-qa='location']",
            ".location",
        ]
        try:
            for selector in selectors:
                location_el = self.driver.locator(selector).first
                if location_el.count() > 0 and location_el.is_visible():
                    value = location_el.inner_text().strip()
                    if value:
                        return value
            return ""
        except Exception as exc:
            logger.error(
                f"Failed to get Greenhouse location: {exc}\n{traceback.format_exc()}"
            )
            return ""

    def get_job_categories(self) -> dict:
        categories = {}
        try:
            department = self.driver.locator(
                "[data-qa='department'], .department"
            ).first
            if department.count() > 0 and department.is_visible():
                value = department.inner_text().strip()
                if value:
                    categories["department"] = value

            commitment = self.driver.locator(
                "[data-qa='employment_type'], .employment_type"
            ).first
            if commitment.count() > 0 and commitment.is_visible():
                value = commitment.inner_text().strip()
                if value:
                    categories["commitment"] = value

            location = self.get_location()
            if location:
                categories["location"] = location
            return categories
        except Exception as exc:
            logger.error(
                f"Failed to get Greenhouse categories: {exc}\n{traceback.format_exc()}"
            )
            return categories

    def get_job_description(self, job) -> str:
        selectors = [
            "#content",
            "#job_details",
            ".job-post",
            ".opening",
        ]
        try:
            for selector in selectors:
                container = self.driver.locator(selector).first
                if container.count() > 0 and container.is_visible():
                    text = container.inner_text().strip()
                    if text:
                        return text
            return ""
        except Exception as exc:
            logger.error(
                f"Error getting Greenhouse job description: {exc}\n{traceback.format_exc()}"
            )
            return ""

    def get_recruiter_link(self) -> str:
        return ""

