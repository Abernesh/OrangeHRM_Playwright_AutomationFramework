# Package: pages
# Class: LoginPage

import logging

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from utils.config import BASE_URL, LOGIN_URL

log = logging.getLogger("orangehrm")


class LoginPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username_input = page.get_by_placeholder("Username")
        self.password_input = page.get_by_placeholder("Password")
        self.login_button = page.get_by_role("button", name="Login")
        self.user_dropdown = page.locator(".oxd-userdropdown-tab")
        self.logout_link = page.get_by_role("menuitem", name="Logout")
        self.dashboard_heading = page.get_by_role("heading", name="Dashboard")

    def navigate(self) -> None:
        # domcontentloaded, not the default "load": the demo site keeps loading
        # assets long after the form is usable, and we wait for it explicitly.
        self.page.goto(BASE_URL, wait_until="domcontentloaded")
        self.login_button.wait_for(state="visible")

    def login(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()
        log.info("Submitted login for %s", username)

    def is_dashboard_visible(self) -> bool:
        """Whether the Dashboard rendered after logging in.

        Returns False rather than raising on timeout, so the caller's assertion
        message is what the reader sees instead of a raw TimeoutError.
        """
        try:
            self.dashboard_heading.wait_for(state="visible")
            return True
        except PlaywrightTimeoutError:
            log.error("Dashboard did not appear; current URL is %s", self.page.url)
            return False

    def logout(self) -> None:
        self.user_dropdown.click()
        self.logout_link.click()
        self.page.wait_for_url(LOGIN_URL)
        self.login_button.wait_for(state="visible")
        log.info("Logged out")
