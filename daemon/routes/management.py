from flask import Blueprint, render_template, abort, request
from models import UserType, User
from common import MANAGEMENT_TEMPLATE, PROGRAMS
from .authentication import auth_or_login


bp = Blueprint('manage', __name__, url_prefix='/manage')


@bp.route('/', methods=['GET'])
def index():
    auth_or_login(minimum_credential=UserType.ADMIN)

    users = User.query.filter_by(type=UserType.STUDENT).all()
    statistics = {
        'Students Online': 8,
        'Runs': 48,
        'Exceptions': 23,
        'Syntax Errors': 5,
        'Registered Students': 39,
        'Workspaces': 39
    }

    return render_template(MANAGEMENT_TEMPLATE,
                           students=users,
                           programs=PROGRAMS,
                           statistics=statistics)
