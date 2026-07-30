# OrangeHRM Automation - Employee Lifecycle

End-to-end Playwright test covering the full employee lifecycle on the OrangeHRM
demo site, with every UI change cross-checked against the OrangeHRM REST API.

**Application under test:** https://opensource-demo.orangehrmlive.com/

## What the test covers

1. Log in as `Admin` and confirm the Dashboard loads
2. Add a new employee with first name, last name, Employee Id and a profile picture
3. Search for that employee by Employee Id and open the record
4. Update **Job Title** and **Employment Status** on the Job tab
5. Reload the record and verify the changes persisted
6. Validate via the API that the employee exists and the job data matches the UI
7. Delete the employee and confirm the deletion in the UI and the API
8. Log out

## Setup Instructions

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Install the browser: `playwright install chromium`

## How to Run the Test

```
pytest tests/test_lifecycle.py
```

Every run regenerates the HTML report and the video. Useful variations:

| Command | Effect |
| --- | --- |
| `pytest` | Runs the whole suite |
| `pytest -v` | Verbose, one line per test |
| `pytest -p no:cacheprovider --headed=false` | Headless (drop `--headed` from `pytest.ini` for CI) |
| `pytest --video=off` | Skip video recording for a faster run |

## Test Report and Video

| Artifact | Location |
| --- | --- |
| HTML report | `reports/report.html` |
| Test run video | `videos/<test-name>/video.webm` |

The report is self-contained: open it directly in a browser, no other files
needed. Each step shows a pass/fail mark, how long it took, and a collapsible
screenshot taken as the step ended. A failing step is marked in red and its
screenshot is labelled `FAILED at: <step>`, so a failure points straight at
where it broke.

## Framework Structure

```
conftest.py                fixtures (login, cleanup, timeouts) and report wiring
pytest.ini                 pytest, report and video configuration
requirements.txt           pinned dependencies

pages/                     Page Object Model
  login_page.py              login, dashboard check, logout
  pim_page.py                add / search / edit / delete employee, job details

tests/
  test_lifecycle.py          the end-to-end lifecycle test

utils/
  config.py                  paths and settings, anchored to the project root
  api_base.py                OrangeHRM API validation and test-data cleanup
  reporter.py                step recording and screenshot evidence

data/
  config.json                application URL and login credentials
  employee.json              employee test data
  profile.png                profile picture used during employee creation

reports/                   generated HTML report
videos/                    generated test run recording
```

### Design notes

- **Page Object Model** - every locator and UI action lives in `pages/`; the test
  reads as the business flow and contains no selectors.
- **Descriptive assertions** - each assertion carries a message naming the actual
  and expected value, e.g.
  `API vs UI mismatch on Job Title: API=QA Lead UI=QA Engineer`.
- **Stable locators** - fields are anchored to their labels and actions are scoped
  to the matching result row, so the suite cannot act on the wrong employee.
- **Self-cleaning** - a fixture deletes the created employee through the API even
  when the test fails, so failed runs leave nothing behind on the shared demo site.
- **Unique test data** - the Employee Id is generated per run
  (`employee_id_prefix` from `data/employee.json` + a random 6-digit suffix)
  because the demo site is shared and rejects duplicate ids.

## Configuration

`data/config.json` holds the application URL and credentials.
`data/employee.json` holds the employee test data used by the run:

```json
{
    "first_name": "Abernesh",
    "last_name": "M",
    "employee_id_prefix": "QA-",
    "job_title": "QA Engineer",
    "status": "Full-Time Permanent",
    "picture_path": "data/profile.png"
}
```

To test with different data, edit this file - no code changes required.

## Dependencies Used

| Package | Purpose |
| --- | --- |
| `pytest` | Test runner |
| `pytest-playwright` | Playwright integration: browser/page fixtures, `--headed`, `--video` |
| `pytest-html` | HTML report generation |
| `playwright` | Browser automation (installed with `pytest-playwright`) |

Python 3.12 was used for development.

## Known Behaviour

The OrangeHRM demo site is public and frequently slow - it has been observed
taking over 30 seconds to serve the login page. Timeouts are raised accordingly
in `conftest.py` (90s navigation, 60s element waits), so a run typically takes
30-90 seconds depending on how the site is behaving.
