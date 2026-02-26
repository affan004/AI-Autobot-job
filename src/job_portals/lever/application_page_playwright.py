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


class LeverApplicationPagePlaywright(BaseApplicationPage):
    def __init__(self, driver):
        super().__init__(driver)

    def has_save_button(self) -> bool:
        return False

    def save(self) -> None:
        raise NotImplementedError

    def discard(self) -> None:
        raise NotImplementedError

    def application_submission_confirmation(self) -> bool:
        try:
            confirmation = self.driver.locator("text=Application submitted").first
            return confirmation.count() > 0 and confirmation.is_visible()
        except Exception as exc:
            logger.error(f"Confirmation check error: {exc}")
            return False

    def wait_until_ready(self):
        try:
            self.driver.wait_for_load_state("domcontentloaded", timeout=120000)
            loading = self.driver.locator("div.loading-indicator").first
            if loading.count() > 0:
                loading.wait_for(state="hidden", timeout=120000)
        except Exception as exc:
            logger.error(
                f"Error occurred while waiting for page to load: {exc}\n{traceback.format_exc()}"
            )
            raise JobSkipException(
                "Page load timeout - loading indicator remained visible"
            ) from exc

    def click_submit_button(self) -> None:
        try:
            submit_button = self.driver.locator("#btn-submit").first
            if submit_button.count() == 0:
                raise ValueError("Submit button not found.")
            submit_button.scroll_into_view_if_needed()
            submit_button.click(timeout=15000)
            browser_utils.handle_security_checks(self.driver)
        except Exception as exc:
            logger.error(
                f"Error occurred while clicking submit button: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Submit button not found.") from exc

    def handle_errors(self) -> None:
        return None

    def has_submit_button(self) -> bool:
        try:
            submit_button = self.driver.locator("#btn-submit").first
            return submit_button.count() > 0 and submit_button.is_visible()
        except Exception:
            return False

    def get_file_upload_elements(self):
        raise NotImplementedError

    def upload_file(self, element, file_path: str) -> None:
        try:
            file_input = element.locator("input[type='file']").first
            if file_input.count() == 0:
                raise ValueError("Upload input not found")
            file_input.set_input_files(file_path)
        except Exception as exc:
            logger.error(
                f"Error occurred while uploading file: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while uploading file") from exc

    def get_form_sections(self) -> List:
        try:
            sections = self.driver.locator(
                "div.section.application-form.page-centered"
            )
            return [sections.nth(idx) for idx in range(sections.count())]
        except Exception as exc:
            logger.error(
                f"Error occurred while getting form sections: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while getting form sections") from exc

    def accept_terms_of_service(self, element) -> None:
        try:
            checkbox = element.locator(
                "input[type='checkbox'][name^='consent']"
            ).first
            if checkbox.count() == 0:
                raise ValueError("Consent checkbox not found in terms section")
            if not checkbox.is_checked():
                checkbox.check(force=True)
        except Exception as exc:
            logger.error(f"Terms acceptance error: {exc}\n{traceback.format_exc()}")
            raise Exception("Failed to check consent box") from exc

    def is_terms_of_service(self, element) -> bool:
        try:
            return element.locator("input[type='checkbox'][name^='consent']").count() > 0
        except Exception as exc:
            logger.error(
                f"Error checking terms of service element: {exc}\n{traceback.format_exc()}"
            )
            return False

    def is_radio_question(self, element) -> bool:
        try:
            return (
                element.locator("input[type='checkbox'], input[type='radio']").count()
                > 0
            )
        except Exception as exc:
            logger.error(
                f"Error occurred while checking if element is a radio question: {exc}\n{traceback.format_exc()}"
            )
            return False

    def web_element_to_radio_question(self, element) -> SelectQuestion:
        try:
            label = element.locator("div.application-label").first
            question_label = label.inner_text().strip() if label.count() > 0 else ""

            inputs = element.locator("input[type='radio'], input[type='checkbox']")
            options = []
            has_checkbox = False
            for idx in range(inputs.count()):
                input_el = inputs.nth(idx)
                input_type = input_el.get_attribute("type") or ""
                if input_type == "checkbox":
                    has_checkbox = True
                value = (input_el.get_attribute("value") or "").strip()
                if value and value not in options:
                    options.append(value)

            if not options:
                option_labels = element.locator("label")
                options = [
                    text.strip()
                    for text in option_labels.all_inner_texts()
                    if text and text.strip()
                ]

            required = (
                element.locator("span.required").count() > 0
                and "(Optional)" not in (element.inner_text() or "")
            )

            return SelectQuestion(
                question=question_label,
                options=options,
                type=(
                    SelectQuestionType.MULTI_SELECT
                    if has_checkbox
                    else SelectQuestionType.SINGLE_SELECT
                ),
                required=required,
            )
        except Exception as exc:
            logger.error(
                f"Error converting element to radio question: {exc}\n{traceback.format_exc()}"
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
                    input_type = input_el.get_attribute("type") or "radio"
                    if input_type == "checkbox":
                        input_el.check(force=True)
                    else:
                        input_el.check(force=True)
                    time_utils.short_sleep()
                    return

            # Fallback: click label by visible text.
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
                f"Error occurred while selecting radio option: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while selecting radio option") from exc

    def is_textbox_question(self, element) -> bool:
        try:
            if element.locator("textarea").count() > 0:
                return True
            return (
                element.locator(
                    "input[type='text'], input[type='number'], input[type='email']"
                ).count()
                > 0
            )
        except Exception as exc:
            logger.error(f"Textbox check error: {exc}\n{traceback.format_exc()}")
            return False

    def web_element_to_textbox_question(self, element) -> TextBoxQuestion:
        try:
            label = element.locator("div.application-label").first
            question_label = label.inner_text().strip() if label.count() > 0 else ""

            input_el = element.locator(
                "textarea, input[type='text'], input[type='number'], input[type='email']"
            ).first
            if input_el.count() == 0:
                raise ValueError("Textbox input not found")

            tag_name = input_el.evaluate("el => el.tagName.toLowerCase()")
            input_type = (
                "text" if tag_name == "textarea" else (input_el.get_attribute("type") or "")
            )
            if input_type in {"text", "textarea"}:
                question_type = TextBoxQuestionType.TEXT
            elif input_type == "number":
                question_type = TextBoxQuestionType.NUMERIC
            elif input_type == "email":
                question_type = TextBoxQuestionType.EMAIL
            else:
                question_type = TextBoxQuestionType.TEXT

            is_required = (
                element.locator("span.required").count() > 0
                or input_el.get_attribute("required") is not None
            )
            return TextBoxQuestion(
                question=question_label,
                type=question_type,
                required=is_required,
            )
        except Exception as exc:
            logger.error(
                f"Error occurred while converting element to textbox question: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while converting element to textbox question") from exc

    def fill_textbox_question(self, element, answer: str) -> None:
        try:
            if self._is_location_input(element):
                self._handle_location_input(element, answer)
                return

            input_element = element.locator(
                "textarea, input[type='text'], input[type='number'], input[type='email']"
            ).first
            if input_element.count() == 0:
                raise ValueError("Textbox input not found")
            input_element.fill(str(answer))
        except Exception as exc:
            logger.error(f"Input handling failed: {exc}\n{traceback.format_exc()}")
            raise Exception(f"Text input error: {exc}") from exc

    def _is_location_input(self, element) -> bool:
        return (
            element.locator("input.location-input[data-qa='location-input']").count()
            > 0
        )

    def _handle_location_input(self, element, answer: str) -> None:
        input_element = element.locator(
            "input.location-input[data-qa='location-input']"
        ).first
        input_element.fill("")
        input_element.type(str(answer), delay=90)

        dropdown_result = self.driver.locator("div.dropdown-results > div").first
        if dropdown_result.count() > 0:
            dropdown_result.click(timeout=10000)

        hidden_selected = element.locator("input#selected-location").first
        if hidden_selected.count() > 0:
            hidden_value = hidden_selected.input_value()
            if not hidden_value:
                raise ValueError("Location selection validation failed")

    def is_date_question(self, element) -> bool:
        return False

    def has_next_button(self) -> bool:
        return False

    def click_next_button(self) -> None:
        raise NotImplementedError

    def has_errors(self) -> None:
        return None

    def check_for_errors(self) -> None:
        return None

    def get_input_elements(self, form_section) -> List:
        try:
            input_elements = form_section.locator("ul li.application-question")
            if input_elements.count() == 0:
                return []
            return [input_elements.nth(idx) for idx in range(input_elements.count())]
        except Exception as exc:
            logger.error(
                f"Error occurred while getting input elements: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while getting input elements") from exc

    def is_upload_field(self, element) -> bool:
        try:
            return element.locator("input[type='file']").count() > 0
        except Exception as exc:
            logger.error(
                f"Error occurred while checking for upload field: {exc}\n{traceback.format_exc()}"
            )
            return False

    def get_upload_element_heading(self, element) -> str:
        try:
            heading = element.locator("div.application-label").first
            if heading.count() == 0:
                return ""
            return heading.inner_text().strip()
        except Exception as exc:
            logger.error(
                f"Error occurred while getting upload element heading: {exc}\n{traceback.format_exc()}"
            )
            return ""

    def is_dropdown_question(self, element) -> bool:
        try:
            return element.locator("select").count() > 0
        except Exception as exc:
            logger.error(
                f"Error checking for multiple-choice question: {exc}\n{traceback.format_exc()}"
            )
            return False

    def web_element_to_dropdown_question(self, element) -> SelectQuestion:
        try:
            label = element.locator("div.application-label").first
            question_label = label.inner_text().strip() if label.count() > 0 else ""

            select_element = element.locator("select").first
            if select_element.count() == 0:
                raise ValueError("Select element not found")

            options = [
                option.strip()
                for option in select_element.locator("option").all_inner_texts()
                if option and option.strip()
            ]

            is_required = (
                element.locator("span.required").count() > 0
                or select_element.get_attribute("required") is not None
            )
            question_type = (
                SelectQuestionType.MULTI_SELECT
                if select_element.get_attribute("multiple")
                else SelectQuestionType.SINGLE_SELECT
            )

            return SelectQuestion(
                question=question_label,
                options=options,
                required=is_required,
                type=question_type,
            )
        except Exception as exc:
            logger.error(
                f"Error occurred while converting element to dropdown question: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while converting element to dropdown question") from exc

    def select_dropdown_option(self, element, answer: str) -> None:
        try:
            select_element = element.locator("select").first
            if select_element.count() == 0:
                raise ValueError("Select element not found")

            # Try label/value matching.
            result = select_element.select_option(label=answer)
            if not result:
                result = select_element.select_option(value=answer)
            if not result:
                raise ValueError(f"Option '{answer}' not found in dropdown")
        except Exception as exc:
            logger.error(
                f"Error occurred while selecting dropdown option: {exc}\n{traceback.format_exc()}"
            )
            raise Exception("Error occurred while selecting dropdown option") from exc

