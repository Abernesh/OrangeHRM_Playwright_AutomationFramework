# Package: utils
# Class: EmployeeApi

import logging

from playwright.sync_api import Page

from utils.config import API_URL

log = logging.getLogger("orangehrm")


class EmployeeApi:
    """Validates PIM records through the OrangeHRM API.

    Built from the Playwright page so requests reuse its request context and
    therefore carry the session cookie from the UI login - that is what makes
    this a genuine API-vs-UI cross check rather than a separate session.
    """

    def __init__(self, page: Page) -> None:
        self._request = page.request
        # empNumber is the API's internal key and never changes for a record,
        # so looking it up once keeps the slow demo site out of the critical path.
        self._employee_numbers: dict[str, int] = {}

    # ------------------------------------------------------------- requests
    def search(self, employee_id: str) -> list[dict]:
        response = self._request.get(
            f"{API_URL}/pim/employees?nameOrId={employee_id}&limit=50&offset=0"
        )
        assert response.status == 200, f"Employee search API failed: {response.status}"
        return response.json().get("data", [])

    def employee_number(self, employee_id: str) -> int:
        if employee_id not in self._employee_numbers:
            records = self.search(employee_id)
            assert records, f"No employee found in the API for id {employee_id}"
            self._employee_numbers[employee_id] = records[0]["empNumber"]
        return self._employee_numbers[employee_id]

    def job_details(self, employee_id: str) -> dict:
        emp_number = self.employee_number(employee_id)
        response = self._request.get(f"{API_URL}/pim/employees/{emp_number}/job-details")
        assert response.status == 200, f"Job details API failed: {response.status}"
        return response.json()["data"]

    # ----------------------------------------------------------- assertions
    def verify_employee_exists(
        self, employee_id: str, first_name: str, last_name: str
    ) -> dict:
        records = self.search(employee_id)
        assert len(records) == 1, \
            f"API vs UI mismatch: expected 1 employee for id {employee_id}, got {len(records)}"

        employee = records[0]
        assert employee["employeeId"] == employee_id, \
            f"API vs UI mismatch on Employee Id: API={employee['employeeId']} UI={employee_id}"
        assert employee["firstName"] == first_name, \
            f"API vs UI mismatch on first name: API={employee['firstName']} UI={first_name}"
        assert employee["lastName"] == last_name, \
            f"API vs UI mismatch on last name: API={employee['lastName']} UI={last_name}"

        self._employee_numbers[employee_id] = employee["empNumber"]
        log.info("API confirms employee %s exists and matches the UI", employee_id)
        return employee

    def verify_job_details(self, details: dict, job_title: str, employment_status: str) -> None:
        """Confirms an already-fetched job-details payload matches the UI.

        Takes the payload rather than fetching it, so the caller can also report
        it without paying for a second round trip.
        """
        api_title = (details.get("jobTitle") or {}).get("title")
        api_status = (details.get("empStatus") or {}).get("name")

        assert api_title == job_title, \
            f"API vs UI mismatch on Job Title: API={api_title} UI={job_title}"
        assert api_status == employment_status, \
            f"API vs UI mismatch on Employment Status: API={api_status} UI={employment_status}"
        log.info("API job details match the UI: %s / %s", api_title, api_status)

    def verify_employee_deleted(self, employee_id: str) -> None:
        records = self.search(employee_id)
        assert not records, f"Employee {employee_id} still present in API after deletion"
        self._employee_numbers.pop(employee_id, None)
        log.info("API confirms employee %s was deleted", employee_id)

    # -------------------------------------------------------------- cleanup
    def delete_if_exists(self, employee_id: str) -> bool:
        """Teardown helper - removes a leftover record without failing the run.

        The demo site is shared, so a test that dies between create and delete
        would otherwise leave its employee behind permanently.
        """
        try:
            records = self.search(employee_id)
            if not records:
                return False

            response = self._request.delete(
                f"{API_URL}/pim/employees",
                data={"ids": [records[0]["empNumber"]]},
            )
            return response.status == 200
        except Exception as exc:
            log.warning("Cleanup of employee %s failed: %s: %s", employee_id, type(exc).__name__, exc)
            return False
