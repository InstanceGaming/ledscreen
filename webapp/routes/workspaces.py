import logging

from flask import Blueprint, request, render_template, url_for
from models import UserType, Workspace
from routes.authentication import auth_or_login
from database import session
from datetime import datetime as dt
import common

LOG = logging.getLogger('ledscreen.web.workspaces')
bp = Blueprint('workspaces', __name__, url_prefix='/workspace')


@bp.route('/<wid>', methods=['GET', 'POST'])
def workspace(wid):
    with session.begin():
        workspace = Workspace.query.get(wid)

    user = False

    if workspace is not None:
        uid = workspace.owner
        if uid is not None:
            user = True
            auth_or_login(minimum_credential=UserType.STUDENT)

    workspace.opened_at = dt.utcnow()
    return render_template(common.USER_WORKSPACE_TEMPLATE, user=user)
