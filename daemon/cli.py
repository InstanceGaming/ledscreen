import argparse
import logging
import dateparser
import system
import database
from utils import load_config
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s][%(module)s:%(lineno)s]: %(message)s')


def parse_args():
    ap = argparse.ArgumentParser(description='Utility command-line script for automating application tasks')
    subparsers = ap.add_subparsers(dest='command')
    sp_reset = subparsers.add_parser('reset')
    sp_reset.add_argument('--archive', '-a',
                          type=str,
                          nargs=1,
                          metavar='DIRECTORY',
                          dest='archive_dir',
                          help='Archive user data to this directory.')
    subparsers.add_parser('setup-db')
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
    reset = cla.command == 'reset'
    archive_dir = cla.archive_dir[0]

    config = load_config()
    uri = config['database.uri']
    database.init(uri)

    if setup_db:
        try:
            import models

            database.create_tables()
        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            exit(100)

        print('Setup database successfully.')
        exit(0)
    elif reset:
        system.reset(archive_dir=archive_dir)

        print('Reset successful.')
        exit(0)
    else:
        if create_user:
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
                try:
                    expiry = dateparser.parse(expiry_text)
                except ValueError:
                    print('Invalid expiry format')
                    exit(201)

            user_name = cla.user_name
            lock = cla.lock
            password = cla.password

            try:
                user = system.create_user(user_type,
                                          user_name,
                                          expiry=expiry,
                                          password=password,
                                          lock=lock)
                if user is not None:
                    print(user.uid)
                    exit(0)
                else:
                    print('Failed to create user (one of this type already exists)')
                    exit(202)
            except SQLAlchemyError as e:
                print(f'Database error: {e}')
                exit(100)

    print('Nothing to do.')
    exit(1)
else:
    print('This script must be ran directly.')
    exit(1)
