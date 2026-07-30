# Package: pages
# Class: PIMPage

import re

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

class PIMPage:
    EMPTY_SELECTION = "-- Select --"

    def __init__(self, page):
        self.page = page
        self.pim_menu = page.get_by_role("link", name="PIM")
        self.add_employee_tab = page.get_by_role("link", name="Add Employee")
        self.employee_list_tab = page.get_by_role("link", name="Employee List")

        self.first_name = page.get_by_placeholder("First Name")
        self.last_name = page.get_by_placeholder("Last Name")
        self.upload_pic = page.locator("input[type='file']")
        self.save_button = page.get_by_role("button", name="Save")

        # Anchored to its label. A positional .oxd-input match would depend on
        # the field order (the top bar Search box is index 0) and would silently
        # resolve to an unrelated field on other PIM pages.
        self.employee_id = self._field_by_label("Employee Id")
        self.search_id_input = self._field_by_label("Employee Id")

        self.search_button = page.get_by_role("button", name="Search")
        self.confirm_delete = page.get_by_role("button", name="Yes, Delete")

        self.personal_details_heading = page.get_by_role("heading", name="Personal Details")
        self.field_errors = page.locator(".oxd-input-field-error-message")

        self.job_tab = page.get_by_role("link", name="Job", exact=True)

    def _field_by_label(self, label):
        return self.page.locator(".oxd-input-group").filter(has_text=label).locator("input")

    def _group_by_label(self, label):
        return self.page.locator(".oxd-input-group").filter(has_text=label)

    def _select_option(self, label, value):
        """Picks a value from an OrangeHRM dropdown by its visible label."""
        self._group_by_label(label).locator(".oxd-select-text").click()
        exact_value = re.compile(rf"^{re.escape(value)}$")
        self.page.locator(".oxd-select-dropdown .oxd-select-option").filter(
            has_text=exact_value
        ).click()

    def _selected_option(self, label):
        return self._group_by_label(label).locator(".oxd-select-text-input").inner_text().strip()

    def navigate_to_add_employee(self):
        self.pim_menu.click()
        self.add_employee_tab.click()
        self.page.wait_for_url("**/pim/addEmployee")
        self.first_name.wait_for(state="visible")

    def add_new_employee(self, fname, lname, emp_id, pic_path):
        self.first_name.fill(fname)
        self.last_name.fill(lname)
        self.employee_id.fill(emp_id)
        self.upload_pic.set_input_files(pic_path)
        self.save_button.click()
        return self.is_success_toast_displayed()

    def _row_locator(self, emp_id):
        """Rows whose Id cell is exactly emp_id.

        has_text is a substring match, so filtering the row on the raw id would
        also match a longer id that contains it (99432759 matches 199432759).
        """
        exact_id = re.compile(rf"^\s*{re.escape(emp_id)}\s*$")
        return self.page.locator(".oxd-table-card").filter(
            has=self.page.locator(".oxd-table-cell", has_text=exact_id)
        )

    def employee_row(self, emp_id):
        """The one result row for emp_id.

        Employee ids are unique, so anything other than exactly one match means
        the search did not do what we think it did - fail loudly rather than
        picking a row with .first and acting on the wrong employee.
        """
        rows = self._row_locator(emp_id)
        count = rows.count()
        assert count == 1, f"Expected exactly 1 result row for {emp_id}, found {count}"
        return rows

    def search_employee_by_id(self, emp_id):
        self.pim_menu.click()
        self.employee_list_tab.click()
        self.page.wait_for_url("**/pim/viewEmployeeList")
        self.search_id_input.wait_for(state="visible")
        self.search_id_input.fill(emp_id)
        self.search_button.click()
        # Wait for the matching row, not just any row - the previous result set
        # stays on screen while the search request is in flight.
        self._row_locator(emp_id).wait_for(state="visible")

    def edit_employee(self, emp_id):
        self.employee_row(emp_id).locator(".bi-pencil-fill").click()
        self.page.wait_for_url("**/pim/viewPersonalDetails/**")
        self.personal_details_heading.wait_for(state="visible")
        # The heading renders before the record loads - wait for the form itself.
        self.first_name.wait_for(state="visible")

    def open_job_tab(self):
        self.job_tab.click()
        self.page.wait_for_url("**/pim/viewJobDetails/**")
        self._group_by_label("Job Title").locator(".oxd-select-text").wait_for(state="visible")

    def update_job_details(self, job_title, employment_status):
        """Sets Job Title and Employment Status on the Job tab and saves."""
        self._select_option("Job Title", job_title)
        self._select_option("Employment Status", employment_status)
        self.save_button.click()
        return self.is_success_toast_displayed()

    def get_job_details(self):
        """Job details as currently rendered, for verifying the update stuck."""
        return {
            "job_title": self._selected_option("Job Title"),
            "employment_status": self._selected_option("Employment Status"),
        }

    def reload_job_tab(self):
        """Re-reads the record from the server so the check is not just the
        values left in the form after saving.

        The dropdowns render as "-- Select --" and are populated a moment later,
        so waiting for visibility alone would read the placeholder.
        """
        self.page.reload()
        job_title = self._group_by_label("Job Title").locator(".oxd-select-text-input")
        job_title.wait_for(state="visible")
        expect(job_title).not_to_have_text(self.EMPTY_SELECTION, timeout=15000)

    def delete_employee(self, emp_id):
        self.employee_row(emp_id).locator(".bi-trash").click()
        self.confirm_delete.click()

    def is_success_toast_displayed(self, timeout=15000):
        """Whether OrangeHRM confirmed the action with a success toast.

        The toast auto-dismisses after a few seconds, so this polls for it from
        the moment it is called instead of checking visibility once. On failure
        it reports any form validation errors, which is where OrangeHRM puts the
        real reason a save was rejected.

        .first is deliberate here: toasts stack when actions happen in quick
        succession, and any success toast answers the question. Matching them
        all would raise a strict mode violation instead.
        """
        try:
            self.page.locator(".oxd-toast-content--success").first.wait_for(
                state="visible", timeout=timeout
            )
            return True
        except PlaywrightTimeoutError:
            for error in self.field_errors.all():
                print(f"Form validation error: {error.inner_text()}")
            return False
