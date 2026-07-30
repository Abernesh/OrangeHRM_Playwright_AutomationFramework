# Package: root (Configuration)

import pytest
from pytest_html import extras as html_extras

from pages.login_page import LoginPage
from pages.pim_page import PIMPage
# Aliased: pytest hookspecs require the parameter name "config", so the module
# cannot share that name here.
from utils import config as settings
from utils.api_client import EmployeeApi
from utils.reporter import Reporter

# The browser/context/page fixtures come from pytest-playwright.


@pytest.fixture(autouse=True)
def evidence(page):
    """Binds the reporter to this test's page and raises the timeouts.

    The public demo site regularly exceeds Playwright's 30s defaults, so the
    waits are widened before anything touches the page.
    """
    page.set_default_navigation_timeout(settings.NAVIGATION_TIMEOUT_MS)
    page.set_default_timeout(settings.ELEMENT_TIMEOUT_MS)
    Reporter.reset(page)
    yield


@pytest.fixture
def pim_page(page):
    return PIMPage(page)


@pytest.fixture
def employee_api(page):
    """API client sharing the browser's session cookie."""
    return EmployeeApi(page)


@pytest.fixture
def logged_in(page, evidence):
    """Logs in before the test, and guarantees logout after it.

    The test logs out itself so the step lands in the report - pytest-html
    discards extras from a passing teardown. This teardown is the safety net
    for when the test dies before reaching its own logout.
    """
    login_page = LoginPage(page)
    with Reporter.step("Log in to OrangeHRM"):
        login_page.navigate()
        login_page.login(settings.USERNAME, settings.PASSWORD)
        assert login_page.is_dashboard_visible(), "Dashboard is not visible after login"

    yield login_page

    if "/auth/login" not in page.url:
        try:
            login_page.logout()
        except Exception as exc:
            print(f"Logout during teardown failed: {type(exc).__name__}: {exc}")


@pytest.fixture
def employee_cleanup(employee_api, logged_in):
    """Removes records the test created, so a failed run leaves nothing behind.

    Depends on logged_in so that it tears down *before* the logout - the
    cleanup calls need a live session.
    """
    created = []
    yield created
    for employee_id in created:
        if employee_api.delete_if_exists(employee_id):
            print(f"Cleaned up leftover employee {employee_id}")


# ------------------------------------------------------------------------ report
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach the collected evidence to the test's row in the HTML report."""
    report = (yield).get_result()
    if report.when != "call":
        return
    if report.failed:
        Reporter.screenshot("failure")
    if Reporter.entries:
        report.extras = getattr(report, "extras", []) + [html_extras.html(Reporter.to_html())]


def pytest_html_report_title(report):
    report.title = "OrangeHRM Automation - Employee Lifecycle Report"


def pytest_html_results_summary(prefix):
    prefix.append(f"<p><strong>Application:</strong> {settings.BASE_URL} "
                  f"&nbsp;|&nbsp; <strong>User:</strong> {settings.USERNAME}</p>")
