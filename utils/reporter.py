# Package: utils
# Class: Reporter

"""Collects what each test did, and renders it into the HTML report.

Tests record steps here; the reporter screenshots the page as each step ends and
conftest hands the result to pytest-html. That is what makes the report a record
of the run rather than a pass/fail line.
"""

import base64
import html
import time
from contextlib import contextmanager


class Reporter:
    entries: list = []      # what the current test has collected
    page = None             # bound by the page fixture, used for screenshots
    _depth = 0

    @classmethod
    def reset(cls, page=None):
        cls.entries, cls.page, cls._depth = [], page, 0

    # --------------------------------------------------------------------- steps
    @classmethod
    @contextmanager
    def step(cls, title):
        """Record a step, then screenshot the page as it closes - pass or fail."""
        entry = {"kind": "step", "title": title, "depth": cls._depth,
                 "status": "passed", "seconds": 0.0}
        cls.entries.append(entry)
        cls._depth += 1
        started = time.monotonic()
        try:
            yield
        except Exception:
            entry["status"] = "failed"
            raise
        finally:
            entry["seconds"] = round(time.monotonic() - started, 2)
            cls._depth -= 1
            cls.screenshot(
                f"{'FAILED at' if entry['status'] == 'failed' else 'End of'}: {title}"
            )

    # --------------------------------------------------------------- attachments
    @classmethod
    def screenshot(cls, title):
        """Screenshot the bound page. Evidence is never worth failing a test over."""
        if cls.page is None or cls.page.is_closed():
            return
        try:
            cls.attach(title, cls.page.screenshot(full_page=True), kind="image")
        except Exception as exc:
            print(f"Could not screenshot {title!r}: {exc}")

    @classmethod
    def attach(cls, title, body, kind="text"):
        # Only text is truncated. Cutting base64 image data mid-string would
        # produce a corrupt screenshot rather than a shortened one.
        body = base64.b64encode(body).decode("ascii") if kind == "image" else body[:20_000]
        cls.entries.append({"kind": kind, "title": title, "depth": cls._depth, "body": body})

    # ----------------------------------------------------------------- rendering
    @classmethod
    def to_html(cls):
        """One self-contained HTML block. Inline styles only, so the file stays standalone."""
        if not cls.entries:
            return ""
        blocks = "".join(cls._render(e) for e in cls.entries)
        return (
            "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:13px;border:1px solid "
            "#d7dae0;border-radius:6px;padding:10px 14px;margin:8px 0;background:#fbfcfd'>"
            "<div style='font-weight:600;margin-bottom:8px'>Test evidence</div>"
            f"{blocks}</div>"
        )

    @classmethod
    def _render(cls, entry):
        style = f"margin:4px 0 4px {14 * entry['depth']}px"
        title = html.escape(entry["title"])

        if entry["kind"] == "step":
            passed = entry["status"] == "passed"
            colour, mark = ("#1a7f37", "&#10003;") if passed else ("#b3261e", "&#10007;")
            return (f"<div style='{style};color:{colour};font-weight:600'>{mark} {title} "
                    f"<span style='color:#68717a;font-weight:400'>({entry['seconds']}s)</span></div>")

        if entry["kind"] == "image":
            content = (f"<img src='data:image/png;base64,{entry['body']}' style='max-width:100%;"
                       f"border:1px solid #d7dae0;border-radius:4px;margin-top:6px'/>")
        else:
            content = (f"<pre style='white-space:pre-wrap;word-break:break-word;background:#f2f4f7;"
                       f"border-radius:4px;padding:8px;margin-top:6px;font-size:12px'>"
                       f"{html.escape(entry['body'])}</pre>")
        return (f"<details style='{style}'><summary style='cursor:pointer;color:#0b62d0'>"
                f"{title}</summary>{content}</details>")
