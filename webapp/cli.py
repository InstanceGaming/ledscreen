import argparse
import logging
import system
import database
import common
from utils import load_config, configure_logger
from sqlalchemy.exc import SQLAlchemyError

configure_logger(logging.getLogger('sqlalchemy'), prod_level=logging.WARNING)
configure_logger(logging.getLogger('sqlalchemy.engine.Engine'), prod_level=logging.WARNING)


def parse_args():
    ap = argparse.ArgumentParser(description='Utility command-line script for automating application tasks')
    subparsers = ap.add_subparsers(dest='command')
    subparsers.add_parser('reset')
    subparsers.add_parser('setup-db')
    sp_create_user = subparsers.add_parser('create-user')
    sp_create_user.add_argument('-p',
                                type=str,
                                nargs=1,
                                metavar='PASSWORD',
                                const=None,
                                dest='password',
                                help='Require this password to login.')
    sp_create_user.add_argument(type=str,
                                dest='user_type',
                                metavar='TYPE',
                                choices=['admin'],
                                help='User privilege level.')
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
    common.config = config
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
        system.reset()

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

        user_name = cla.user_name
        password = cla.password

        try:
            user = system.create_user(user_type,
                                      user_name,
                                      password=password,
                                      lock=False)
            print(user.uid)
            exit(0)
        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            exit(100)

    print('Nothing to do')
    exit(1)
else:
    print('This script must be ran directly')
    exit(1)
