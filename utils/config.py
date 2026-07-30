# Package: utils
# Module: config

"""Project paths and settings, resolved from this file's location.

Everything here is anchored to PROJECT_ROOT rather than the working directory,
so the suite runs the same from any folder.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCREENSHOT_DIR = PROJECT_ROOT / "reports" / "screenshots"


def load_json(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as handle:
        return json.load(handle)


def resolve(relative_path):
    """Absolute path for a project-relative path such as data/profile.png."""
    return str(PROJECT_ROOT / relative_path)


CONFIG = load_json("config.json")

BASE_URL = CONFIG["base_url"]
LOGIN_URL = f"{BASE_URL}/web/index.php/auth/login"
API_URL = f"{BASE_URL}/web/index.php/api/v2"
USERNAME = CONFIG["username"]
PASSWORD = CONFIG["password"]
