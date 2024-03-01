
from werkzeug.security import generate_password_hash, check_password_hash
from smtplib import SMTPConnectError
from flask_mail import Mail, Message
from flask import Flask, render_template, request, flash, redirect, session, url_for, send_from_directory, send_file, current_app
from flask import jsonify, g
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import DataRequired, EqualTo, Email  # Ajoutez Email ici
from wtforms import StringField, PasswordField, SubmitField, FileField, SelectField, BooleanField
from datetime import datetime
from flask import render_template, redirect, request, url_for, jsonify, render_template_string
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
    user_logged_in
)
from flask_mail import Message

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.email import send_email
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import UserProfile, Users, ImageUploadVisible, RapportGenere, ImageUploadInvisible
import re
from apps.authentication.signals import user_saved_signals, delete_user_signals
from apps.authentication.token import confirm_token, generate_confirmation_token
from apps.authentication.util import hash_pass, new_password_should_be_different, verify_pass
from apps.config import Config
from apps.config import Email_config
from apps.helpers import createAccessToken, emailValidate, password_validate, sanitise_fille_name, createFolder, serverImageUrl, uniqueFileName, get_ts
from werkzeug.utils import secure_filename
from messages import Messages
import secrets
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, EqualTo, Length, Regexp
import ssl
from werkzeug.utils import secure_filename
from PIL import Image
from base64 import b64encode
from io import BytesIO
import math
import piexif
from PIL.ExifTags import TAGS, GPSTAGS
import cv2
import base64

# classification d'images chargement du model
import os
import uuid
from werkzeug.utils import secure_filename
from io import BytesIO
import shutil
import numpy as np


from fractions import Fraction
from flask import Markup
import logging
import pytesseract
from urllib.parse import unquote
import locale
import math
import traceback

from apps.config import Email_config
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import mobilenet_v2  # Import de MobileNetV2

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# classification d'images chargement du model

ssl._create_default_https_context = ssl._create_unverified_context

message = Messages.message

login_limit = Config.LOGIN_ATTEMPT_LIMIT

# User States
STATUS_SUSPENDED = Config.USERS_STATUS['SUSPENDED']
STATUS_ACTIVE = Config.USERS_STATUS['ACTIVE']

# Users Roles
ROLE_ADMIN = Config.USERS_ROLES['ADMIN']
ROLE_USER = Config.USERS_ROLES['USER']

upload_folder_name = createFolder('media')
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = upload_folder_name
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    days=365)  # adjust as needed
app.config['SESSION_PROTECTION'] = 'strong'

# Configurations Flask-Mail
app.config['MAIL_SERVER'] = Email_config.MAIL_SERVER
app.config['MAIL_PORT'] = Email_config.MAIL_PORT
app.config['MAIL_USE_TLS'] = Email_config.MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = Email_config.MAIL_USE_SSL
app.config['MAIL_USERNAME'] = Email_config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = Email_config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = Email_config.MAIL_DEFAULT_SENDER


mail = Mail(app)

@blueprint.route('/')
def route_default():
    return redirect(url_for('authentication_blueprint.login'))

# Login & Registration


@blueprint.route('/index')
@login_required
def index():
    return render_template('index.html')


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
        userID = request.form['username']  # user || email
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

        return redirect(url_for('home_blueprint.acceuil'))

    if not current_user.is_authenticated:

        # we might have a redirect from OAuth
        msg = request.args.get('oautherr')

        if msg and 'suspended' in msg:
            msg = message['suspended_account_please_contact_support']

        return render_template(template_name,
                               form=login_form,
                               msg=msg)

    return redirect(url_for('home_blueprint.acceuil'))


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
                                   msg=valid_pwd,
                                   success=False,
                                   form=create_account_form)

        user = Users(**request.form)
        user.api_token = createAccessToken()
        user.api_token_ts = get_ts()

        user.save()

        # Force logout
        logout_user()

        # send signal for create profile
        user_saved_signals.send({"user_id": user.id, "email": user.email})

        return render_template(template_name,
                               msg=message['account_created_successfully'],
                               success=True,
                               form=create_account_form)

    else:
        return render_template(template_name, form=create_account_form)


