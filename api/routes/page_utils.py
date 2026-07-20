from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import current_app, get_flashed_messages, jsonify, send_from_directory


def serve_page(page_path: str):
    return send_from_directory(current_app.static_folder, page_path)


def serialize_user(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "skin_type": user.skin_type,
        "role": user.role,
    }


def format_local_datetime(value, fmt="%d %b %Y, %I:%M %p"):
    if value is None:
        return ""

    print("Database value:", value)
    print("Timezone:", value.tzinfo)

    app_timezone = ZoneInfo(current_app.config.get("APP_TIMEZONE", "Asia/Kathmandu"))

    if value.tzinfo is None:
        value = value.replace(tzinfo=app_timezone)

    return value.astimezone(app_timezone).strftime(fmt)

def flash_payload():
    messages = get_flashed_messages(with_categories=True)
    return [{"category": category, "message": message} for category, message in messages]


def page_response_payload(user=None, **extra):
    payload = {
        "authenticated": bool(user and getattr(user, "is_authenticated", False)),
        "flash_messages": flash_payload(),
    }
    if payload["authenticated"]:
        payload["user"] = serialize_user(user)
    else:
        payload["user"] = None
    payload.update(extra)
    return jsonify(payload)
