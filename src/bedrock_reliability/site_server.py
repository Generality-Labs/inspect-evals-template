"""Serves the ported target pages from inside the sandbox.

Pinned, static copies of the pages bedrock's tasks were originally measured
against, so a run today exercises the same page shape a run next year will.
No outbound network access is required or used — everything the browser
needs (including jQuery) is vendored under site/.

quotes/ is the one page that isn't purely static: the real quotes.toscrape.com
login accepts any credentials, sets a session cookie, and shows a Logout link
on the home page — and that Logout link is what quotes_login_form's mechanism
depends on (an agent that reaches the logged-in state can still click Logout
and undo itself). A stdlib handler with a cookie is the smallest thing that
reproduces that behavior without pulling in a web framework.

Runs as ThreadingHTTPServer: a single page load fires off several concurrent
requests (the HTML plus its <script src> for jQuery), and there's no shared
mutable state here for concurrent handlers to race on.
"""

from __future__ import annotations

import sys
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PORT = 8080
SITE_ROOT = Path(__file__).parent / "site"
COOKIE_NAME = "bedrock_session"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

# path -> file under SITE_ROOT. Both the directory and the directory+index.html
# form are listed since a browser normalizes "/foo/" but a task's start_url may
# name either.
STATIC_ROUTES = {
    "/add_remove_elements/": "add_remove_elements/index.html",
    "/add_remove_elements/index.html": "add_remove_elements/index.html",
    "/add_remove_elements_prepopulated/": "add_remove_elements_prepopulated/index.html",
    "/add_remove_elements_prepopulated/index.html": "add_remove_elements_prepopulated/index.html",
    "/dynamic_controls": "dynamic_controls/index.html",
    "/dynamic_controls/": "dynamic_controls/index.html",
    "/vendor/jquery-1.11.3.min.js": "vendor/jquery-1.11.3.min.js",
}

LOGIN_TEMPLATE = (SITE_ROOT / "quotes" / "login.html").read_text()
HOME_TEMPLATE = (SITE_ROOT / "quotes" / "home.html").read_text()


def _is_logged_in(handler: BaseHTTPRequestHandler) -> bool:
    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    return cookie.get(COOKIE_NAME) is not None and cookie[COOKIE_NAME].value == "1"


class Handler(BaseHTTPRequestHandler):
    server_version = "bedrock-site/1"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"[site_server] {self.address_string()} {fmt % args}\n")

    def _serve_bytes(
        self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str, set_cookie: str | None = None) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        if set_cookie is not None:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()

    def _serve_static(self, relative_path: str) -> None:
        path = SITE_ROOT / relative_path
        body = path.read_bytes()
        self._serve_bytes(
            body, CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        )

    def _serve_quotes_home(self) -> None:
        nav = (
            '<a href="/quotes/logout">Logout</a>'
            if _is_logged_in(self)
            else '<a href="/quotes/login">Login</a>'
        )
        body = HOME_TEMPLATE.replace("__NAV_LINK__", nav).encode()
        self._serve_bytes(body, CONTENT_TYPES[".html"])

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler's naming convention
        path = urlsplit(self.path).path

        if path == "/healthz":
            self._serve_bytes(b"ok", "text/plain")
        elif path in STATIC_ROUTES:
            self._serve_static(STATIC_ROUTES[path])
        elif path in ("/quotes", "/quotes/"):
            self._serve_quotes_home()
        elif path == "/quotes/login":
            self._serve_bytes(LOGIN_TEMPLATE.encode(), CONTENT_TYPES[".html"])
        elif path == "/quotes/logout":
            self._redirect("/quotes/", set_cookie=f"{COOKIE_NAME}=; Path=/; Max-Age=0")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/quotes/login":
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(
                length
            )  # any credentials are accepted, same as the real site
            self._redirect("/quotes/", set_cookie=f"{COOKIE_NAME}=1; Path=/")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[site_server] serving {SITE_ROOT} on :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