@blueprint.route('/profile', methods=['GET', 'PUT'])
@login_required
def user_profile():
    """
    Get user profile view
    """
    if request.method == 'GET':

        template = 'accounts/account-settings.html'

        user = Users.find_by_id(current_user.id)
        user_profile = UserProfile.find_by_user_id(user.id)

        context = {
            'id': user.id,
            'profile_name': user_profile.full_name,
            'profile_bio': user_profile.bio,
            'profile_address': user_profile.address,
            'profile_zipcode': user_profile.zipcode,
            'profile_phone': user_profile.phone,
            'email': user_profile.email,
            'profile_service': user_profile.service,
            'user_profile_id': user_profile.id

        }

        return render_template(template, context=context)

    return redirect(url_for('authentication_blueprint.index'))


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# ///////////////////////////...............Route pour charger la phtoto de profile actuellement elle ne focntionne pas car l'image ne s'affiche pas sur toutes les pages je sais pas pourquoi, l'image est au format binaire////////
@blueprint.route('/photo_upload', methods=['GET', 'POST'])
@login_required
def photo_upload():
    if request.method == 'POST':
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                image_binary = base64.b64encode(image.read())
                user_profile = UserProfile.query.filter_by(
                    user=current_user.id).first()
                user_profile.image = image_binary
                db.session.commit()

                # Update the image_url variable after updating the user_profile.image
                image_url = user_profile.image

    user_profile = UserProfile.query.filter_by(user=current_user.id).first()
<<<<<<< HEAD
    return render_template('home/index.html', user_profile=user_profile)
=======
    return render_template('accounts/profile.html', user_profile=user_profile)
<<<<<<< HEAD
>>>>>>> Prince-Gildas
#///////////////////////////...............Route pour charger la phtoto de profile actuellement elle ne focntionne pas car l'image ne s'affiche pas sur toutes les pages je sais pas pourquoi, l'image est au format binaire////////
=======
# ///////////////////////////...............Route pour charger la phtoto de profile actuellement elle ne focntionne pas car l'image ne s'affiche pas sur toutes les pages je sais pas pourquoi, l'image est au format binaire////////

>>>>>>> Prince-Gildas

@blueprint.route('/user_list', methods=['GET'])
def user_list():
    """
        Get all users list view
    """

    if current_user.role != ROLE_ADMIN:
        return redirect(url_for('authentication_blueprint.user_profile'))

    if request.method == 'GET':
        template = 'accounts/users-reports.html'
        users = Users.query.all()

        user_list = []
        if users is not None:
            for user in users:
                for data in UserProfile.query.filter_by(user=user.id):
                    user_list.append(data)

        context = {'users': user_list}

        return render_template(template, context=context)

    return redirect(url_for('authentication_blueprint.index'))

@user_logged_in.connect
def track_login(sender, user, **extra):
    user.last_login_at = datetime.utcnow()
    db.session.commit()

