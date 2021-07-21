from flask import Blueprint, request, render_template, url_for
import common
from models import UserType, User, Workspace
from routes.authentication import auth_or_login

bp = Blueprint('workspaces', __name__, url_prefix='/workspace')


@bp.route('/<wid>', methods=['GET', 'POST'])
def workspace(wid):
    workspace = Workspace.query.get(wid)
    user = False

    if workspace is not None:
        uid = workspace.owner
        if uid is not None:
            user = True
            auth_or_login(minimum_credential=UserType.STUDENT)

    return render_template(common.USER_WORKSPACE_TEMPLATE, user=user)



