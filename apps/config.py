# -*- encoding: utf-8 -*-

import os
import random
import string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import sqlite3

class Email_config(object):
    MAIL_USERNAME = 'vocasaracontactapp@gmail.com'
    MAIL_PASSWORD = 'oviq vypu oozz cjou'
    MAIL_DEFAULT_SENDER = 'vocasaracontactapp@gmail.com'
    
    
class Config(object):
    

    USERS_ROLES  = { 'ADMIN'  :1 , 'USER'      : 2 }
    USERS_STATUS = { 'ACTIVE' :1 , 'SUSPENDED' : 2 }
    
    # USERS_STATUS = { 'ACTIVE' :1 , 'SUSPENDED' : 2 }
    # check verified_email
    VERIFIED_EMAIL = { 'verified' :1 , 'not-verified' : 2 }

    LOGIN_ATTEMPT_LIMIT = 3

    DEFAULT_IMAGE_URL =  'static/assets/images/'
  
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Set up the App SECRET_KEY
    SECRET_KEY  = os.getenv('SECRET_KEY', None)
    if not SECRET_KEY:
        SECRET_KEY = ''.join(random.choice( string.ascii_lowercase  ) for i in range( 32 ))

    SECURITY_PASSWORD_SALT = 'f495b66803a6512d'

    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')
    
    # Social AUTH Settings
    OAUTHLIB_INSECURE_TRANSPORT = os.getenv('OAUTHLIB_INSECURE_TRANSPORT')

    # Mail Settings
    MAIL_SERVER   = os.getenv('MAIL_SERVER')
    MAIL_PORT     = os.getenv('MAIL_PORT')

    # Mail Authentication
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_USE_TLS  = True

    # Mail Accounts
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

#base de donnee
    #DB_ENGINE = os.getenv('DB_ENGINE', 'mysql+pyodbc')
    DB_USERNAME = os.getenv('DB_USERNAME', 'client')
    DB_PASS = os.getenv('DB_PASS', '1234')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'root')

    USE_SQLITE = False
    # try to set up a Relational DBMS
    if  DB_NAME and DB_USERNAME:

        try:
            
            # Relational DBMS: PSQL, MySql
            SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{DB_USERNAME}:{DB_PASS}@{DB_HOST}/{DB_NAME}'

            USE_SQLITE = False

        except OperationalError as e:
            print('> Error: DBMS Exception: ' + str(e))
            print('> Fallback to SQLite ')
            USE_SQLITE = True

    if USE_SQLITE:

        # Use SQLite if the connection to SQL Server fails
        try:
            # This will create a file in <app> FOLDER
            SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')

            # Check if the SQLite database file exists, if not, create it
            if not os.path.exists(os.path.join(basedir, 'db.sqlite3')):
                conn = sqlite3.connect(os.path.join(basedir, 'db.sqlite3'))
                conn.close()

        except Exception as e:
            print('> Error: SQLite Exception: ' + str(e))
            raise

class ProductionConfig(Config):

    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 36000

class DebugConfig(Config):
    DEBUG = True

# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug'     : DebugConfig
}