@blueprint.route('/edit_user', methods=['PUT'])
def edit_user():
    """
        1.Get User by id(Get user view)
        2.Update user(update user view)
    Returns:
        _type_: json data
    """
    if request.method == 'GET':

        user = UserProfile.find_by_id(request.args.get('user_id'))

        # if check user none or not
        if user:

            context = {'id': user.id, 'full_name': user.full_name, 'bio': user.bio,
                       'address': user.address, 'zipcode': user.zipcode, 'phone': user.phone,
                       'email': user.email, 'service': user.service, 'image': user.image,
                       'user_id': user.user_id.id}

            return jsonify(context), 200

        else:
            return jsonify({'error': message['record_not_found']}), 404

    if request.method == 'PUT':

        data = request.form
        image = request.files.get('image')

        FTP_error = False

        profile_obj = UserProfile.find_by_id(data.get('user_id'))
        if profile_obj is not None:
            # if check image none or not
            if image:
                filename = sanitise_fille_name(secure_filename(image.filename))

                # unque file name
                unique_name = uniqueFileName(filename)

                # if check folder
                if upload_folder_name in os.listdir():
                    image.save(os.path.join(
                        app.config['uploadFolder'], unique_name))

                # if check image
                if profile_obj.image is not None:

                    # save to FTP server replace exists image
                    if uploadImageFTP(unique_name, profile_obj.image):
                        profile_obj.image = serverImageUrl(unique_name)
                    else:
                        FTP_error = True
            if data.get('email') != '':
                try:
                    profile_obj.full_name = data.get('full_name')
                    profile_obj.bio = data.get('bio')
                    profile_obj.address = data.get('address')
                    profile_obj.zipcode = data.get('zipcode')
                    profile_obj.phone = data.get('phone')
                    profile_obj.email = data.get('email')
                    profile_obj.service = data.get('service')

                    profile_obj.save()
                except:
                    return jsonify({'error': message['email_already_registered']}), 404

                user = Users.find_by_id(data.get('user_id'))
                user.email = data.get('email')
                user.save()
            else:
                profile_obj.full_name = data.get('full_name')
                profile_obj.bio = data.get('bio')
                profile_obj.address = data.get('address')
                profile_obj.zipcode = data.get('zipcode')
                profile_obj.phone = data.get('phone')
                profile_obj.service = data.get('service')

                profile_obj.save()

        aMsg = message['user_updated_successfully']

        if FTP_error:
            aMsg += ' (FTP Upload Err)'

        return jsonify({'message': aMsg}), 200

    else:
        return jsonify({'error': message['record_not_found']}), 404

@blueprint.route('/update_role', methods=['PUT'])
def update_role():
    if request.method == 'PUT':
        user = Users.find_by_id(request.form.get('user_id'))

        # Check if the user exists
        if user:
            # Update the user role (you may want to add more validation logic)
            if user.role == ROLE_ADMIN:
                user.role = ROLE_USER
            else:
                user.role = ROLE_ADMIN

            # Save the updated user role
            user.save()

            context = {'new_role': user.role}
            return jsonify(context), 200
        else:
            return jsonify({'error': message['record_not_found']}), 404

@blueprint.route('/update_status', methods=['PUT'])
def update_status():
    """Update status view

    Returns:
        _type_: json
    """
    if request.method == 'PUT':

        user = Users.find_by_id(request.form.get('user_id'))

        # if check user none or not
        if user:

            # if check status none or not
            if user.status:
                if user.status == STATUS_ACTIVE:
                    user.status = STATUS_SUSPENDED
                else:
                    user.status = STATUS_ACTIVE

                # save user state
                user.save()

            context = {'message': message['successfully_updated']}

            return jsonify(context), 200

        else:
            return jsonify({'error': message['record_not_found']}), 404


@blueprint.route('/delete_user', methods=['DELETE'])
def delete_user():
    """Delete user view

    Returns:
        _type_: json
    """
    if request.method == 'DELETE':
        user = Users.find_by_id(request.form.get('user_id'))
        if user:
            # send signal for create profile
            delete_user_signals.send({"user_id": user.id})
            user.delete_from_db()
            return jsonify({'message': message["deleted_successfully"]}), 200


@blueprint.route('/logout')
@login_required
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

                confirm_url = url_for(
                    'authentication_blueprint.confirm_email', token=token, _external=True)
                html = render_template(
                    'accounts/activate.html', confirm_url=confirm_url)
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

    return redirect(url_for('authentication_blueprint.index'))


@blueprint.route('/change_password', methods=['POST'])
def change_password():
    """Change an existing user's password."""

    data = request.form
    new_password = data.get('new_password')
    new_password2 = data.get('new_password2')

    user = Users.find_by_username(username=current_user.username)

    if not user:
        return jsonify({'error': message['user_not_found']}), 404

    # check password match or not
    if new_password != new_password2:
        return jsonify({'error': message['pwd_not_match']}), 404

    # Save the new password
    user.password = hash_pass(new_password)
    user.save()

    return jsonify({'message': message['password_has_been_updated']}), 200

