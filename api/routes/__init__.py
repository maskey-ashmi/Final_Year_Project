from flask import Blueprint

auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)
prediction_bp = Blueprint("prediction", __name__)
admin_bp = Blueprint("admin", __name__)

