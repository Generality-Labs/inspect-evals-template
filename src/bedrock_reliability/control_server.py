"""Owns the one browser the sandbox runs, across the whole sample.

The solver's perceive -> plan -> act loop lives in the Inspect process, not in
here — planning needs generate(), which only makes sense host-side. But the
Page has to survive between every step of that loop, and a Playwright Page
can only be touched from the thread that created it. So this process launches
Playwright once, keeps the Page as module state, and serves each step of the
loop as one HTTP request from the solver's sandbox.exec() calls. Runs a plain
(single-threaded) HTTPServer for exactly that reason: requests are already
strictly sequential (the solver awaits one before issuing the next), and using
ThreadingHTTPServer here would risk a request landing on a different thread
than the one Playwright is bound to.

perceive() and execute() below are bedrock's agent/perceive.py and
agent/act.py, unchanged in mechanism: same interactive-element selector, same
ref = position in that list, same re-resolve-at-action-time instead of
trusting a stale handle. That ref-numbering is the whole point of this port —
it's the mechanism the published finding depends on — so it is not touched.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import ElementHandle, Page, sync_playwright

PORT = 8000
GOTO_TIMEOUT_MS = 15_000
CLICK_TIMEOUT_MS = 5_000
FILL_TIMEOUT_MS = 5_000
LOAD_STATE_TIMEOUT_MS = 8_000
MAX_ELEMENTS = 60

# Elements an agent can actually act on. Identical to bedrock's agent/perceive.py.
_INTERACTIVE = (
    "a, button, input, textarea, select, "
    "[role=button], [role=link], [role=textbox], [onclick]"
)


class _State:
    """Holds the one Page for the process's lifetime.

    An attribute on an object, rather than a rebound module global, so main()
    can set it up without a `global` statement.
    """

    page: Page


state = _State()


def _perceive() -> dict[str, Any]:
    handles = state.page.query_selector_all(_INTERACTIVE)

    elements: list[dict[str, Any]] = []
    for h in handles:
        if len(elements) >= MAX_ELEMENTS:
            break
        try:
            if not h.is_visible():
                continue
            text = (h.inner_text() or "").strip()
            name = (
                h.get_attribute("aria-label")
                or h.get_attribute("placeholder")
                or h.get_attribute("name")
            )
            elements.append(
                {
                    "ref": len(elements),
                    "tag": (h.evaluate("e => e.tagName") or "").lower(),
                    "text": text,
                    "role": h.get_attribute("role"),
                    "name": name,
                    "value": h.get_attribute("value"),
                }
            )
        except Exception:  # noqa: BLE001 — a stale/detached node must not kill perception
            continue

    try:
        body_text = state.page.inner_text("body")
    except Exception:  # noqa: BLE001
        body_text = ""

    return {
        "url": state.page.url,
        "title": state.page.title(),
        "text": " ".join(body_text.split()),
        "elements": elements,
    }


class ActuatorError(RuntimeError):
    """The action could not be performed."""


def _require_ref(action: dict[str, Any]) -> int:
    ref = action.get("ref")
    if not isinstance(ref, int):
        raise ActuatorError(
            f"action {action['action']!r} requires an integer ref, got {ref!r}"
        )
    return ref


def _resolve_ref(ref: int, elements_at_perception: int) -> ElementHandle:
    """Map a ref back to a live element, re-querying rather than trusting a stale handle.

    If the page has changed shape since the ref was assigned, say so instead of
    guessing — this is the exact re-resolution bedrock's act.py relies on to
    surface (rather than mask) index-shift failures.
    """
    handles = [h for h in state.page.query_selector_all(_INTERACTIVE) if h.is_visible()]
    if ref < 0 or ref >= len(handles):
        raise ActuatorError(
            f"ref [{ref}] out of range — page now has {len(handles)} visible "
            f"elements, had {elements_at_perception} at perception time"
        )
    return handles[ref]


def _execute(action: dict[str, Any]) -> dict[str, Any]:
    url_before = state.page.url
    kind = action["action"]
    text = action.get("text")
    elements_at_perception = action.get("elements_at_perception", 0)

    try:
        if kind == "click":
            ref = _require_ref(action)
            el = _resolve_ref(ref, elements_at_perception)
            el.click(timeout=CLICK_TIMEOUT_MS)
            state.page.wait_for_load_state(
                "domcontentloaded", timeout=LOAD_STATE_TIMEOUT_MS
            )
            detail = f"clicked [{ref}]"

        elif kind == "type":
            ref = _require_ref(action)
            el = _resolve_ref(ref, elements_at_perception)
            el.fill(text or "", timeout=FILL_TIMEOUT_MS)
            detail = f"typed {text!r} into [{ref}]"

        elif kind == "navigate":
            state.page.goto(
                text or "", wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS
            )
            detail = f"navigated to {text}"

        else:
            return {
                "ok": True,
                "detail": f"terminal action: {kind}",
                "url_before": url_before,
                "url_after": state.page.url,
            }

    except ActuatorError as exc:
        return {
            "ok": False,
            "detail": str(exc),
            "url_before": url_before,
            "url_after": state.page.url,
        }
    except Exception as exc:  # noqa: BLE001 — a failed action is data, not a crash
        return {
            "ok": False,
            "detail": f"{type(exc).__name__}: {exc}",
            "url_before": url_before,
            "url_after": state.page.url,
        }

    return {
        "ok": True,
        "detail": detail,
        "url_before": url_before,
        "url_after": state.page.url,
    }


def _final() -> dict[str, Any]:
    try:
        body_text = " ".join(state.page.inner_text("body").split())
    except Exception:  # noqa: BLE001
        body_text = ""
    return {"url": state.page.url, "text": body_text}


class Handler(BaseHTTPRequestHandler):
    server_version = "bedrock-control/1"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"[control_server] {self.address_string()} {fmt % args}\n")

    def _reply(
        self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/healthz":
            self._reply({"ok": True})
        elif path == "/perceive":
            self._reply(_perceive())
        elif path == "/final":
            self._reply(_final())
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        try:
            body = self._read_json()
        except json.JSONDecodeError as exc:
            self._reply(
                {"error": f"malformed JSON body: {exc}"}, HTTPStatus.BAD_REQUEST
            )
            return

        if path == "/goto":
            url = body.get("url")
            if not url:
                self._reply({"error": "goto requires 'url'"}, HTTPStatus.BAD_REQUEST)
                return
            state.page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            self._reply({"url": state.page.url})
        elif path == "/act":
            if body.get("action") not in ("click", "type", "navigate", "done", "fail"):
                self._reply(
                    {"error": f"unknown action {body.get('action')!r}"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            self._reply(_execute(body))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)


@dataclass(slots=True)
class _Browser:
    """Keeps the playwright/browser/context objects alive for the process lifetime."""

    playwright: Any
    browser: Any
    context: Any


def _launch() -> _Browser:
    pw = sync_playwright().start()
    # --no-sandbox: the container doesn't grant the extra capabilities Chromium's
    # own sandbox wants, and this container is itself the isolation boundary.
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context()
    return _Browser(playwright=pw, browser=browser, context=context)


def main() -> None:
    held = _launch()
    state.page = held.context.new_page()

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[control_server] browser ready, serving :{PORT}", flush=True)
    try:
        server.serve_forever()
    finally:
        held.browser.close()
        held.playwright.stop()


if __name__ == "__main__":
    main()