# .................#forget pass.............................####################


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
    ), EqualTo('new_password', message=message['pwd_not_match'])])
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

    return render_template('accounts/password_reset_request.html', form=form,
                           success_message=success_message, error_message=error_message)


class ResetPasswordForm(FlaskForm):
    new_password = PasswordField(
        'Nouveau mot de passe',
        validators=[
            InputRequired(message='Le champ est requis'),
            Length(min=6, message=message['caractere_mot_de_passe']),
            Regexp('^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()_+{}|:"<>?])',
                   message=message['lettre_caractere_mot_de_passe'])
        ]
    )

    confirm_password = PasswordField(
        'Confirmer le mot de passe',
        validators=[
            InputRequired(message='Le champ est requis'),
            EqualTo('new_password', message=message['pwd_not_match'])
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


# .................#forget pass.............................####################


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


# //////////////////////////UPLAD////////////

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ................IMAAGE//////VISIBLE//////////


def get_decimal_from_dms(dms, ref):
    degrees, minutes, seconds = dms
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal


def extract_gps_info(img_path):
    try:
        img = Image.open(img_path)
        exif_data = img._getexif()

        if not exif_data:
            return None

        # Get the GPSInfo dictionary
        gps_info = exif_data.get(34853)
        if not gps_info:
            return None

        # Parse GPS coordinates
        gps_latitude = gps_info.get(2)
        gps_latitude_ref = gps_info.get(1)
        gps_longitude = gps_info.get(4)
        gps_longitude_ref = gps_info.get(3)

        if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
            latitude = get_decimal_from_dms(gps_latitude, gps_latitude_ref)
            longitude = get_decimal_from_dms(gps_longitude, gps_longitude_ref)

            # Ensure longitude is negative for West Africa
            if longitude > 0:
                longitude = -longitude

            return {'latitude': latitude, 'longitude': longitude}
        else:
            return None
    except Exception as e:
        print(f"Error extracting GPS info: {e}")
        return None
    # Ouvrir l'image avec PIL
    img = Image.open(img_path)

    # Vérifier si l'image a des métadonnées EXIF
    exif_data = img._getexif()
    if exif_data is not None:
        # Recherche des informations GPS dans les métadonnées EXIF
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == 'GPSInfo':
                for t, v in value.items():
                    sub_tag_name = GPSTAGS.get(t, t)
                    # Convertir les coordonnées GPS en décimales
                    value[t] = v[0] / v[1]
                    if sub_tag_name == 'GPSLongitudeRef' and v == 'W':
                        # Inverser la longitude si elle est à l'ouest
                        value[t] = -value[t]

                return {'latitude': value.get(2), 'longitude': value.get(4)}

    return None


@login_required
@blueprint.route("/upload_page")
def upload_page():
    return render_template('rapport/traitement_visible.html')

# Chargement du modèle pré-entraîné


def load_model_visible(num_classes):
    model = mobilenet_v2(pretrained=True)  # Utiliser MobileNetV2
    num_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_features, num_classes)
    model.features[0][0] = nn.Conv2d(3, 32, kernel_size=(3, 3), stride=(
        1, 1), padding=(1, 1), bias=False)  # Adapter l'entrée à 3 canaux
    model._dropout = nn.Dropout(0.5)  # Choisir la valeur de dropout souhaitée

    # Chargement des poids du modèle
    # Assurez-vous d'avoir le bon nom de fichier
    if torch.cuda.is_available():
        model.load_state_dict(torch.load(
            './apps/IA/model/model_mobilenetv2_normal.pt'))
    else:
        model.load_state_dict(torch.load(
            './apps/IA/model/model_mobilenetv2_normal.pt', map_location=torch.device('cpu')))
    return model.to(device)


# Transformation des images pour la classification
def prepare_image_from_path_visible(file_path):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(30),
        transforms.ColorJitter(
            brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[
                             0.229, 0.224, 0.225])
    ])
    image = Image.open(file_path).convert('RGB')
    img_tensor = transform(image).unsqueeze(0).to(device)
    return img_tensor


