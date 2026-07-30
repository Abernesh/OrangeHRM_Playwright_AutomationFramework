# Package: tests
# Function: test_employee_lifecycle

import random

from utils import config
from utils.api_base import APIBase
from utils.reporter import Reporter

test_data = config.load_json("employee.json")


def unique_employee_id():
    """The demo site is shared and rejects duplicate ids, so each run needs its
    own. Prefix comes from the test data; the 6-digit suffix is random."""
    return f"{test_data['employee_id_prefix']}{random.randint(100000, 999999)}"


def test_employee_lifecycle(page, logged_in, pim_page, employee_cleanup):
    """Login and the logout safety net are handled by the logged_in fixture."""
    employee_id = unique_employee_id()

    with Reporter.step(f"Add a new employee ({employee_id})"):
        pim_page.navigate_to_add_employee()
        employee_cleanup.append(employee_id)
        assert pim_page.add_new_employee(
            test_data["first_name"],
            test_data["last_name"],
            employee_id,
            config.resolve(test_data["picture_path"])
        ), f"Employee creation failed for id {employee_id}"

    with Reporter.step("Search for the employee by Employee Id"):
        pim_page.search_employee_by_id(employee_id)
        pim_page.edit_employee(employee_id)

    with Reporter.step(
        f"Update Job Title to {test_data['job_title']!r} "
        f"and Employment Status to {test_data['status']!r}"
    ):
        pim_page.open_job_tab()
        assert pim_page.update_job_details(
            test_data["job_title"],
            test_data["status"]
        ), "Job details update was not confirmed by the UI"

    with Reporter.step("Verify the changes are reflected after a reload"):
        # Re-read from the server rather than trusting the values left in the form.
        pim_page.reload_job_tab()
        ui_job_details = pim_page.get_job_details()
        assert ui_job_details["job_title"] == test_data["job_title"], \
            f"Job Title not reflected in UI: {ui_job_details['job_title']}"
        assert ui_job_details["employment_status"] == test_data["status"], \
            f"Employment Status not reflected in UI: {ui_job_details['employment_status']}"

    with Reporter.step("Cross-check the API against the UI"):
        # Each raises with a specific mismatch message if the API disagrees.
        APIBase.verify_employee_exists(
            page, employee_id, test_data["first_name"], test_data["last_name"]
        )
        APIBase.verify_job_details(
            page,
            employee_id,
            ui_job_details["job_title"],
            ui_job_details["employment_status"]
        )
        Reporter.attach("API job details", str(APIBase.get_job_details(page, employee_id)))

    with Reporter.step("Delete the employee"):
        pim_page.search_employee_by_id(employee_id)
        pim_page.delete_employee(employee_id)
        assert pim_page.is_success_toast_displayed(), "Employee deletion failed on UI"

    with Reporter.step("Confirm the deletion via the API"):
        APIBase.verify_employee_deleted(page, employee_id)
        # Deleted for real, so the teardown has nothing left to clean up.
        employee_cleanup.remove(employee_id)

    with Reporter.step("Log out"):
        logged_in.logout()
        assert page.url == config.LOGIN_URL, "Logout failed"
