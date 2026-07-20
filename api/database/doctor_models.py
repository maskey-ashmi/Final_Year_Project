from .db import query_one, query_all, execute


class Doctor:
    @staticmethod
    def all():
        return query_all("SELECT * FROM doctors")

    @staticmethod
    def get_by_id(doctor_id):
        return query_one("SELECT * FROM doctors WHERE id=%s", (doctor_id,))

    @staticmethod
    def all_sorted_by_rating_name():
        return query_all("SELECT * FROM doctors ORDER BY rating DESC, name ASC")

    @staticmethod
    def create(name, specialization, location=None, experience_years=None, rating=None):
        execute(
            "INSERT INTO doctors (name, specialization, location, experience_years, rating, created_at) VALUES (%s,%s,%s,%s,%s,NOW())",
            (name, specialization, location, experience_years, rating),
        )

    @staticmethod
    def update(doctor_id, name, specialization, location=None, experience_years=None, rating=None):
        execute(
            "UPDATE doctors SET name=%s, specialization=%s, location=%s, experience_years=%s, rating=%s WHERE id=%s",
            (name, specialization, location, experience_years, rating, doctor_id),
        )


class Appointment:
    @staticmethod
    def recent(limit=10):
        # join with doctors for convenience
        sql = """
        SELECT a.*, d.id AS doctor_id, d.name AS doctor_name, d.specialization AS doctor_specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.appointment_time DESC
        LIMIT %s
        """
        return query_all(sql, (limit,))

    @staticmethod
    def get_by_id(appointment_id):
        sql = """
        SELECT a.*, d.id AS doctor_id, d.name AS doctor_name, d.specialization AS doctor_specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.id = %s
        """
        return query_one(sql, (appointment_id,))

    @staticmethod
    def create(user_id, doctor_id, appointment_time, status="pending"):
        execute(
            "INSERT INTO appointments (user_id, doctor_id, appointment_time, status, created_at) VALUES (%s,%s,%s,%s,NOW())",
            (user_id, doctor_id, appointment_time, status),
        )

    @staticmethod
    def update(appointment_id, doctor_id, appointment_time):
        execute(
            "UPDATE appointments SET doctor_id=%s, appointment_time=%s WHERE id=%s",
            (doctor_id, appointment_time, appointment_id),
        )

    @staticmethod
    def delete_by_id(appointment_id):
        execute("DELETE FROM appointments WHERE id=%s", (appointment_id,))

    @staticmethod
    def for_user(user_id):
        sql = """
        SELECT a.*, d.id AS doctor_id, d.name AS doctor_name, d.specialization AS doctor_specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id = %s
        ORDER BY a.appointment_time DESC
        """
        return query_all(sql, (user_id,))