@blueprint.route('/results_page/<rapport_genere_id>', methods=['GET'])
def results_page(rapport_genere_id):
    # Récupérer les images associées au rapport généré
    images = ImageUploadVisible.query.filter_by(
        rapport_genere_id=rapport_genere_id).all()
    return render_template('rapport/traitement_visible.html', images=images)


# Mettez à jour la route pour traiter les images
@login_required
@blueprint.route('/upload_and_traitement_visible', methods=['POST'])
def upload_and_traitement_visible():
    try:
        # Assurez-vous de récupérer le champ "file" comme une liste
        files = request.files.getlist('file')

        # Créer un identifiant unique pour le sous-répertoire
        user_subdirectory = str(uuid.uuid4())

        # Chemin du sous-répertoire dans le répertoire UPLOAD_FOLDER
        user_upload_path = os.path.join(
            app.config['UPLOAD_FOLDER'], user_subdirectory)

        # Créer le sous-répertoire
        os.makedirs(user_upload_path)

        class_labels_path = './apps/IA/label/class_labels_normalv2.txt'
        with open(class_labels_path, 'r') as f:
            class_labels = f.read().splitlines()
        num_classes = len(class_labels)

        # Maintenant que num_classes est défini, vous pouvez appeler load_model
        model = load_model_visible(num_classes)

        # Ajout de la déclaration pour threshold
        threshold = 0.3  # Vous pouvez ajuster cette valeur en fonction de vos besoins

        rapport_genere_id = None  # Déclarer rapport_genere_id à l'extérieur de la boucle
        
        for file in files:
            try:
                # Le traitement pour chaque fichier est similaire à votre code existant
                filename = secure_filename(file.filename)

                # Sauvegarder le fichier dans le sous-répertoire
                file_path = os.path.join(user_upload_path, filename)
                file.save(file_path)

                img_tensor = prepare_image_from_path_visible(file_path)
                model.eval()
                with torch.no_grad():
                    predictions = model(img_tensor)
                    probabilities = torch.softmax(predictions, dim=1)[0]
                    max_prob, predicted_class = torch.max(probabilities, dim=0)
                    detected_defect = class_labels[predicted_class.item()]
                    defect_prob = max_prob.item() * 100

                    # Extraire les coordonnées GPS si disponibles
                    gps_info = extract_gps_info(file_path)

                    # Compresser l'image
                    compressed_data = compress_image(file_path)

                    # Obtenir la taille de l'image originale
                    original_size = os.path.getsize(file_path)

                    # Créer une nouvelle instance de ImageUploadVisible avec les résultats
                    new_image = ImageUploadVisible(
                        filename=filename,
                        data=compressed_data,  # Stocker les données compressées
                        # Stocker la taille originale
                        original_size=convert_size(original_size),
                        # Stocker la taille compressée
                        compressed_size=convert_size(len(compressed_data)),
                        nom_operateur=current_user.email,
                        feeder=request.cookies.get('feeder'),
                        troncon=request.cookies.get('troncon'),
                        zone=request.cookies.get('zone'),
                        groupement_troncon=request.cookies.get(
                            'groupementTroncon'),
                        type_image=request.cookies.get('selectedOption'),
                        latitude=gps_info['latitude'] if gps_info else None,
                        longitude=gps_info['longitude'] if gps_info else None,
                        type_defaut=detected_defect if defect_prob > threshold else None
                    )

                    # Associer l'image au rapport généré
                    if rapport_genere_id is None:
                        rapport_genere_id = request.cookies.get(
                            'rapportGenereId')
                    new_image.rapport_genere_id = rapport_genere_id

                    # Ajouter à la base de données (pas besoin de commit ici)
                    db.session.add(new_image)
                    
                    

            except Exception as e:
                logging.error(f"Error processing image {filename}: {e}")

        # Ajouter le commit ici, après avoir traité tous les fichiers
        db.session.commit()

        # Supprimer le sous-répertoire après le traitement des images
        shutil.rmtree(user_upload_path)

        # Rendre le template avec le message de succès et les résultats
        rapport_genere_id = request.cookies.get('rapportGenereId')
              # Envoyer un e-mail à l'utilisateur
        user_email = current_user.email
        subject_user = "Traitement d'images en cours"
        message_user = "Le message: les images normales chargées sont soumises à une vérification préalable. Néanmoins, vous pouvez déjà consulter les statistiques ou générer des rapports. Pour un résultat optimal, il est préférable d'attendre un délai de 30 minutes à 1 heure pour de meilleurs résultats.Nous vous recontacterons dans les plus brefs délais"

        send_email(user_email, subject_user, message_user)

        # Envoyer un e-mail à tous les admins (rôle == 1)
        if current_user.role == 1:
            send_email_to_admins()
        return redirect(url_for('authentication_blueprint.results_page', rapport_genere_id=rapport_genere_id))


    except Exception as main_exception:
        error_message = f"Error in upload_and_traitement_visible route: {main_exception}"
        logging.error(error_message)
        traceback.print_exc()  # Imprime la trace complète de l'exception

        # Incluez des informations supplémentaires dans le message d'erreur
        # Pour identifier plus facilement la source de l'erreur
        error_message += f"\nAdditional Info: {str(main_exception)}"

        # Relevez à nouveau l'exception pour la propager correctement
        raise RuntimeError(error_message)

