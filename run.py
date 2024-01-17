# -*- encoding: utf-8 -*-


import os
from flask_script import Manager
from flask_migrate import Migrate
from  flask_minify  import Minify
from  sys import exit

from apps.config import config_dict
from apps import create_app, db
from flask_wtf.csrf import CSRFProtect

from apps.commands.create_admin import CreateAdmin

from ftp_server import testFTPConnection

# WARNING: Don't run with debug turned on in production!
DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
# The configuration
get_config_mode = 'Debug' if DEBUG else 'Production'

try:
    # Load the configuration using the default values
    app_config = config_dict[get_config_mode.capitalize()]

except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

app = create_app(app_config)
csrf = CSRFProtect(app)
app.config['ENV'] = get_config_mode.capitalize()
Migrate(app, db)

if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)

@app.cli.command("create_admin")
def create_admin():

    # Make sure we have the tables
    db.create_all()

    # Create the admin user
    CreateAdmin.create_admin()

@app.cli.command("test_ftp")
def test_ftp():

    if testFTPConnection():
        app.logger.info( 'FTP connection OK' )
    else:
        app.logger.info( 'FTP connection ERROR' )


if DEBUG:
    app.logger.info('DEBUG            = ' + str(DEBUG)             )
    app.logger.info('Page Compression = ' + 'FALSE' if DEBUG else 'TRUE' )
    app.logger.info('DBMS             = ' + app_config.SQLALCHEMY_DATABASE_URI)
    app.logger.info('ASSETS_ROOT      = ' + app_config.ASSETS_ROOT )

if __name__ == "__main__":
    with app.app_context():
        manager.run()
