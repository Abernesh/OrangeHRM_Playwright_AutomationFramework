# Package: pages
# Class: PIMPage

import logging
import re

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from utils.config import ELEMENT_TIMEOUT_MS

log = logging.getLogger("orangehrm")


class PIMPage(BasePage):
    """The PIM module: adding, finding, editing and deleting employees."""

    EMPLOYEE_ID_LABEL = "Employee Id"
    JOB_TITLE_LABEL = "Job Title"
    EMPLOYMENT_STATUS_LABEL = "Employment Status"

    _RESULT_ROW = ".oxd-table-card"
    _RESULT_CELL = ".oxd-table-cell"
    _EDIT_ICON = ".bi-pencil-fill"
    _DELETE_ICON = ".bi-trash"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.pim_menu = page.get_by_role("link", name="PIM")
        self.add_employee_tab = page.get_by_role("link", name="Add Employee")
        self.employee_list_tab = page.get_by_role("link", name="Employee List")
        self.job_tab = page.get_by_role("link", name="Job", exact=True)

        self.first_name = page.get_by_placeholder("First Name")
        self.last_name = page.get_by_placeholder("Last Name")
        self.upload_picture = page.locator("input[type='file']")
        self.save_button = page.get_by_role("button", name="Save")
        self.search_button = page.get_by_role("button", name="Search")
        self.confirm_delete = page.get_by_role("button", name="Yes, Delete")

        # Used both on Add Employee and as the Employee List search filter.
        self.employee_id_field = self.field_by_label(self.EMPLOYEE_ID_LABEL)
        self.personal_details_heading = page.get_by_role("heading", name="Personal Details")

    # ----------------------------------------------------------- navigation
    def navigate_to_add_employee(self) -> None:
        self.pim_menu.click()
        self.add_employee_tab.click()
        self.page.wait_for_url("**/pim/addEmployee")
        self.first_name.wait_for(state="visible")

    def open_job_tab(self) -> None:
        self.job_tab.click()
        self.page.wait_for_url("**/pim/viewJobDetails/**")
        self.group_by_label(self.JOB_TITLE_LABEL).locator(
            self._SELECT_TRIGGER
        ).wait_for(state="visible")

    # -------------------------------------------------------------- create
    def add_new_employee(
        self, first_name: str, last_name: str, employee_id: str, picture_path: str
    ) -> bool:
        """Fills the Add Employee form and saves. True if OrangeHRM confirmed it."""
        self.first_name.fill(first_name)
        self.last_name.fill(last_name)
        self.employee_id_field.fill(employee_id)
        self.upload_picture.set_input_files(picture_path)
        self.save_button.click()
        log.info("Submitted new employee %s (%s %s)", employee_id, first_name, last_name)
        return self.is_success_toast_displayed()

    # -------------------------------------------------------------- search
    def _row_locator(self, employee_id: str) -> Locator:
        """Rows whose Id cell is exactly employee_id.

        has_text is a substring match, so filtering the row on the raw id would
        also match a longer id that contains it (99432759 matches 199432759).
        """
        exact_id = re.compile(rf"^\s*{re.escape(employee_id)}\s*$")
        return self.page.locator(self._RESULT_ROW).filter(
            has=self.page.locator(self._RESULT_CELL, has_text=exact_id)
        )

    def employee_row(self, employee_id: str) -> Locator:
        """The one result row for employee_id.

        Employee ids are unique, so anything other than exactly one match means
        the search did not do what we think it did - fail loudly rather than
        picking a row with .first and acting on the wrong employee.
        """
        rows = self._row_locator(employee_id)
        count = rows.count()
        assert count == 1, f"Expected exactly 1 result row for {employee_id}, found {count}"
        return rows

    def search_employee_by_id(self, employee_id: str) -> None:
        self.pim_menu.click()
        self.employee_list_tab.click()
        self.page.wait_for_url("**/pim/viewEmployeeList")
        self.employee_id_field.wait_for(state="visible")
        self.employee_id_field.fill(employee_id)
        self.search_button.click()
        # Wait for the matching row, not just any row - the previous result set
        # stays on screen while the search request is in flight.
        self._row_locator(employee_id).wait_for(state="visible")
        log.info("Found employee %s in the employee list", employee_id)

    # ---------------------------------------------------------------- edit
    def edit_employee(self, employee_id: str) -> None:
        self.employee_row(employee_id).locator(self._EDIT_ICON).click()
        self.page.wait_for_url("**/pim/viewPersonalDetails/**")
        self.personal_details_heading.wait_for(state="visible")
        # The heading renders before the record loads - wait for the form itself.
        self.first_name.wait_for(state="visible")

    def update_job_details(self, job_title: str, employment_status: str) -> bool:
        """Sets Job Title and Employment Status on the Job tab and saves."""
        self.select_option(self.JOB_TITLE_LABEL, job_title)
        self.select_option(self.EMPLOYMENT_STATUS_LABEL, employment_status)
        self.save_button.click()
        return self.is_success_toast_displayed()

    def get_job_details(self) -> dict:
        """Job details as currently rendered, for verifying the update stuck."""
        return {
            "job_title": self.selected_option(self.JOB_TITLE_LABEL),
            "employment_status": self.selected_option(self.EMPLOYMENT_STATUS_LABEL),
        }

    def reload_job_tab(self) -> None:
        """Re-reads the record from the server so the check is not just the
        values left in the form after saving.

        The dropdowns render as "-- Select --" and are populated a moment later,
        so waiting for visibility alone would read the placeholder.
        """
        self.page.reload()
        job_title = self.group_by_label(self.JOB_TITLE_LABEL).locator(self._SELECT_VALUE)
        job_title.wait_for(state="visible")
        expect(job_title).not_to_have_text(
            self.EMPTY_SELECTION, timeout=ELEMENT_TIMEOUT_MS
        )

    # -------------------------------------------------------------- delete
    def delete_employee(self, employee_id: str) -> None:
        self.employee_row(employee_id).locator(self._DELETE_ICON).click()
        self.confirm_delete.click()
        log.info("Confirmed deletion of employee %s", employee_id)