#envoyer un email au admin #

# Fonction pour envoyer un e-mail
# Fonction pour envoyer un e-mail
def send_email(to, subject, message, html=None):
    msg = Message(subject, recipients=[to])
    msg.body = message
    if html:
        msg.html = html
    msg.sender = app.config['MAIL_DEFAULT_SENDER']  # Ajout de l'expéditeur
    mail.send(msg)


# Fonction pour envoyer un e-mail à tous les admins
def send_email_to_admins():
    admins = Users.query.filter_by(role=1).all()
    for admin in admins:
        admin_email = admin.email
        subject_admin = f"Rapport généré par {current_user.username}"
        message_admin = f"L'utilisateur {current_user.username} vient de générer un rapport. Merci de vérifier cela et de le corriger, puis informer le client."
        html_admin = render_template('rapport/email_template.html', username=current_user.username, rapport_genere_id=request.cookies.get('rapportGenereId'), troncon=request.cookies.get('troncon'), feeder=request.cookies.get('feeder'), type_image=request.cookies.get('selectedOption'))

        send_email(admin_email, subject_admin, message_admin, html_admin)



#envoyer un email au admin #


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

# Mettez à jour la fonction compress_image pour retourner les données compressées sans sauvegarder sur le disque


def compress_image(file_path, quality=60):
    try:
        # Ouvrir l'image avec Pillow à partir du chemin du fichier
        img = Image.open(file_path)

        # Convertir l'image en mode RGB
        img = img.convert('RGB')

        # Vérifier la présence de données EXIF
        exif_bytes = img.info.get('exif', b'')

        # Si des données EXIF sont présentes, réduire la qualité en préservant les données EXIF
        if exif_bytes:
            output_buffer = BytesIO()
            img.save(output_buffer, 'JPEG', quality=quality, exif=exif_bytes)
        else:
            # Si aucune donnée EXIF n'est présente, réduire la qualité sans conserver les données EXIF
            output_buffer = BytesIO()
            img.save(output_buffer, 'JPEG', quality=quality)

        # Lire les données de l'image compressée
        compressed_data = b64encode(output_buffer.getvalue()).decode('utf-8')

        return compressed_data
    except Exception as e:
        print(f"Error compressing image: {e}")
        print(traceback.format_exc())  # Imprime la trace complète de l'erreur
        return None


# ................IMAAGE//////VISIBLE//////////


