# Package: utils
# Class: APIBase

from utils.config import API_URL


class APIBase:
    """Validates PIM records through the OrangeHRM API.

    Requests reuse the Playwright page's request context so they carry the
    session cookie from the UI login - that is what makes this a genuine
    API-vs-UI cross check.
    """

    BASE_URL = API_URL

    @staticmethod
    def _search_employee(page, emp_id):
        response = page.request.get(
            f"{APIBase.BASE_URL}/pim/employees?nameOrId={emp_id}&limit=50&offset=0"
        )
        assert response.status == 200, f"API request failed: {response.status}"
        return response.json().get("data", [])

    @staticmethod
    def verify_employee_exists(page, emp_id, first_name, last_name):
        records = APIBase._search_employee(page, emp_id)
        assert len(records) == 1, \
            f"API vs UI mismatch: expected 1 employee for id {emp_id}, got {len(records)}"

        employee = records[0]
        assert employee["employeeId"] == emp_id, \
            f"API vs UI mismatch on Employee Id: API={employee['employeeId']} UI={emp_id}"
        assert employee["firstName"] == first_name, \
            f"API vs UI mismatch on first name: API={employee['firstName']} UI={first_name}"
        assert employee["lastName"] == last_name, \
            f"API vs UI mismatch on last name: API={employee['lastName']} UI={last_name}"
        return True

    @staticmethod
    def get_employee_number(page, emp_id):
        records = APIBase._search_employee(page, emp_id)
        assert records, f"No employee found in API for id {emp_id}"
        return records[0]["empNumber"]

    @staticmethod
    def get_job_details(page, emp_id):
        emp_number = APIBase.get_employee_number(page, emp_id)
        response = page.request.get(f"{APIBase.BASE_URL}/pim/employees/{emp_number}/job-details")
        assert response.status == 200, f"Job details API failed: {response.status}"
        return response.json()["data"]

    @staticmethod
    def verify_job_details(page, emp_id, job_title, employment_status):
        """Confirms the API reports the job data the UI just saved."""
        data = APIBase.get_job_details(page, emp_id)
        api_title = (data.get("jobTitle") or {}).get("title")
        api_status = (data.get("empStatus") or {}).get("name")

        assert api_title == job_title, \
            f"API vs UI mismatch on Job Title: API={api_title} UI={job_title}"
        assert api_status == employment_status, \
            f"API vs UI mismatch on Employment Status: API={api_status} UI={employment_status}"
        return True

    @staticmethod
    def verify_employee_deleted(page, emp_id):
        records = APIBase._search_employee(page, emp_id)
        assert len(records) == 0, f"Employee {emp_id} still present in API after deletion"
        return True

    @staticmethod
    def delete_employee_if_exists(page, emp_id):
        """Teardown helper - removes a leftover record without failing the run.

        The demo site is shared, so a test that dies between create and delete
        would otherwise leave its employee behind permanently.
        """
        try:
            records = APIBase._search_employee(page, emp_id)
            if not records:
                return False

            response = page.request.delete(
                f"{APIBase.BASE_URL}/pim/employees",
                data={"ids": [records[0]["empNumber"]]},
            )
            return response.status == 200
        except Exception as exc:
            print(f"Cleanup of employee {emp_id} failed: {type(exc).__name__}: {exc}")
            return False
