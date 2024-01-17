# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from datetime import datetime
import os
from flask import render_template, redirect, request, url_for, jsonify
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user
) 

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.email import send_email
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import UserProfile, Users
import re
from apps.authentication.token import confirm_token, generate_confirmation_token
from apps.authentication.util import hash_pass, new_password_should_be_different, verify_pass
from apps.config import Config
from apps.config import Email_config
from apps.helpers import createAccessToken, emailValidate, password_validate, sanitise_fille_name, createFolder, serverImageUrl, uniqueFileName, get_ts
from ftp_server import uploadImageFTP
from werkzeug.utils import secure_filename
from flask import Flask, flash
from messages import Messages
from flask_dance.contrib.github import github
import secrets
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, EqualTo, Length, Regexp
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

message = Messages.message

login_limit = Config.LOGIN_ATTEMPT_LIMIT

# User States
STATUS_SUSPENDED = Config.USERS_STATUS['SUSPENDED']
STATUS_ACTIVE    = Config.USERS_STATUS['ACTIVE'   ]

# Users Roles
ROLE_ADMIN       = Config.USERS_ROLES['ADMIN']
ROLE_USER        = Config.USERS_ROLES['USER']

upload_folder_name = createFolder('media')
app = Flask(__name__)

app.config['uploadFolder'] = upload_folder_name 


@blueprint.route('/')
def route_default():
    return redirect(url_for('authentication_blueprint.login')) 

# Login & Registration
@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """ 
        Login View 
    """
    
    template_name = 'accounts/login.html'
    login_form = LoginForm(request.form)

    if 'login' in request.form:

        # Read form data
        userID   = request.form['username'] # user || email
        password = request.form['password']
        
        valid_email = emailValidate(userID)
                        
        if valid_email == True:
            user = Users.find_by_email(userID)
        else:
            # Locate user
            user = Users.find_by_username(userID)

        # if user not found
        if not user:
            return render_template(template_name,
                                   msg=message['wrong_user_or_password'],
                                   form=login_form)
        
        # Check user is suspended
        if STATUS_SUSPENDED == user.status:
            return render_template(template_name,
                               msg=message['suspended_account_please_contact_support'],
                               form=login_form)            

        if user.failed_logins >= login_limit:
            user.status = STATUS_SUSPENDED
            db.session.commit()
            return render_template(template_name,
                               msg=message['suspended_account_maximum_nb_of_tries_exceeded'],
                               form=login_form)
        
        # Check the password
        if user and not verify_pass(password, user.password):
            user.failed_logins += 1
            db.session.commit()

            return render_template(template_name,
                               msg=message['incorrect_password'],
                               form=login_form)
        login_user(user)
        user.failed_logins = 0
        db.session.commit()
        
        return redirect(url_for('home_blueprint.index'))

    if not current_user.is_authenticated:

        # we might have a redirect from OAuth
        msg = request.args.get('oautherr')

        if msg and 'suspended' in msg:
            msg = message['suspended_account_please_contact_support']

        return render_template(template_name,
                               form=login_form,
                               msg=msg)
    
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    """
        User register view
    """
    # already logged in
    if current_user.is_authenticated:
        return redirect('/')
    
    template_name = 'accounts/register.html'
    create_account_form = CreateAccountForm(request.form)

    if 'register' in request.form:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password_check']
        
        if password != password2:
            return render_template(template_name,
                                   msg=message['pwd_not_match'],
                                   success=False,
                                   form=create_account_form)
        
        # Check usename exists
        user = Users.find_by_username(username)
        if user:
            return render_template(template_name,
                                   msg=message['username_already_registered'],
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.find_by_email(email)
        if user:
            return render_template(template_name,
                                   msg=message['email_already_registered'],
                                   success=False,
                                   form=create_account_form)
            
        valid_pwd = password_validate(password)
        if valid_pwd != True:
            return render_template(template_name,
                                   msg = valid_pwd,
                                   success = False,
                                   form = create_account_form)
        
        user = Users(**request.form)
        user.api_token = createAccessToken()
        user.api_token_ts = get_ts()
        
        user.save()

        # Force logout
        logout_user()

        # send signal for create profile
        user_saved_signals.send({"user_id":user.id, "email": user.email})

        return render_template(template_name,
                               msg = message['account_created_successfully'],
                               success = True,
                               form = create_account_form)

    else:
        return render_template(template_name, form=create_account_form) 


@blueprint.route('/profile', methods=['GET', 'PUT'])
def user_profile():
    """
        Get user profile view
    """
    if request.method =='GET':
       
        template = 'accounts/account-settings.html'
        
        user         = Users.find_by_id(current_user.id)
        user_profile = UserProfile.find_by_user_id(user.id) 
        
        context = { 'id':user.id, 
                    'profile_name':user_profile.full_name,
                    'profile_bio':user_profile.bio, 
                    'profile_address':user_profile.address, 
                    'profile_zipcode':user_profile.zipcode, 
                    'profile_phone':user_profile.phone,
                    'email':user_profile.email, 
                    'profile_website':user_profile.website, 
                    'profile_image':user_profile.image, 
                    'user_profile_id':user_profile.id}
        
        return render_template(template, context=context)

    return redirect(url_for('home_blueprint.index')) 


@blueprint.route('/logout')
def logout():
    """ Logout View """
    logout_user()
    return redirect(url_for('authentication_blueprint.login'))

@blueprint.route('/verify_email', methods=['GET', 'POST'])  
def verify_email():
    """ Verify email view """

    if request.method == 'POST':
        email = request.form['email']
        user = Users.query.filter_by(username=current_user.username).one()
        if user:
            if user.email != email and user.email is not None:
                flash(message['email_not_found'])
            else:
                token = generate_confirmation_token(email)
                
                confirm_url = url_for('authentication_blueprint.confirm_email', token=token, _external=True)
                html = render_template('accounts/activate.html', confirm_url=confirm_url)
                subject = "Please confirm your email"
                # send email
                send_email(email, subject, html)
                
                flash(message['email_has_been_sent_via_email'])
   
    return render_template('home/pages-auth-verify-email.html')


@blueprint.route('/confirm/<token>')
def confirm_email(token):
    """ confirm email with token """
    try:
        email = confirm_token(token)
    except:
        return message['link_is_invalid_or_has_expired']

    user = Users.query.filter_by(username=current_user.username).first_or_404()

    if user.verified_email == 1:
        return message['account_already_confirmed']
    else:
        user.verified_email = 1
        user.email = email
        user.save()
        profile = UserProfile.find_by_user_id(user.id)
        profile.email = email
        profile.save()

    return redirect(url_for('home_blueprint.index'))

@blueprint.route('/change_password', methods=['POST'])    
def change_password():
    """Change an existing user's password."""
    
    data          = request.form
    new_password  = data.get('new_password')
    new_password2 = data.get('new_password2')

    user = Users.find_by_username(username=current_user.username)

    if not user:
        return jsonify({'error':message['user_not_found']}), 404

    # check password match or not 
    if new_password != new_password2:
            return jsonify({'error':message['pwd_not_match']}), 404

    # Save the new password
    user.password = hash_pass(new_password)
    user.save()

    return jsonify({'message':message['password_has_been_updated']}), 200

#.................#forget pass.............................####################


from wtforms import StringField, PasswordField, SubmitField, FileField, SelectField, BooleanField
from wtforms.validators import DataRequired, EqualTo, Email  # Ajoutez Email ici
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from flask_wtf import FlaskForm
from flask import Flask, render_template, request, flash, redirect, session, url_for, send_from_directory, send_file
from flask_mail import Mail, Message
from smtplib import SMTPConnectError


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = Email_config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = Email_config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = Email_config.MAIL_DEFAULT_SENDER

mail = Mail(app)

class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Demander la réinitialisation du mot de passe')


class ResetPasswordForm(FlaskForm):
    new_password = PasswordField(
        'Nouveau mot de passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(
    ), EqualTo('new_password', message= message['pwd_not_match'])])
    submit = SubmitField('Réinitialiser le mot de passe')

