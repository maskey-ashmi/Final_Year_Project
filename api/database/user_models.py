from datetime import datetime
from flask_login import UserMixin
from .db import query_one, query_all, execute, login_manager


@login_manager.user_loader
def load_user(user_id):
    row = query_one("SELECT * FROM users WHERE id=%s", (int(user_id),))
    return User.from_row(row) if row else None


class User(UserMixin):
    def __init__(self, id, name, email, password_hash, age, skin_type, role, created_at):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.age = age
        self.skin_type = skin_type
        self.role = role
        self.created_at = created_at

    def get_id(self):
        return str(self.id)

    @staticmethod
    def from_row(row):
        if not row:
            return None
        return User(
            id=row.get("id"),
            name=row.get("name"),
            email=row.get("email"),
            password_hash=row.get("password_hash"),
            age=row.get("age"),
            skin_type=row.get("skin_type"),
            role=row.get("role"),
            created_at=row.get("created_at"),
        )

    @classmethod
    def get_by_email(cls, email):
        row = query_one("SELECT * FROM users WHERE email=%s", (email,))
        return cls.from_row(row)

    @classmethod
    def create(cls, name, email, password_hash, age=None, skin_type=None, role="user"):
        execute(
            "INSERT INTO users (name, email, password_hash, age, skin_type, role, created_at) VALUES (%s,%s,%s,%s,%s,%s,NOW())",
            (name, email, password_hash, age, skin_type, role),
        )
        return cls.get_by_email(email)

    @staticmethod
    def update_skin_type(user_id, skin_type):
        execute(
            "UPDATE users SET skin_type=%s WHERE id=%s",
            (skin_type, user_id),
        )

    @staticmethod
    def count():
        row = query_one("SELECT COUNT(*) AS c FROM users")
        return int(row.get("c", 0)) if row else 0

    @staticmethod
    def recent(limit=10):
        return query_all("SELECT * FROM users ORDER BY created_at DESC LIMIT %s", (limit,))


class Prediction:
    @staticmethod
    def create(user_id, image_path, acne_type, confidence, severity, notes=None):
        execute(
            "INSERT INTO predictions (user_id, image_path, acne_type, confidence, severity, notes, created_at) VALUES (%s,%s,%s,%s,%s,%s,NOW())",
            (user_id, image_path, acne_type, confidence, severity, notes),
        )

    @staticmethod
    def count():
        row = query_one("SELECT COUNT(*) AS c FROM predictions")
        return int(row.get("c", 0)) if row else 0

    @staticmethod
    def get_most_common_condition():
        row = query_one("SELECT acne_type, COUNT(*) as c FROM predictions GROUP BY acne_type ORDER BY c DESC LIMIT 1")
        return row.get("acne_type") if row else "N/A"

    @staticmethod
    def recent(limit=12):
        return query_all("SELECT * FROM predictions ORDER BY created_at DESC LIMIT %s", (limit,))

    @staticmethod
    def get_by_id(prediction_id):
        row = query_one("SELECT * FROM predictions WHERE id=%s", (prediction_id,))
        return row

    @staticmethod
    def get_by_image_path(image_path):
        return query_one("SELECT * FROM predictions WHERE image_path=%s LIMIT 1", (image_path,))

    @staticmethod
    def delete_by_id(prediction_id):
        execute("DELETE FROM predictions WHERE id=%s", (prediction_id,))

    @staticmethod
    def get_by_ids(ids):
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        sql = f"SELECT * FROM predictions WHERE id IN ({placeholders})"
        return query_all(sql, tuple(ids))

    @staticmethod
    def get_latest_for_user(user_id):
        return query_one("SELECT * FROM predictions WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (user_id,))

    @staticmethod
    def get_all_for_user(user_id):
        return query_all("SELECT * FROM predictions WHERE user_id=%s ORDER BY created_at ASC", (user_id,))


class Routine:
    @staticmethod
    def create(user_id, acne_type, age, skin_type, steps):
        execute(
            "INSERT INTO routines (user_id, acne_type, age, skin_type, steps, created_at) VALUES (%s,%s,%s,%s,%s,NOW())",
            (user_id, acne_type, age, skin_type, steps),
        )