# §§§§§§§§§§§§§§§§§§IMAGE INVISIBLE§§§§§§§§§§§§§§§§§


try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except Exception as e:
    print("Error can't find tesseract:", e)


@login_required
@blueprint.route("/upload_page_invisible")
def upload_page_invisible():
    return render_template('rapport/traitement_invisible.html')


@blueprint.route('/results_page_invisible/<rapport_genere_id>', methods=['GET'])
def results_page_invisible(rapport_genere_id):
    # Récupérer les images associées au rapport généré
    images = ImageUploadInvisible.query.filter_by(
        rapport_genere_id=rapport_genere_id).all()
    return render_template('rapport/traitement_invisible.html', images=images)

# Chargement du modèle pré-entraîné


def load_model(num_classes):
    model = mobilenet_v2(pretrained=True)  # Utiliser MobileNetV2
    num_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_features, num_classes)
    model.features[0][0] = nn.Conv2d(3, 32, kernel_size=(3, 3), stride=(
        1, 1), padding=(1, 1), bias=False)  # Adapter l'entrée à 3 canaux
    model._dropout = nn.Dropout(0.5)  # Choisir la valeur de dropout souhaitée

    # Chargement des poids du modèle
    # Assurez-vous d'avoir le bon nom de fichier
    if torch.cuda.is_available():
        model.load_state_dict(torch.load(
            './apps/IA/model/model_mobilenetv2_thermo.pt'))
    else:
        model.load_state_dict(torch.load(
            './apps/IA/model/model_mobilenetv2_thermo.pt', map_location=torch.device('cpu')))
    return model.to(device)


# Transformation des images pour la classification
def prepare_image_from_path(file_path):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(30),
        transforms.ColorJitter(
            brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[
                             0.229, 0.224, 0.225])
    ])
    image = Image.open(file_path).convert('RGB')
    img_tensor = transform(image).unsqueeze(0).to(device)
    return img_tensor


@blueprint.route('/upload_and_traitement_invisible', methods=['POST'])
@login_required
def upload_and_traitement_invisible():
    try:
        files = request.files.getlist('file')
        user_subdirectory = str(uuid.uuid4())
        user_upload_path = os.path.join(
            app.config['UPLOAD_FOLDER'], user_subdirectory)
        os.makedirs(user_upload_path)

        class_labels_path = './apps/IA/label/class_label_mobilenetv2_thermo.txt'
        with open(class_labels_path, 'r') as f:
            class_labels = f.read().splitlines()
        num_classes = len(class_labels)

        # Maintenant que num_classes est défini, vous pouvez appeler load_model
        model = load_model(num_classes)

        threshold = 0.4

        rapport_genere_id = None

        for file in files:
            try:
                filename = secure_filename(file.filename)
                file_path = os.path.join(user_upload_path, filename)
                file.save(file_path)

                img_tensor = prepare_image_from_path(file_path)
                model.eval()
                with torch.no_grad():
                    predictions = model(img_tensor)
                    probabilities = torch.softmax(predictions, dim=1)[0]
                    max_prob, predicted_class = torch.max(probabilities, dim=0)
                    detected_defect = class_labels[predicted_class.item()]
                    defect_prob = max_prob.item() * 100

                    # Extract OCR data
                    nom_image, coordonnee, temperature, latitude, longitude = extract_data_for_image(
                        file_path)

                    # Compress the image
                    compressed_data = compress_image(file_path)

                    # Get the size of the original image
                    original_size = os.path.getsize(file_path)

                    # Create a new instance of ImageUploadInvisible with the results
                    new_image = ImageUploadInvisible(
                        filename=filename,
                        data=compressed_data,
                        original_size=convert_size(original_size),
                        compressed_size=convert_size(len(compressed_data)),
                        nom_operateur=current_user.email,
                        feeder=request.cookies.get('feeder'),
                        troncon=request.cookies.get('troncon'),
                        zone=request.cookies.get('zone'),
                        groupement_troncon=request.cookies.get(
                            'groupementTroncon'),
                        type_image=request.cookies.get('selectedOption'),
                        latitude=latitude,
                        longitude=longitude,
                        type_defaut=detected_defect if defect_prob > threshold else None,
                        temperature=temperature,

                    )

                    if rapport_genere_id is None:
                        rapport_genere_id = request.cookies.get(
                            'rapportGenereId')
                    new_image.rapport_genere_id = rapport_genere_id

                    db.session.add(new_image)

            except Exception as e:
                logging.error(f"Error processing image {filename}: {e}")

        db.session.commit()
        shutil.rmtree(user_upload_path)

        rapport_genere_id = request.cookies.get('rapportGenereId')
                # Rendre le template avec le message de succès et les résultats
        rapport_genere_id = request.cookies.get('rapportGenereId')
              # Envoyer un e-mail à l'utilisateur
        user_email = current_user.email
        subject_user = "Traitement d'images en cours"
        message_user = " Les images Thermiques chargées sont soumises à une vérification Plus poussée, car certains détails sur l'images ne peuvent etre traités automatiquement.Seuls les images autorisées seront visible sur la page statistique,mocamisation,et Inspections Invisibles Néanmoins. Pour un résultat optimal, il est préférable d'attendre un délai de 30 minutes à 2 heure pour de meilleurs résultats.Nous vous recontacterons dans les plus brefs délais"

        send_email(user_email, subject_user, message_user)

        # Envoyer un e-mail à tous les admins (rôle == 1)
        if current_user.role == 1:
            send_email_to_admins()
        return redirect(url_for('authentication_blueprint.results_page_invisible', rapport_genere_id=rapport_genere_id))

    except Exception as main_exception:
        error_message = f"Error in upload_and_traitement_visible route: {main_exception}"
        logging.error(error_message)
        traceback.print_exc()
        error_message += f"\nAdditional Info: {str(main_exception)}"
        raise RuntimeError(error_message)