mail = Mail(app)

def send_password_reset_email(user_form, token):
    user_email = user_form.email.data  # Utiliser le champ e-mail du formulaire

    email_content = [
        "Pour réinitialiser votre mot de passe, veuillez suivre le lien suivant :",
        f"{url_for('authentication_blueprint.reset_password', token=token, _external=True)}",
        "Si vous n'avez pas demandé à réinitialiser votre mot de passe, veuillez ignorer cet e-mail.",
        "Ceci est un email régéner automatiquement merci.",
        "Ce lien est valide 1 heure"
    ]

    msg = Message('Réinitialisation de votre mot de passe',
                  sender=app.config['MAIL_USERNAME'], recipients=[user_email])
    msg.body = "\n".join(email_content)
    mail.send(msg)


@blueprint.route('/password_reset_request', methods=['GET', 'POST'])
def password_reset_request():
    form = PasswordResetRequestForm()
    success_message = None
    error_message = None

    try:
        if form.validate_on_submit():
            email = form.email.data
            user = Users.query.filter_by(email=email).first()

            if user:
                # Générer un jeton unique
                token = secrets.token_urlsafe(20)

                # Définir la date d'expiration du jeton (par exemple, 1 heure à partir de maintenant)
                expiration_date = datetime.now() + timedelta(hours=1)

                # Stocker le jeton dans la base de données
                user.reset_token = token
                user.reset_token_expiration = expiration_date
                db.session.commit()

                # Envoyer un e-mail à l'utilisateur avec un lien contenant le jeton
                send_password_reset_email(form, token)  # Passez le formulaire

                success_message = message['email_ok_message']
                

            else:
                error_message = message['erreur_connexion_smtp']

    except SMTPConnectError as e:
        # Gérer l'erreur de connexion SMTP ici
        error_message = message['serveur_error']

    return render_template('accounts/authentication-reset-illustration.html', form=form,
                           success_message=success_message, error_message=error_message)


class ResetPasswordForm(FlaskForm):
    new_password = PasswordField(
        'Nouveau mot de passe',
        validators=[
            InputRequired(message='Le champ est requis'),
            Length(min=6, message=message['caractere_mot_de_passe']),
            Regexp('^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()_+{}|:"<>?])',
                   message= message['lettre_caractere_mot_de_passe'])
        ]
    )

    confirm_password = PasswordField(
        'Confirmer le mot de passe',
        validators=[
            InputRequired(message='Le champ est requis'),
            EqualTo('new_password', message= message['pwd_not_match'])
        ]
    )

    submit = SubmitField('Réinitialiser le mot de passe')
    
@blueprint.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = Users.query.filter_by(reset_token=token).first()

    if user and user.reset_token_expiration > datetime.now():
        form = ResetPasswordForm()

        if form.validate_on_submit():
            new_password = form.new_password.data

            # Mise à jour du mot de passe de l'utilisateur
            user.password = hash_pass(new_password)
            user.reset_token = None
            user.reset_token_expiration = None
            db.session.commit()

            success_message = message['password_has_been_updated']
            return render_template('accounts/reset_password.html', form=form, token=token, success_message=success_message)

        return render_template('accounts/reset_password.html', form=form, token=token)

    else:
        error_message = message['lien_invalide']
        return redirect(url_for('authentication_blueprint.login', error_message=error_message))

#.................#forget pass.............................####################

# Errors
@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403

@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404

@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500
