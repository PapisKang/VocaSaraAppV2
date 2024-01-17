# [Soft UI Dashboard PRO Flask](https://appseed.us/product/soft-ui-dashboard-pro/flask/)

Premium **Flask Dashboard** project crafted on top of **[Soft UI Dashboard PRO](https://appseed.us/product/soft-ui-dashboard-pro/flask/)**, a pixel-perfect `Bootstrap 5` design from `Creative-Tim`. 

Designed for those who like bold elements and beautiful websites, **Soft UI Dashboard** is ready to help you create stunning websites and webapps. **Soft UI Dashboard** is built with over 300+ frontend individual elements, like buttons, inputs, navbars, nav tabs, cards, or alerts, giving you the freedom of choosing and combining.

- 👉 [Soft UI Dashboard PRO Flask](https://appseed.us/product/soft-ui-dashboard-pro/flask) - Product Page
- 👉 [Soft UI Dashboard PRO Flask](https://flask-soft-dashboard-enh.appseed-srv1.com/) - LIVE Demo

<br />

## ✅ Features 

- `DB Tools`: SQLAlchemy ORM, `Flask-Migrate` (schema migrations)
- `Persistence`:
  - `SQLite` & `MySql` 
- `Authentication`
  - Session Based (via **flask_login**)
  - `Social Login` (optional) for **Github** 
  - Automatic suspension on failed logins 
- `Users Management` 
  - `Extended user profile`
  - Complete Users management (for `Admins`) 
- `API` via Flask-RestX
  - Path: `/api/` 
  - `Products`, `Sales` Models   
- `Deployment`
  - `Docker`
  - Page Compression via `Flask-Minify` (for production)

![Soft UI Dashboard PRO - Starter generated by AppSeed.](https://user-images.githubusercontent.com/51070104/170829870-8acde5af-849a-4878-b833-3be7e67cff2d.png)

<br />

## ✅ Start in `Docker`

> **Step 1** - Download and unzip the sources

```bash
$ # Get the code
$ unzip flask-soft-ui-dashboard-enh.zip
$ cd flask-soft-ui-dashboard-enh
```

<br />

> **Step 2** - Start the APP in `Docker`

```bash
$ docker-compose up --build 
```

Visit `http://localhost:5085` in your browser. The app should be up & running.

<br />

## ✅ Create`.env` file

The meaning of each variable can be found below: 

- `FLASK_DEBUG`: `1` (development) or `0` (production) 
- Flask `environment variables` (used in development)
  - `FLASK_APP=run.py`
- `ASSETS_ROOT`: used in assets management
  - default value: `/static/assets`
- Persistence: SQLite used by default
- For `MYSQL`:
  - install the driver: `pip install flask_mysqldb`
  - edit `.env` 
    - `DB_ENGINE`, default value = `mysql`
    - `DB_NAME`, default value = `appseed_db`
    - `DB_HOST`, default value = `localhost`
    - `DB_PORT`, default value = `3306`
    - `DB_USERNAME`, default value = `appseed_db_usr`
    - `DB_PASS`, default value = `pass`
- `SOCIAL AUTH` Github (optional)
  - `GITHUB_ID`=YOUR_GITHUB_ID
  - `GITHUB_SECRET`=YOUR_GITHUB_SECRET
  
<br />

## ✅ Set up MySql

**Note:** Make sure your Mysql server is properly installed and accessible. 

> **Step 1** - Create the MySql Database to be used by the app

- `Create a new MySql` database
- `Create a new user` and assign full privilegies (read/write)

<br />

> **Step 2** - Edit the `.env` to match your MySql DB credentials. Make sure `DB_ENGINE` is set to `mysql`.

- `DB_ENGINE`  : `mysql` 
- `DB_NAME`    : default value = `appseed_db`
- `DB_HOST`    : default value = `localhost`
- `DB_PORT`    : default value = `3306`
- `DB_USERNAME`: default value = `appseed_db_usr`
- `DB_PASS`    : default value = `pass`

<br />

Here is a sample:  

```txt
# .env sample

DB_ENGINE=mysql            # Database Driver
DB_NAME=appseed_db         # Database Name
DB_USERNAME=appseed_db_usr # Database User
DB_PASS=STRONG_PASS_HERE   # Password 
DB_HOST=localhost          # Database HOST, default is localhost 
DB_PORT=3306               # MySql port, default = 3306 
```

<br />

## ✅ Manual Build

> - Download the [code](https://appseed.us/product/soft-ui-dashboard-pro/flask/) and unzip the sources (requires a `purchase`). 

```bash
$ unzip flask-soft-ui-dashboard-enh.zip
$ cd flask-soft-ui-dashboard-enh
```

<br />

### 👉 Set Up for `Unix`, `MacOS` 

> Install modules via `VENV`  

```bash
$ virtualenv env
$ source env/bin/activate
$ pip install -r requirements.txt
```

<br />

> Set Up Flask Environment

```bash
$ export FLASK_APP=run.py
```

<br />

> Set Up Database

```bash
# Init migration folder
$ flask db init # to be executed only once         
```

```bash
$ flask db migrate # Generate migration SQL
$ flask db upgrade # Apply changes
```

<br />

> Create super admin 

```bash
$ flask create_admin
```

<br />

> Start the app

```bash
$ flask run
// OR
$ flask run --cert=adhoc # For HTTPS server
```

At this point, the app runs at `http://127.0.0.1:5000/`. 

<br />

### 👉 Set Up for `Windows` 

> Install modules via `VENV` (windows) 

```
$ virtualenv env
$ .\env\Scripts\activate
$ pip3 install -r requirements.txt
```

<br />

> Set Up Flask Environment

```bash
$ # CMD 
$ set FLASK_APP=run.py
$
$ # Powershell
$ $env:FLASK_APP = ".\run.py"
```

<br />

> Start the app

```bash
$ flask run
// OR
$ flask run --cert=adhoc # For HTTPS server
```

At this point, the app runs at `http://127.0.0.1:5000/`. 

<br />

### 👉 Create (ordinary) Users

By default, the app redirects guest users to authenticate. In order to access the private pages, follow this set up: 

- Start the app via `flask run`
- Access the `registration` page and create a new user:
  - `http://127.0.0.1:5000/register`
- Access the `sign in` page and authenticate
  - `http://127.0.0.1:5000/login`

<br />

## ✅ Codebase

The project is coded using blueprints, app factory pattern, dual configuration profile (development and production) and an intuitive structure presented bellow:

```bash
< PROJECT ROOT >
   |
   |-- apps/
   |    |
   |    |-- home/                           # A simple app that serve HTML files
   |    |    |-- routes.py                  # Define app routes
   |    |
   |    |-- authentication/                 # Handles auth routes (login and register)
   |    |    |-- routes.py                  # Define authentication routes  
   |    |    |-- models.py                  # Defines models  
   |    |    |-- forms.py                   # Define auth forms (login and register) 
   |    |
   |    |-- static/
   |    |    |-- <css, JS, images>          # CSS files, Javascripts files
   |    |
   |    |-- templates/                      # Templates used to render pages
   |    |    |-- includes/                  # HTML chunks and components
   |    |    |    |-- navigation.html       # Top menu component
   |    |    |    |-- sidebar.html          # Sidebar component
   |    |    |    |-- footer.html           # App Footer
   |    |    |    |-- scripts.html          # Scripts common to all pages
   |    |    |
   |    |    |-- layouts/                   # Master pages
   |    |    |    |-- base-fullscreen.html  # Used by Authentication pages
   |    |    |    |-- base.html             # Used by common pages
   |    |    |
   |    |    |-- accounts/                  # Authentication pages
   |    |    |    |-- login.html            # Login page
   |    |    |    |-- register.html         # Register page
   |    |    |
   |    |    |-- home/                      # UI Kit Pages
   |    |         |-- index.html            # Index page
   |    |         |-- 404-page.html         # 404 page
   |    |         |-- *.html                # All other pages
   |    |    
   |  config.py                             # Set up the app
   |    __init__.py                         # Initialize the app
   |
   |-- requirements.txt                     # App Dependencies
   |
   |-- .env                                 # Inject Configuration via Environment
   |-- run.py                               # Start the app - WSGI gateway
   |
   |-- ************************************************************************
```

<br />

---
[Soft UI Dashboard PRO Flask](https://appseed.us/product/soft-ui-dashboard-pro/flask/) - Starter provided by **[AppSeed](https://appseed.us)**.
