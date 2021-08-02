import argparse
import logging
import os
import system
import database
import utils
import spreadsheets as ss
import common
from models import RunTarget
from utils import load_config, configure_logger
from sqlalchemy.exc import SQLAlchemyError


configure_logger(logging.getLogger('sqlalchemy'), prod_level=logging.WARNING)
configure_logger(logging.getLogger('sqlalchemy.engine.Engine'), prod_level=logging.WARNING)


def pretty_roster_errors(errors):
    print(f'{len(errors)} errors found in first sheet of workbook:')

    for i, error in enumerate(errors, start=1):
        print(f'  {i}. At {error.cell_notation()}, {error.message}')


def parse_args():
    ap = argparse.ArgumentParser(description='Utility command-line script for automating application tasks')
    subparsers = ap.add_subparsers(dest='command')
    sp_reset = subparsers.add_parser('reset')
    sp_reset.add_argument('--archive', '-a',
                          action='store_true',
                          dest='archive',
                          help='Create archives of user data.')
    subparsers.add_parser('setup-db')
    sp_reset = subparsers.add_parser('import-students')
    sp_reset.add_argument(type=str,
                          dest='workbook_path',
                          metavar='WORKBOOK',
                          help='Path to a XLSX workbook with student account info.')
    sp_reset = subparsers.add_parser('validate-roster')
    sp_reset.add_argument(type=str,
                          dest='workbook_path',
                          metavar='WORKBOOK',
                          help='Path to a XLSX workbook with student account info.')
    sp_create_user = subparsers.add_parser('create-user')
    sp_create_user.add_argument('-p',
                                type=str,
                                nargs=1,
                                metavar='PASSWORD',
                                const=None,
                                dest='password',
                                help='Require this password to login.')
    sp_create_user.add_argument('-e', '--expiry',
                                type=str,
                                nargs=1,
                                metavar='DATETIME',
                                const=None,
                                dest='expiry',
                                help='User will be marked as expired after this datetime.')
    sp_create_user.add_argument('-l',
                                action='store_true',
                                dest='lock',
                                help='Lock user account by default.')
    sp_create_user.add_argument('-r',
                                type=str,
                                nargs=1,
                                metavar='TARGET',
                                dest='run_privilege',
                                choices=RunTarget.names(),
                                default=RunTarget.SIMULATE.name,
                                help='Set user run privilege. Default is SIMULATE.')
    sp_create_user.add_argument('-M',
                                type=int,
                                nargs=1,
                                metavar='SECONDS',
                                dest='max_runtime',
                                help='Set user max run time.')
    sp_create_user.add_argument(type=str,
                                dest='user_type',
                                metavar='TYPE',
                                choices=['student', 'admin'],
                                help='User privilege level. "student" or "admin".')
    sp_create_user.add_argument(type=str,
                                dest='user_name',
                                metavar='NAME',
                                help='The new users name.')

    return ap.parse_args()


if __name__ == '__main__':
    cla = parse_args()
    setup_db = cla.command == 'setup-db'
    create_user = cla.command == 'create-user'
    import_students = cla.command == 'import-students'
    validate_roster = cla.command == 'validate-roster'
    reset = cla.command == 'reset'

    config = load_config()
    common.init_minimum(config)
    uri = config['database.uri']
    database.init(uri)

    if setup_db:
        try:
            import models

            database.setup()
        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            exit(100)

        print('Setup database successfully')
        exit(0)
    elif reset:
        system.reset(cla.archive)

        print('Reset successful')
        exit(0)
    elif create_user:
        from models import UserType

        user_type_text = cla.user_type
        user_type = None

        try:
            user_type = UserType[user_type_text.upper()]
        except ValueError:
            print('Invalid user type')
            exit(200)

        expiry_text = cla.expiry
        expiry = None

        if expiry_text is not None:
            expiry = utils.parse_account_expiry(expiry_text)
            if expiry is None:
                print('Invalid expiry format')
                exit(201)

        user_name = cla.user_name
        lock = cla.lock
        password = cla.password

        run_privilege_text = cla.run_privilege

        try:
            run_privilege = RunTarget[run_privilege_text.upper()]
        except KeyError:
            print('Invalid run privilege')
            exit(202)

        max_runtime = cla.max_runtime

        if max_runtime is not None and max_runtime < 2:
            print('Max runtime must be at least 2 seconds')
            exit(203)

        try:
            workspace = system.create_workspace(run_privilege=run_privilege,
                                                max_runtime=max_runtime)
            user = system.create_user(user_type,
                                      user_name,
                                      workspace.wid,
                                      expiry=expiry,
                                      password=password,
                                      lock=lock)
            print(user.uid)
            exit(0)
        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            exit(100)
    elif import_students:
        workbook_path = cla.workbook_path

        if os.path.exists(workbook_path):
            try:
                roster = ss.load_student_roster(workbook_path)
            except OSError as e:
                print(f'Failed to load workbook: {str(e)}')
                exit(301)

            errors = ss.validate_roster(roster)

            if len(errors) > 0:
                pretty_roster_errors(errors)
                exit(302)
            else:
                simplified = ss.transform_roster(roster)
                count = system.bulk_create_students(simplified)
                print(f'Created {count} student accounts')
                exit(0)
        else:
            print(f'Workbook not found at "{workbook_path}"')
            exit(300)
    elif validate_roster:
        workbook_path = cla.workbook_path

        if os.path.exists(workbook_path):
            try:
                roster = ss.load_student_roster(workbook_path)
            except OSError as e:
                print(f'Failed to load workbook: {str(e)}')
                exit(401)

            errors = ss.validate_roster(roster)

            if len(errors) > 0:
                pretty_roster_errors(errors)
                exit(402)
            else:
                print(f'Valid')
                exit(0)
        else:
            print(f'Workbook not found at "{workbook_path}"')
            exit(400)

    print('Nothing to do')
    exit(1)
else:
    print('This script must be ran directly')
    exit(1)
