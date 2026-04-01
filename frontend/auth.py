from __future__ import annotations

import os
import unicodedata
from datetime import timedelta
from urllib.parse import quote

from flask import Flask, abort, redirect, request, session

from frontend.login_view import render_login_page

SESSION_USER_KEY = "lemonbi_user"
DEMO_USERS = {
    "tomas": {
        "username": "Tomás",
        "password": "1234",
        "display_name": "Tomás",
        "role": "Demo local",
    }
}
PUBLIC_PREFIXES = ("/login", "/assets/", "/favicon.ico")
PRIVATE_API_PREFIXES = ("/_dash", "/_dash-component-suites")


def _normalize_username(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").strip())
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_text.casefold()


def authenticate_user(username: str, password: str) -> dict | None:
    user = DEMO_USERS.get(_normalize_username(username))
    if not user or password != user["password"]:
        return None
    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
    }


def login_user(user: dict) -> None:
    session[SESSION_USER_KEY] = user
    session.permanent = True


def logout_user() -> None:
    session.pop(SESSION_USER_KEY, None)


def current_user() -> dict | None:
    return session.get(SESSION_USER_KEY)


def is_authenticated() -> bool:
    return SESSION_USER_KEY in session


def safe_next_path(raw_path: str | None) -> str:
    if not raw_path:
        return "/"
    if not raw_path.startswith("/") or raw_path.startswith("//"):
        return "/"
    if raw_path.startswith("/login") or raw_path.startswith("/logout"):
        return "/"
    return raw_path


def register_auth(server: Flask) -> None:
    server.secret_key = server.config.get("SECRET_KEY") or os.getenv("LEMON_DEMO_SECRET_KEY", "lemonbi-demo-secret")
    server.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=10)
    server.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    server.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    @server.before_request
    def guard_private_routes():
        path = request.path or "/"

        if path.startswith(PUBLIC_PREFIXES):
            if path.startswith("/login") and request.method == "GET" and is_authenticated():
                return redirect(safe_next_path(request.args.get("next")))
            return None

        if path.startswith("/logout"):
            return None

        if is_authenticated():
            return None

        if path.startswith(PRIVATE_API_PREFIXES):
            return abort(401)

        next_path = safe_next_path(request.full_path[:-1] if request.full_path.endswith("?") else request.full_path)
        return redirect(f"/login?next={quote(next_path)}")

    @server.route("/login", methods=["GET", "POST"])
    def login_route():
        if request.method == "GET":
            return render_login_page(
                error=request.args.get("error") == "1",
                next_path=safe_next_path(request.args.get("next")),
            )

        user = authenticate_user(
            username=request.form.get("username", ""),
            password=request.form.get("password", ""),
        )
        next_path = safe_next_path(request.form.get("next"))
        if not user:
            return redirect(f"/login?error=1&next={quote(next_path)}")

        login_user(user)
        return redirect(next_path)

    @server.route("/logout", methods=["GET"])
    def logout_route():
        logout_user()
        return redirect("/login")

    @server.after_request
    def add_session_headers(response):
        path = request.path or "/"
        if path.startswith("/assets/") or path.startswith("/_dash-component-suites"):
            return response

        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
