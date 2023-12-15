# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os, random, string
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

class Config(object):
    
    # for Product model iii
    CURRENCY     = { 'usd' : 'usd' , 'eur' : 'eur' }
    STATE        = { 'completed' : 1 , 'pending' : 2, 'refunded' : 3 }
    PAYMENT_TYPE = { 'cc' : 1 , 'paypal' : 2, 'wire' : 3 }
    
    USERS_ROLES  = { 'ADMIN'  :1 , 'USER'      : 2 }
    USERS_STATUS = { 'ACTIVE' :1 , 'SUSPENDED' : 2 }
    
    # USERS_STATUS = { 'ACTIVE' :1 , 'SUSPENDED' : 2 }
    # check verified_email
    VERIFIED_EMAIL = { 'verified' :1 , 'not-verified' : 2 }

    LOGIN_ATTEMPT_LIMIT = 3

    DEFAULT_IMAGE_URL =  'static/assets/images/'

    # Read the optional FTP values
    FTP_SERVER   = os.getenv( 'FTP_SERVER'   )
    FTP_USER     = os.getenv( 'FTP_USER'     )
    FTP_PASSWORD = os.getenv( 'FTP_PASSWORD' )
    FTP_WWW_ROOT = os.getenv( 'FTP_WWW_ROOT' )

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

    SOCIAL_AUTH_GITHUB  = False
    SOCIAL_AUTH_TWITTER = False

    GITHUB_ID      = os.getenv('GITHUB_ID')
    GITHUB_SECRET  = os.getenv('GITHUB_SECRET')

    # Enable/Disable Github Social Login    
    if GITHUB_ID and GITHUB_SECRET:
         SOCIAL_AUTH_GITHUB  = True

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

    DB_ENGINE   = os.getenv('DB_ENGINE'   , None)
    DB_USERNAME = os.getenv('DB_USERNAME' , None)
    DB_PASS     = os.getenv('DB_PASS'     , None)
    DB_HOST     = os.getenv('DB_HOST'     , None)
    DB_NAME     = os.getenv('DB_NAME'     , None)

    USE_SQLITE  = True 

    # try to set up a Relational DBMS
    if DB_ENGINE and DB_NAME and DB_USERNAME:

        try:
            
            # Relational DBMS: PSQL, MySql
            SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc://{DB_USERNAME}:{DB_PASS}@{DB_HOST}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"

            USE_SQLITE  = False

        except Exception as e:

            print('> Error: DBMS Exception: ' + str(e) )
            print('> Fallback to SQLite ')    

    if USE_SQLITE:

        # This will create a file in <app> FOLDER
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')    
    
class ProductionConfig(Config):

    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

class DebugConfig(Config):
    DEBUG = True


# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug'     : DebugConfig
}