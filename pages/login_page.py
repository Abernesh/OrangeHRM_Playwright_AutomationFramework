# Package: pages
# Class: LoginPage

from utils.config import BASE_URL, LOGIN_URL


class LoginPage:
    def __init__(self, page):
        self.page = page
        self.username_input = page.get_by_placeholder("Username")
        self.password_input = page.get_by_placeholder("Password")
        self.login_button = page.get_by_role("button", name="Login")
        self.user_dropdown = page.locator(".oxd-userdropdown-tab")
        self.logout_link = page.get_by_role("menuitem", name="Logout")
        self.dashboard_heading = page.get_by_role("heading", name="Dashboard")

    def navigate(self):
        # domcontentloaded, not the default "load": the demo site keeps loading
        # assets long after the form is usable, and we wait for it explicitly.
        self.page.goto(BASE_URL, wait_until="domcontentloaded")
        self.login_button.wait_for(state="visible")

    def login(self, username, password):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def is_dashboard_visible(self):
        """Waits for the dashboard instead of checking once - is_visible() on
        its own returns immediately, before the page has finished rendering."""
        self.dashboard_heading.wait_for(state="visible")
        return self.dashboard_heading.is_visible()

    def logout(self):
        self.user_dropdown.click()
        self.logout_link.click()
        self.page.wait_for_url(LOGIN_URL)
        self.login_button.wait_for(state="visible")
