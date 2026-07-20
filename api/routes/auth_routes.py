from flask import redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from database.db import bcrypt
from database.user_models import User
from .page_utils import page_response_payload, serve_page
from . import auth_bp


@auth_bp.route("/api/session")
def session_state():
    return page_response_payload(current_user)


@auth_bp.route("/api/update_skin_type", methods=["POST"])
@login_required
def update_skin_type():
    data = request.get_json()
    skin_type = data.get("skin_type")
    if not skin_type:
        return {"error": "Missing skin_type"}, 400
    User.update_skin_type(current_user.id, skin_type)
    # Update in-memory user object
    current_user.skin_type = skin_type
    return page_response_payload(current_user)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        age = request.form.get("age")


        existing = User.get_by_email(email)
        if existing:
            flash("Email already registered.", "warning")
            return redirect(url_for("auth.signup"))

        pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User.create(
            name=name,
            email=email,
            password_hash=pw_hash,
            age=int(age) if age else None,
        )

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return serve_page("pages/auth/signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    mode = request.args.get("mode", "user")
    next_page = request.args.get("next")

    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        mode = request.form.get("mode", mode)
        next_page = request.form.get("next") or next_page

        user = User.get_by_email(email)
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if mode == "admin" and user.role != "admin":
                flash("This portal is reserved for practitioners and admin accounts.", "warning")
                return redirect(url_for("auth.login", mode=mode, next=next_page))

            login_user(user, remember=True)
            flash("Logged in successfully.", "success")
            if next_page:
                return redirect(next_page)
            if user.role == "admin":
                return redirect(url_for("admin.admin_dashboard"))
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "danger")

    return serve_page("pages/auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))




