# Package: pages
# Class: BasePage

import logging
import re

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from utils.config import TOAST_TIMEOUT_MS

log = logging.getLogger("orangehrm")


class BasePage:
    """Shared OrangeHRM widget helpers.

    OrangeHRM renders every field inside an `.oxd-input-group` that also carries
    the field's label, so fields are located by their label rather than by
    position. A positional match would depend on the field order (the top bar
    Search box is index 0) and would silently resolve to an unrelated field on
    another page.
    """

    EMPTY_SELECTION = "-- Select --"

    _INPUT_GROUP = ".oxd-input-group"
    _SELECT_TRIGGER = ".oxd-select-text"
    _SELECT_VALUE = ".oxd-select-text-input"
    _SELECT_OPTION = ".oxd-select-dropdown .oxd-select-option"
    _SUCCESS_TOAST = ".oxd-toast-content--success"
    _FIELD_ERROR = ".oxd-input-field-error-message"

    def __init__(self, page: Page) -> None:
        self.page = page

    # ------------------------------------------------------------- locators
    def group_by_label(self, label: str) -> Locator:
        """The input group that carries the given label."""
        return self.page.locator(self._INPUT_GROUP).filter(has_text=label)

    def field_by_label(self, label: str) -> Locator:
        return self.group_by_label(label).locator("input")

    # ----------------------------------------------------------- dropdowns
    def select_option(self, label: str, value: str) -> None:
        """Picks a value from an OrangeHRM dropdown by its visible label."""
        self.group_by_label(label).locator(self._SELECT_TRIGGER).click()
        exact_value = re.compile(rf"^{re.escape(value)}$")
        self.page.locator(self._SELECT_OPTION).filter(has_text=exact_value).click()
        log.info("Selected %r in %s", value, label)

    def selected_option(self, label: str) -> str:
        return self.group_by_label(label).locator(self._SELECT_VALUE).inner_text().strip()

    # --------------------------------------------------------------- toasts
    def is_success_toast_displayed(self, timeout: int = TOAST_TIMEOUT_MS) -> bool:
        """Whether OrangeHRM confirmed the action with a success toast.

        The toast auto-dismisses after a few seconds, so this polls for it from
        the moment it is called instead of checking visibility once. On failure
        it logs any form validation errors, which is where OrangeHRM puts the
        real reason a save was rejected.

        `.first` is deliberate: toasts stack when actions happen in quick
        succession and any success toast answers the question, whereas matching
        them all would raise a strict mode violation.
        """
        try:
            self.page.locator(self._SUCCESS_TOAST).first.wait_for(
                state="visible", timeout=timeout
            )
            return True
        except PlaywrightTimeoutError:
            for error in self.page.locator(self._FIELD_ERROR).all():
                log.error("Form validation error: %s", error.inner_text())
            return False
