import os
from datetime import datetime, timedelta

from flask import current_app, flash, jsonify, redirect, request, url_for
from flask_login import login_required, current_user

from database.doctor_models import Appointment, Doctor
from database.user_models import Prediction
from .page_utils import format_local_datetime, page_response_payload, serve_page
from . import main_bp


def _remove_prediction_image_if_unused(image_path: str) -> None:
    image_file_path = os.path.join(current_app.root_path, image_path)
    image_still_used = Prediction.get_by_image_path(image_path) is not None

    if not image_still_used and os.path.exists(image_file_path):
        os.remove(image_file_path)


@main_bp.route("/")
def index():
    if current_user.is_authenticated and current_user.role == "admin":
        return redirect(url_for("admin.admin_dashboard"))
    return serve_page("pages/index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        return redirect(url_for("admin.admin_dashboard"))
    return serve_page("pages/dashboard/user_dashboard.html")


@main_bp.route("/scan")
@login_required
def scan():
    if current_user.role == "admin":
        return redirect(url_for("admin.admin_dashboard"))
    return serve_page("pages/scan.html")


@main_bp.route("/book-appointment")
def book_appointment():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard", _anchor="book-appointment"))
    return redirect(url_for("auth.login", next=url_for("main.dashboard", _anchor="book-appointment")))


@main_bp.route("/appointments", methods=["POST"])
@login_required
def create_appointment():
    doctor_id = request.form.get("doctor_id", type=int)
    appointment_date = request.form.get("appointment_date", type=str)
    appointment_time = request.form.get("appointment_time", type=str)

    if not doctor_id or not appointment_date or not appointment_time:
        flash("Please select a doctor, date, and time.", "warning")
        return redirect(url_for("main.dashboard"))

    doctor = Doctor.get_by_id(doctor_id)
    if doctor is None:
        flash("Selected doctor was not found.", "danger")
        return redirect(url_for("main.dashboard"))

    try:
        # Time inputs might include seconds (e.g. 14:30:00), we only want HH:MM
        appointment_time_hm = appointment_time[:5]
        appointment_at = datetime.strptime(
            f"{appointment_date} {appointment_time_hm}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        flash("Invalid appointment date or time.", "danger")
        return redirect(url_for("main.dashboard"))

    # Check if appointment date/time is in the past
    now = datetime.utcnow()
    if appointment_at < now:
        flash("Cannot book an appointment in the past. Please select a future date and time.", "danger")
        return redirect(url_for("main.dashboard"))

    # Enforce clinic hours: 9 AM – 7 PM
    if not (9 <= appointment_at.hour < 19):
        flash("Appointments can only be booked between 9:00 AM and 7:00 PM.", "danger")
        return redirect(url_for("main.dashboard"))

    Appointment.create(
        user_id=current_user.id,
        doctor_id=doctor.get("id"),
        appointment_time=appointment_at,
        status="successful",
    )

    flash(
        f"Appointment booked successfully with {doctor.get('name')} on {appointment_at.strftime('%d %b %Y at %I:%M %p')}.",
        "success",
    )
    return redirect(url_for("main.dashboard"))


@main_bp.route("/appointments/<int:appointment_id>/edit", methods=["POST"])
@login_required
def edit_appointment(appointment_id: int):
    appointment = Appointment.get_by_id(appointment_id)
    if not appointment:
        return jsonify({"error": "Appointment not found."}), 404

    if appointment.get("user_id") != current_user.id:
        return jsonify({"error": "Not allowed."}), 403

    appt_time = appointment.get("appointment_time")
    if appt_time:
        now = datetime.utcnow()
        one_day_before = appt_time - timedelta(days=1)
        if now >= one_day_before:
            return jsonify({"error": "Appointments can only be edited more than 24 hours before the scheduled time."}), 400

    doctor_id = request.form.get("doctor_id", type=int)
    appointment_date = request.form.get("appointment_date", type=str)
    appointment_time = request.form.get("appointment_time", type=str)

    if not doctor_id or not appointment_date or not appointment_time:
        return jsonify({"error": "Please provide doctor, date, and time."}), 400

    doctor = Doctor.get_by_id(doctor_id)
    if doctor is None:
        return jsonify({"error": "Selected doctor was not found."}), 400

    try:
        # Time inputs might include seconds (e.g. 14:30:00), we only want HH:MM
        appointment_time_hm = appointment_time[:5]
        new_time = datetime.strptime(f"{appointment_date} {appointment_time_hm}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({"error": "Invalid date or time format."}), 400

    if new_time <= datetime.utcnow():
        return jsonify({"error": "Cannot reschedule to a past date and time."}), 400

    # Enforce clinic hours: 9 AM – 7 PM
    if not (9 <= new_time.hour < 19):
        return jsonify({"error": "Appointments can only be scheduled between 9:00 AM and 7:00 PM."}), 400

    Appointment.update(appointment_id, doctor_id, new_time)
    return jsonify({"success": True, "message": f"Appointment updated to {new_time.strftime('%d %b %Y at %I:%M %p')} with {doctor.get('name')}."}), 200


@main_bp.route("/appointments/<int:appointment_id>/delete", methods=["POST"])
@login_required
def delete_appointment(appointment_id: int):
    appointment = Appointment.get_by_id(appointment_id)
    if not appointment:
        return jsonify({"error": "Appointment not found."}), 404

    if appointment.get("user_id") != current_user.id:
        return jsonify({"error": "Not allowed."}), 403

    Appointment.delete_by_id(appointment_id)
    return jsonify({"success": True, "message": "Appointment cancelled successfully."}), 200


@main_bp.route("/predictions/<int:prediction_id>/delete", methods=["POST"])
@login_required
def delete_prediction(prediction_id: int):
    prediction = Prediction.get_by_id(prediction_id)
    if not prediction:
        flash("Photo not found.", "warning")
        return redirect(url_for("main.dashboard"))

    if current_user.role != "admin" and prediction.get("user_id") != current_user.id:
        flash("You are not allowed to delete this photo.", "danger")
        return redirect(url_for("main.dashboard"))

    image_path = prediction.get("image_path")
    Prediction.delete_by_id(prediction_id)
    _remove_prediction_image_if_unused(image_path)

    flash("Photo deleted successfully.", "success")
    if current_user.role == "admin":
        return redirect(url_for("admin.admin_dashboard"))
    return redirect(url_for("main.dashboard"))


@main_bp.route("/predictions/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_predictions():
    prediction_ids = request.form.getlist("prediction_ids", type=int)
    if not prediction_ids:
        flash("Select at least one photo to delete.", "warning")
        return redirect(url_for("main.dashboard"))

    predictions = Prediction.get_by_ids(prediction_ids)
    allowed_predictions = [
        p for p in predictions if current_user.role == "admin" or p.get("user_id") == current_user.id
    ]

    if not allowed_predictions:
        flash("You are not allowed to delete the selected photos.", "danger")
        return redirect(url_for("main.dashboard"))

    deleted_count = 0
    image_paths = {prediction.get("image_path") for prediction in allowed_predictions if prediction.get("image_path")}
    for prediction in allowed_predictions:
        Prediction.delete_by_id(prediction.get("id"))
        deleted_count += 1

    for image_path in image_paths:
        _remove_prediction_image_if_unused(image_path)

    noun = "photo" if deleted_count == 1 else "photos"
    flash(f"{deleted_count} {noun} deleted successfully.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/api/dashboard")
@login_required
def dashboard_data():
    latest_prediction = Prediction.get_latest_for_user(current_user.id)
    predictions = Prediction.get_all_for_user(current_user.id)
    appointments = Appointment.for_user(current_user.id)
    doctors = Doctor.all_sorted_by_rating_name()

    chart_labels = []
    chart_values = []

    history_entries = [
        {
            "day_label": f"Day {index}",
            "prediction": {
                "id": prediction.get("id"),
                "image_path": prediction.get("image_path", "").replace("\\", "/"),
                "acne_type": prediction.get("acne_type"),
                "confidence": round(float(prediction.get("confidence", 0.0)), 4) if prediction.get("confidence") is not None else 0.0,
                "created_at": prediction.get("created_at").isoformat() if prediction.get("created_at") else None,
                "created_at_display": format_local_datetime(prediction.get("created_at")) if prediction.get("created_at") else None,
            },
        }
        for index, prediction in enumerate(predictions, start=1)
    ]

    next_appointment = next(
        (appointment for appointment in appointments if appointment.get("appointment_time") and appointment.get("appointment_time") >= datetime.utcnow()),
        appointments[0] if appointments else None,
    )

    appointment_payload = [
        {
            "id": appointment.get("id"),
            "doctor": {
                "id": appointment.get("doctor_id"),
                "name": appointment.get("doctor_name"),
                "specialization": appointment.get("doctor_specialization"),
            },
            "status": appointment.get("status"),
            "appointment_time": appointment.get("appointment_time").isoformat() if appointment.get("appointment_time") else None,
            "appointment_time_display": format_local_datetime(appointment.get("appointment_time")) if appointment.get("appointment_time") else None,
            # can_edit = appointment is in the future AND more than 24h away
            "can_edit": (
                appointment.get("appointment_time") is not None
                and appointment.get("appointment_time") > datetime.utcnow() + timedelta(days=1)
            ),
            # can_delete = appointment is still in the future
            "can_delete": (
                appointment.get("appointment_time") is not None
                and appointment.get("appointment_time") > datetime.utcnow()
            ),
        }
        for appointment in appointments
    ]
    doctor_payload = [
        {
            "id": doctor.get("id"),
            "name": doctor.get("name"),
            "specialization": doctor.get("specialization"),
            "location": doctor.get("location"),
            "experience_years": doctor.get("experience_years"),
            "rating": doctor.get("rating"),
        }
        for doctor in doctors
    ]

    next_appointment_payload = None
    if next_appointment is not None:
        next_appointment_payload = {
            "id": next_appointment.get("id"),
            "doctor": {
                "id": next_appointment.get("doctor_id"),
                "name": next_appointment.get("doctor_name"),
                "specialization": next_appointment.get("doctor_specialization"),
            },
            "status": next_appointment.get("status"),
            "appointment_time": next_appointment.get("appointment_time").isoformat() if next_appointment.get("appointment_time") else None,
            "appointment_time_display": format_local_datetime(next_appointment.get("appointment_time")) if next_appointment.get("appointment_time") else None,
        }

    latest_prediction_payload = None
    if latest_prediction is not None:
        latest_prediction_payload = {
            "id": latest_prediction.get("id"),
            "acne_type": latest_prediction.get("acne_type"),
            "confidence": round(float(latest_prediction.get("confidence", 0.0)), 4) if latest_prediction.get("confidence") is not None else 0.0,
        }

    profile_ready = current_user.age is not None and bool(current_user.skin_type)

    return page_response_payload(
        current_user,
        profile_ready=profile_ready,
        latest_prediction=latest_prediction_payload,
        history_entries=history_entries,
        appointments=appointment_payload,
        doctors=doctor_payload,
        next_appointment=next_appointment_payload,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )

