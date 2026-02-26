from job_portals.base_job_portal import BaseApplicationPage, BaseJobPage
from job_portals.greenhouse.application_page_playwright import (
    GreenhouseApplicationPagePlaywright,
)
from job_portals.greenhouse.job_page_playwright import GreenhouseJobPagePlaywright
from job_portals.lever.application_page_playwright import LeverApplicationPagePlaywright
from job_portals.lever.job_page_playwright import LeverJobPagePlaywright
from job_portals.workday.application_page_playwright import (
    WorkdayApplicationPagePlaywright,
)
from job_portals.workday.job_page_playwright import WorkdayJobPagePlaywright


class MultiAtsJobPagePlaywright(BaseJobPage):
    def __init__(self, driver):
        super().__init__(driver)
        self.lever_page = LeverJobPagePlaywright(driver)
        self.greenhouse_page = GreenhouseJobPagePlaywright(driver)
        self.workday_page = WorkdayJobPagePlaywright(driver)
        self._active = self.lever_page

    def goto_job_page(self, job):
        self._active = self._page_for_url(job.link)
        return self._active.goto_job_page(job)

    def get_apply_button(self, job_context):
        return self._delegate().get_apply_button(job_context)

    def get_job_description(self, job):
        return self._delegate().get_job_description(job)

    def get_recruiter_link(self):
        return self._delegate().get_recruiter_link()

    def click_apply_button(self, job_context):
        return self._delegate().click_apply_button(job_context)

    def get_location(self):
        return self._delegate().get_location()

    def get_job_categories(self):
        return self._delegate().get_job_categories()

    def _delegate(self):
        return self._active if self._active is not None else self._page_for_current_url()

    def _page_for_current_url(self):
        url = ""
        if hasattr(self.driver, "url"):
            url = self.driver.url or ""
        return self._page_for_url(url)

    def _page_for_url(self, url: str):
        lowered = (url or "").lower()
        if "greenhouse.io" in lowered:
            return self.greenhouse_page
        if "myworkdayjobs.com" in lowered or "workdayjobs.com" in lowered:
            return self.workday_page
        return self.lever_page


class MultiAtsApplicationPagePlaywright(BaseApplicationPage):
    def __init__(self, driver):
        super().__init__(driver)
        self.lever_page = LeverApplicationPagePlaywright(driver)
        self.greenhouse_page = GreenhouseApplicationPagePlaywright(driver)
        self.workday_page = WorkdayApplicationPagePlaywright(driver)

    def wait_until_ready(self):
        return self._delegate().wait_until_ready()

    def has_next_button(self) -> bool:
        return self._delegate().has_next_button()

    def click_next_button(self) -> None:
        return self._delegate().click_next_button()

    def has_submit_button(self) -> bool:
        return self._delegate().has_submit_button()

    def click_submit_button(self) -> None:
        return self._delegate().click_submit_button()

    def application_submission_confirmation(self) -> bool:
        return self._delegate().application_submission_confirmation()

    def has_errors(self) -> None:
        return self._delegate().has_errors()

    def handle_errors(self) -> None:
        return self._delegate().handle_errors()

    def check_for_errors(self) -> None:
        return self._delegate().check_for_errors()

    def get_input_elements(self, form_section):
        return self._delegate().get_input_elements(form_section)

    def is_upload_field(self, element) -> bool:
        return self._delegate().is_upload_field(element)

    def get_file_upload_elements(self):
        return self._delegate().get_file_upload_elements()

    def get_upload_element_heading(self, element) -> str:
        return self._delegate().get_upload_element_heading(element)

    def upload_file(self, element, file_path: str) -> None:
        return self._delegate().upload_file(element, file_path)

    def get_form_sections(self):
        return self._delegate().get_form_sections()

    def is_terms_of_service(self, element) -> bool:
        return self._delegate().is_terms_of_service(element)

    def accept_terms_of_service(self, element) -> None:
        return self._delegate().accept_terms_of_service(element)

    def is_radio_question(self, element) -> bool:
        return self._delegate().is_radio_question(element)

    def web_element_to_radio_question(self, element):
        return self._delegate().web_element_to_radio_question(element)

    def select_radio_option(self, radio_question_web_element, answer: str) -> None:
        return self._delegate().select_radio_option(radio_question_web_element, answer)

    def is_textbox_question(self, element) -> bool:
        return self._delegate().is_textbox_question(element)

    def web_element_to_textbox_question(self, element):
        return self._delegate().web_element_to_textbox_question(element)

    def fill_textbox_question(self, element, answer: str) -> None:
        return self._delegate().fill_textbox_question(element, answer)

    def is_dropdown_question(self, element) -> bool:
        return self._delegate().is_dropdown_question(element)

    def web_element_to_dropdown_question(self, element):
        return self._delegate().web_element_to_dropdown_question(element)

    def select_dropdown_option(self, element, answer: str) -> None:
        return self._delegate().select_dropdown_option(element, answer)

    def discard(self) -> None:
        return self._delegate().discard()

    def has_save_button(self) -> bool:
        return self._delegate().has_save_button()

    def save(self) -> None:
        return self._delegate().save()

    def _delegate(self):
        url = ""
        if hasattr(self.driver, "url"):
            url = self.driver.url or ""
        lowered = url.lower()
        if "greenhouse.io" in lowered:
            return self.greenhouse_page
        if "myworkdayjobs.com" in lowered or "workdayjobs.com" in lowered:
            return self.workday_page
        return self.lever_page
