from flask_login import login_required, current_user

from database.doctor_models import Appointment, Doctor
from database.user_models import Prediction, User
from . import admin_bp
from .page_utils import format_local_datetime, page_response_payload, serve_page


@admin_bp.route("/admin")
@login_required
def admin_dashboard():
    return serve_page("pages/dashboard/admin_dashboard.html")


@admin_bp.route("/api/admin/dashboard")
@login_required
def admin_dashboard_data():
    if current_user.role != "admin":
        return page_response_payload(current_user, unauthorized=True)

    users_count = User.count()
    scans_count = Prediction.count()
    most_common_condition = Prediction.get_most_common_condition()
    doctors = Doctor.all()
    appointments = Appointment.recent(10)
    predictions = Prediction.recent(12)
    users = User.recent(10)

    return page_response_payload(
        current_user,
        unauthorized=False,
        users_count=users_count,
        scans_count=scans_count,
        most_common_condition=most_common_condition,
        doctors=[
            {
                "id": doctor.get("id"),
                "name": doctor.get("name"),
                "specialization": doctor.get("specialization"),
                "location": doctor.get("location"),
                "experience_years": doctor.get("experience_years"),
                "rating": doctor.get("rating"),
            }
            for doctor in doctors
        ],
        appointments=[
            {
                "id": appointment.get("id"),
                "user_id": appointment.get("user_id"),
                "status": appointment.get("status"),
                "doctor": {
                    "id": appointment.get("doctor_id"),
                    "name": appointment.get("doctor_name"),
                },
                "appointment_time": appointment.get("appointment_time").isoformat() if appointment.get("appointment_time") else None,
                "appointment_time_display": format_local_datetime(appointment.get("appointment_time")) if appointment.get("appointment_time") else None,
            }
            for appointment in appointments
        ],
        predictions=[
            {
                "id": prediction.get("id"),
                "user_id": prediction.get("user_id"),
                "image_path": prediction.get("image_path", "").replace("\\", "/"),
                "acne_type": prediction.get("acne_type"),
                "confidence": round(float(prediction.get("confidence", 0.0)), 4) if prediction.get("confidence") is not None else 0.0,
                "created_at": prediction.get("created_at").isoformat() if prediction.get("created_at") else None,
                "created_at_display": format_local_datetime(prediction.get("created_at")) if prediction.get("created_at") else None,
            }
            for prediction in predictions
        ],
        users=[
            {
                "id": user.get("id"),
                "name": user.get("name"),
                "email": user.get("email"),
                "role": user.get("role"),
                "skin_type": user.get("skin_type"),
            }
            for user in users
        ],
    )


@admin_bp.route("/admin/doctors/add", methods=["POST"])
@login_required
def add_doctor():
    if current_user.role != "admin":
        from flask import flash, redirect, url_for
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))

    from flask import request, flash, redirect, url_for
    name = request.form.get("name")
    specialization = request.form.get("specialization")
    location = request.form.get("location")
    experience_years = request.form.get("experience_years", type=int)
    rating = request.form.get("rating", type=float)

    if not name or not specialization:
        flash("Doctor name and specialization are required.", "warning")
    else:
        Doctor.create(name, specialization, location, experience_years, rating)
        flash("Doctor added successfully.", "success")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/doctors/<int:doctor_id>/edit", methods=["POST"])
@login_required
def edit_doctor(doctor_id):
    if current_user.role != "admin":
        from flask import flash, redirect, url_for
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))

    from flask import request, flash, redirect, url_for
    name = request.form.get("name")
    specialization = request.form.get("specialization")
    location = request.form.get("location")
    experience_years = request.form.get("experience_years", type=int)
    rating = request.form.get("rating", type=float)

    if not name or not specialization:
        flash("Doctor name and specialization are required.", "warning")
    else:
        Doctor.update(doctor_id, name, specialization, location, experience_years, rating)
        flash("Doctor updated successfully.", "success")

    return redirect(url_for("admin.admin_dashboard"))

