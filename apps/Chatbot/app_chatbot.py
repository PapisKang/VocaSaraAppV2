# chatbot_routes.py

from flask import Blueprint, request, jsonify, render_template
import uuid
import secrets
from chatbot import get_response
from flask_limiter import Limiter
import logging
from flask_sqlalchemy import SQLAlchemy

chatbot_blueprint = Blueprint('chatbot', __name__)
db = SQLAlchemy()

# Define your model for the remember table
class Remember(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(255))
    phrase = db.Column(db.Text)

# Configuration du logging
logging.basicConfig(filename='./log/crash.log', level=logging.ERROR)

# Configuration du logging
access_logger = logging.getLogger('access')
access_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('./log/access.log')
access_logger.addHandler(file_handler)

limiter = Limiter(chatbot_blueprint, default_limits=["200 per day", "100 per hour"])

def generate_secret_key():
    return secrets.token_urlsafe()

@chatbot_blueprint.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

# Ajouter un log lorsqu'un utilisateur se connecte
@chatbot_blueprint.before_request
def log_request():
    access_logger.info('Accès à l\'URL : %s', request.url)

def generate_session_id():
    return str(uuid.uuid4())

# Fonction pour récupérer l'identifiant de session et l'identifiant de l'utilisateur
def get_user_ids():
    session_id = request.cookies.get('session_id')
    user_id = request.cookies.get('user_id')
    if not session_id:
        session_id = generate_session_id()
    if not user_id:
        user_id = generate_session_id()
    return session_id, user_id

@chatbot_blueprint.route('/predict', methods=['POST'])
@limiter.limit("20 per minute")
def predict():
    try:
        message = request.get_json().get('message')
        session_id, user_id = get_user_ids()
        response = get_response(session_id, user_id, message)
        message = {"answer": response}
        resp = jsonify(message)
        resp.set_cookie('session_id', session_id, httponly=True, secure=True, samesite='Strict')  # Ajout de SameSite
        resp.set_cookie('user_id', user_id, httponly=True, secure=True, samesite='Strict')  # Ajout de SameSite
        return resp
    except Exception as e:
        logging.exception('Une erreur s\'est produite :')
        return jsonify({'error': 'Une erreur s\'est produite.'}), 500

@chatbot_blueprint.route('/save-phrase', methods=['POST'])
def save_phrase():
    try:
        user_id = request.cookies.get('user_id')
        phrase = request.get_json().get('phrase')

        # Create a new Remember instance and add it to the session
        remember_instance = Remember(user_id=user_id, phrase=phrase)
        db.session.add(remember_instance)
        db.session.commit()

        return jsonify({'success': 'Phrase saved successfully.'})
    except Exception as e:
        logging.exception('Une erreur s\'est produite :')
        return jsonify({'error': 'Une erreur s\'est produite.'}), 500
