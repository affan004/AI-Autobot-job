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


class GreenhouseApplicationPagePlaywright(BaseApplicationPage):
    def __init__(self, driver):
        super().__init__(driver)

    def has_save_button(self) -> bool:
        return False

    def save(self) -> None:
        raise NotImplementedError

    def discard(self) -> None:
        raise NotImplementedError

    def application_submission_confirmation(self) -> bool:
        confirmation_selectors = [
            "text=Application submitted",
            "text=Thank you for applying",
            "text=We've received your application",
        ]
        try:
            for selector in confirmation_selectors:
                confirmation = self.driver.locator(selector).first
                if confirmation.count() > 0 and confirmation.is_visible():
                    return True
            return False
        except Exception as exc:
            logger.error(f"Greenhouse confirmation check error: {exc}")
            return False

    def wait_until_ready(self):
        try:
            self.driver.wait_for_load_state("domcontentloaded", timeout=120000)
            form = self.driver.locator(
                "form#application_form, form[action*='applications']"
            ).first
            if form.count() > 0:
                form.wait_for(state="visible", timeout=30000)
        except Exception as exc:
            logger.error(
                f"Error while waiting for Greenhouse page load: {exc}\n{traceback.format_exc()}"
            )
            raise JobSkipException("Greenhouse application page load timeout") from exc

    def has_next_button(self) -> bool:
        # Greenhouse forms are usually single-page.
        return False

    def click_next_button(self) -> None:
        raise NotImplementedError

    def has_submit_button(self) -> bool:
        selectors = [
            "#submit_app",
            "button[type='submit']",
            "input[type='submit']",
        ]
        try:
            for selector in selectors:
                submit = self.driver.locator(selector).first
                if submit.count() > 0 and submit.is_visible():
                    return True
            return False
        except Exception:
            return False

    def click_submit_button(self) -> None:
        selectors = [
            "#submit_app",
            "button[type='submit']",
            "input[type='submit']",
        ]
        try:
            for selector in selectors:
                submit = self.driver.locator(selector).first
                if submit.count() == 0 or not submit.is_visible():
                    continue
                submit.scroll_into_view_if_needed()
                submit.click(timeout=15000)
                browser_utils.handle_security_checks(self.driver)
                return
            raise ValueError("Greenhouse submit button not found.")
        except Exception as exc:
            logger.error(
                f"Error clicking Greenhouse submit: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Greenhouse submit button not found.") from exc

    def has_errors(self) -> None:
        return None

    def handle_errors(self) -> None:
        return None

    def check_for_errors(self) -> None:
        return None

    def get_form_sections(self) -> List:
        try:
            form = self.driver.locator(
                "form#application_form, form[action*='applications']"
            ).first
            if form.count() > 0:
                return [form]

            container = self.driver.locator("#application, #main").first
            if container.count() > 0:
                return [container]

            return []
        except Exception as exc:
            logger.error(
                f"Error getting Greenhouse form sections: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while getting Greenhouse form sections") from exc

    def get_input_elements(self, form_section) -> List:
        try:
            candidates = form_section.locator(
                "div.field, div.application-field, li.application-question, div:has(> label)"
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
                f"Error getting Greenhouse input elements: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while getting Greenhouse input elements") from exc

    def is_upload_field(self, element) -> bool:
        try:
            return element.locator("input[type='file']").count() > 0
        except Exception:
            return False

    def get_file_upload_elements(self) -> List:
        raise NotImplementedError

    def get_upload_element_heading(self, element) -> str:
        try:
            label = element.locator("label, legend, .application-label").first
            if label.count() == 0:
                return ""
            return label.inner_text().strip()
        except Exception:
            return ""

    def upload_file(self, element, file_path: str) -> None:
        try:
            file_input = element.locator("input[type='file']").first
            if file_input.count() == 0:
                raise ValueError("Upload input not found")
            file_input.set_input_files(file_path)
        except Exception as exc:
            logger.error(
                f"Error uploading Greenhouse file: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while uploading file") from exc

    def is_terms_of_service(self, element) -> bool:
        try:
            return (
                element.locator(
                    "input[type='checkbox'][name*='consent'], input[type='checkbox'][name*='privacy']"
                ).count()
                > 0
            )
        except Exception:
            return False

    def accept_terms_of_service(self, element) -> None:
        try:
            checkbox = element.locator(
                "input[type='checkbox'][name*='consent'], input[type='checkbox'][name*='privacy']"
            ).first
            if checkbox.count() == 0:
                raise ValueError("Consent checkbox not found")
            if not checkbox.is_checked():
                checkbox.check(force=True)
        except Exception as exc:
            logger.error(
                f"Error accepting Greenhouse terms: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Failed to check consent box") from exc

    def is_radio_question(self, element) -> bool:
        try:
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
                item = inputs.nth(idx)
                input_type = (item.get_attribute("type") or "").strip().lower()
                if input_type == "checkbox":
                    has_checkbox = True
                value = (item.get_attribute("value") or "").strip()
                if value and value not in options:
                    options.append(value)

            if not options:
                option_labels = element.locator("label")
                options = [
                    text.strip()
                    for text in option_labels.all_inner_texts()
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
                f"Error building Greenhouse radio question: {exc}\n{traceback.format_exc()}"
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
                label_text = (label.inner_text() or "").strip().lower()
                if label_text == answer.lower():
                    label.click(timeout=5000)
                    time_utils.short_sleep()
                    return

            raise ValueError(f"Option '{answer}' not found in radio group")
        except Exception as exc:
            logger.error(
                f"Error selecting Greenhouse radio option: {exc}\n{traceback.format_exc()}"
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
                f"Error building Greenhouse textbox question: {exc}\n{traceback.format_exc()}"
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
                f"Error filling Greenhouse textbox: {exc}\n{traceback.format_exc()}"
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
                item.strip()
                for item in select_element.locator("option").all_inner_texts()
                if item and item.strip()
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
                f"Error building Greenhouse dropdown question: {exc}\n{traceback.format_exc()}"
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
                f"Error selecting Greenhouse dropdown option: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while selecting dropdown option") from exc

    def _question_text(self, element) -> str:
        label = element.locator("label, legend, .application-label").first
        if label.count() > 0:
            text = (label.inner_text() or "").strip()
            if text:
                return text
        return ""

    def _is_required(self, element) -> bool:
        if element.locator("span.required, abbr.required").count() > 0:
            return True
        input_el = element.locator("input,textarea,select").first
        return input_el.count() > 0 and input_el.get_attribute("required") is not None
