import traceback
from typing import List

from custom_exception import JobSkipException
from job_portals.application_form_elements import (
    SelectQuestion,
    SelectQuestionType,
    TextBoxQuestion,
    TextBoxQuestionType,
)
from job_portals.base_job_portal import BaseApplicationPage
from logger import logger
from utils import browser_utils, time_utils


class WorkdayApplicationPagePlaywright(BaseApplicationPage):
    def __init__(self, driver):
        super().__init__(driver)

    def has_save_button(self) -> bool:
        selectors = [
            "button[data-automation-id='saveAndContinueButton']",
            "button:has-text('Save')",
        ]
        for selector in selectors:
            el = self.driver.locator(selector).first
            if el.count() > 0 and el.is_visible():
                return True
        return False

    def save(self) -> None:
        selectors = [
            "button[data-automation-id='saveAndContinueButton']",
            "button:has-text('Save')",
        ]
        for selector in selectors:
            el = self.driver.locator(selector).first
            if el.count() > 0 and el.is_visible():
                el.click(timeout=10000)
                return

    def discard(self) -> None:
        raise NotImplementedError

    def application_submission_confirmation(self) -> bool:
        selectors = [
            "text=Application Submitted",
            "text=Thank you for applying",
            "text=Your application has been submitted",
        ]
        try:
            for selector in selectors:
                confirmation = self.driver.locator(selector).first
                if confirmation.count() > 0 and confirmation.is_visible():
                    return True
            return False
        except Exception as exc:
            logger.error(f"Workday confirmation check error: {exc}")
            return False

    def wait_until_ready(self):
        try:
            self.driver.wait_for_load_state("domcontentloaded", timeout=120000)
            body = self.driver.locator("body").first
            if body.count() > 0:
                body.wait_for(state="visible", timeout=30000)
        except Exception as exc:
            logger.error(
                f"Error while waiting for Workday page load: {exc}\n{traceback.format_exc()}"
            )
            raise JobSkipException("Workday application page load timeout") from exc

    def has_next_button(self) -> bool:
        selectors = [
            "button[data-automation-id='nextButton']",
            "button:has-text('Next')",
            "button:has-text('Continue')",
        ]
        for selector in selectors:
            button = self.driver.locator(selector).first
            if button.count() > 0 and button.is_visible():
                return True
        return False

    def click_next_button(self) -> None:
        selectors = [
            "button[data-automation-id='nextButton']",
            "button:has-text('Next')",
            "button:has-text('Continue')",
        ]
        for selector in selectors:
            button = self.driver.locator(selector).first
            if button.count() > 0 and button.is_visible():
                button.click(timeout=15000)
                browser_utils.handle_security_checks(self.driver)
                return
        raise Exception("Workday next button not found")

    def has_submit_button(self) -> bool:
        selectors = [
            "button[data-automation-id='submitButton']",
            "button:has-text('Submit')",
            "button:has-text('Review and Submit')",
        ]
        for selector in selectors:
            button = self.driver.locator(selector).first
            if button.count() > 0 and button.is_visible():
                return True
        return False

    def click_submit_button(self) -> None:
        selectors = [
            "button[data-automation-id='submitButton']",
            "button:has-text('Submit')",
            "button:has-text('Review and Submit')",
        ]
        for selector in selectors:
            button = self.driver.locator(selector).first
            if button.count() > 0 and button.is_visible():
                button.scroll_into_view_if_needed()
                button.click(timeout=15000)
                browser_utils.handle_security_checks(self.driver)
                return
        raise Exception("Workday submit button not found")

    def has_errors(self) -> None:
        return None

    def handle_errors(self) -> None:
        return None

    def check_for_errors(self) -> None:
        return None

    def get_form_sections(self) -> List:
        try:
            candidates = [
                self.driver.locator("form").first,
                self.driver.locator("[data-automation-id='pageContent']").first,
                self.driver.locator("main").first,
            ]
            sections = []
            for candidate in candidates:
                if candidate.count() > 0 and candidate.is_visible():
                    sections.append(candidate)
            return sections
        except Exception as exc:
            logger.error(
                f"Error getting Workday form sections: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while getting Workday form sections") from exc

    def get_input_elements(self, form_section) -> List:
        try:
            candidates = form_section.locator(
                "div[data-automation-id='formField'], div[role='group'], fieldset, div"
            )
            elements = []
            for idx in range(candidates.count()):
                el = candidates.nth(idx)
                has_input = el.locator("input, textarea, select").count() > 0
                if has_input:
                    elements.append(el)
            return elements
        except Exception as exc:
            logger.error(
                f"Error getting Workday input elements: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while getting Workday input elements") from exc

    def is_upload_field(self, element) -> bool:
        try:
            return (
                element.locator("input[type='file']").count() > 0
                or element.locator("[data-automation-id*='file']").count() > 0
            )
        except Exception:
            return False

    def get_file_upload_elements(self) -> List:
        raise NotImplementedError

    def get_upload_element_heading(self, element) -> str:
        try:
            heading = element.locator("label, legend, div[data-automation-id='prompt']").first
            if heading.count() == 0:
                return ""
            return (heading.inner_text() or "").strip()
        except Exception:
            return ""

    def upload_file(self, element, file_path: str) -> None:
        try:
            file_input = element.locator("input[type='file']").first
            if file_input.count() == 0:
                raise ValueError("File input not found")
            file_input.set_input_files(file_path)
        except Exception as exc:
            logger.error(
                f"Error uploading Workday file: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while uploading file") from exc

    def is_terms_of_service(self, element) -> bool:
        try:
            checkbox = element.locator("input[type='checkbox']").first
            if checkbox.count() == 0:
                return False
            return self._is_terms_text((element.inner_text() or ""))
        except Exception:
            return False

    def accept_terms_of_service(self, element) -> None:
        try:
            checkbox = element.locator("input[type='checkbox']").first
            if checkbox.count() == 0:
                raise ValueError("Consent checkbox not found")
            if not checkbox.is_checked():
                checkbox.check(force=True)
        except Exception as exc:
            logger.error(
                f"Error accepting Workday terms: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Failed to check consent box") from exc

    def is_radio_question(self, element) -> bool:
        try:
            if self.is_terms_of_service(element):
                return False
            return (
                element.locator("input[type='radio'], input[type='checkbox']").count()
                > 0
            )
        except Exception:
            return False

    def web_element_to_radio_question(self, element) -> SelectQuestion:
        try:
            question_text = self._question_text(element)
            inputs = element.locator("input[type='radio'], input[type='checkbox']")
            options = []
            has_checkbox = False
            for idx in range(inputs.count()):
                input_el = inputs.nth(idx)
                input_type = (input_el.get_attribute("type") or "").lower()
                if input_type == "checkbox":
                    has_checkbox = True
                value = (input_el.get_attribute("value") or "").strip()
                if value and value not in options:
                    options.append(value)

            if not options:
                labels = element.locator("label")
                options = [
                    text.strip()
                    for text in labels.all_inner_texts()
                    if text and text.strip()
                ]

            return SelectQuestion(
                question=question_text,
                options=options,
                type=(
                    SelectQuestionType.MULTI_SELECT
                    if has_checkbox
                    else SelectQuestionType.SINGLE_SELECT
                ),
                required=self._is_required(element),
            )
        except Exception as exc:
            logger.error(
                f"Error building Workday radio question: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error converting element to radio question") from exc

    def select_radio_option(self, radio_question_web_element, answer: str) -> None:
        try:
            inputs = radio_question_web_element.locator(
                "input[type='radio'], input[type='checkbox']"
            )
            for idx in range(inputs.count()):
                input_el = inputs.nth(idx)
                value = (input_el.get_attribute("value") or "").strip()
                if value.lower() == answer.lower():
                    input_el.check(force=True)
                    time_utils.short_sleep()
                    return

            labels = radio_question_web_element.locator("label")
            for idx in range(labels.count()):
                label = labels.nth(idx)
                if (label.inner_text() or "").strip().lower() == answer.lower():
                    label.click(timeout=5000)
                    time_utils.short_sleep()
                    return

            raise ValueError(f"Option '{answer}' not found in radio group")
        except Exception as exc:
            logger.error(
                f"Error selecting Workday radio option: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while selecting radio option") from exc

    def is_textbox_question(self, element) -> bool:
        try:
            if element.locator("textarea").count() > 0:
                return True
            return (
                element.locator(
                    "input[type='text'], input[type='number'], input[type='email'], input[type='tel'], input[type='url']"
                ).count()
                > 0
            )
        except Exception:
            return False

    def web_element_to_textbox_question(self, element) -> TextBoxQuestion:
        try:
            question_text = self._question_text(element)
            input_el = element.locator(
                "textarea, input[type='text'], input[type='number'], input[type='email'], input[type='tel'], input[type='url']"
            ).first
            if input_el.count() == 0:
                raise ValueError("Textbox input not found")

            tag_name = input_el.evaluate("el => el.tagName.toLowerCase()")
            input_type = (
                "text" if tag_name == "textarea" else (input_el.get_attribute("type") or "text")
            ).lower()

            if input_type == "number":
                question_type = TextBoxQuestionType.NUMERIC
            elif input_type == "email":
                question_type = TextBoxQuestionType.EMAIL
            else:
                question_type = TextBoxQuestionType.TEXT

            return TextBoxQuestion(
                question=question_text,
                type=question_type,
                required=self._is_required(element),
            )
        except Exception as exc:
            logger.error(
                f"Error building Workday textbox question: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error converting element to textbox question") from exc

    def fill_textbox_question(self, element, answer: str) -> None:
        try:
            input_element = element.locator(
                "textarea, input[type='text'], input[type='number'], input[type='email'], input[type='tel'], input[type='url']"
            ).first
            if input_element.count() == 0:
                raise ValueError("Textbox input not found")
            input_element.fill(str(answer))
        except Exception as exc:
            logger.error(
                f"Error filling Workday textbox: {exc}\n{traceback.format_exc()}"
            )
            raise Exception(f"Text input error: {exc}") from exc

    def is_dropdown_question(self, element) -> bool:
        try:
            return element.locator("select").count() > 0
        except Exception:
            return False

    def web_element_to_dropdown_question(self, element) -> SelectQuestion:
        try:
            question_text = self._question_text(element)
            select_element = element.locator("select").first
            if select_element.count() == 0:
                raise ValueError("Select element not found")

            options = [
                text.strip()
                for text in select_element.locator("option").all_inner_texts()
                if text and text.strip()
            ]

            return SelectQuestion(
                question=question_text,
                options=options,
                required=self._is_required(element),
                type=(
                    SelectQuestionType.MULTI_SELECT
                    if select_element.get_attribute("multiple")
                    else SelectQuestionType.SINGLE_SELECT
                ),
            )
        except Exception as exc:
            logger.error(
                f"Error building Workday dropdown question: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error converting element to dropdown question") from exc

    def select_dropdown_option(self, element, answer: str) -> None:
        try:
            select_element = element.locator("select").first
            if select_element.count() == 0:
                raise ValueError("Select element not found")
            result = select_element.select_option(label=answer)
            if not result:
                result = select_element.select_option(value=answer)
            if not result:
                raise ValueError(f"Option '{answer}' not found in dropdown")
        except Exception as exc:
            logger.error(
                f"Error selecting Workday dropdown option: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while selecting dropdown option") from exc

    def _question_text(self, element) -> str:
        label = element.locator("label, legend, div[data-automation-id='prompt']").first
        if label.count() > 0:
            text = (label.inner_text() or "").strip()
            if text:
                return text
        return ""

    def _is_required(self, element) -> bool:
        if element.locator("abbr.required, span.required").count() > 0:
            return True
        input_el = element.locator("input,textarea,select").first
        return input_el.count() > 0 and input_el.get_attribute("required") is not None

    @staticmethod
    def _is_terms_text(text: str) -> bool:
        lowered = text.lower()
        keywords = ["terms", "consent", "privacy", "agree", "authorization"]
        return any(keyword in lowered for keyword in keywords)

