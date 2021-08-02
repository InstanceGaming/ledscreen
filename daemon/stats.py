from datetime import datetime, timedelta
from database import session
from models import User, UserType, RunLog


def get_stats():
    return get_student_count(), get_online_student_count(), get_execution_count()


def get_student_count():
    with session.begin():
        return User.query.filter(User.type == UserType.STUDENT).count()


def get_online_student_count():
    with session.begin():
        return User.query.filter(
            User.type == UserType.STUDENT and User.login_at is not None and (User.login_at > User.logout_at)).count()


def get_execution_count():
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    with session.begin():
        return RunLog.query.filter(RunLog.started_at >= one_hour_ago).count()