def apply_threshold(image, threshold_value):
    _, thresholded = cv2.threshold(
        image, threshold_value, 255, cv2.THRESH_BINARY)
    return thresholded


def remove_lines(image):
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (24, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 24))
    horizontal_lines = cv2.morphologyEx(
        image, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    vertical_lines = cv2.morphologyEx(
        image, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    lines = cv2.addWeighted(horizontal_lines, 1, vertical_lines, 1, 0)
    return cv2.addWeighted(image, 1, lines, -1, 0)


def extract_data_for_image(file_path):
    try:
        image = cv2.imread(file_path)
        if image.shape[0] > 750 or image.shape[1] > 1624:
            scale_factor = min(750 / image.shape[0], 1624 / image.shape[1])
            image = cv2.resize(image, (0, 0), fx=scale_factor, fy=scale_factor)
        # Coordinates extraction
        x, y, w, h = 440, 690, 305, 38
        crop_img = image[y:y + h, x:x + w]
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        coordonnée = pytesseract.image_to_string(gray)  # coordonnée
        pattern = r"[-]?\d+[.]\d+,\s*[-]?\d+[.]\d+"
        matches = re.findall(pattern, coordonnée)
        coordinates = matches[0].split(',') if len(matches) > 0 else ['', '']
        # Temperature extraction
        roi = (660, 550, 460, 37)
        x, y, w, h = roi
        if x + w > image.shape[1]:
            w = image.shape[1] - x
        if y + h > image.shape[0]:
            h = image.shape[0] - y
        roi_img = image[y:y + h, x:x + w]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        température = pytesseract.image_to_string(gray)  # température
        nom_image = os.path.basename(file_path).split('.')[0]
        return (nom_image, coordonnée, température, coordinates[1], coordinates[0])
    except Exception as e:
        logging.error(
            'Erreur lors du traitement de l\'image {}: {}'.format(file_path, str(e)))
        return ('', '', '', '', '')

# §§§§§§§§§§§§§§§§§§IMAGE INVISIBLE§§§§§§§§§§§§§§§§§
