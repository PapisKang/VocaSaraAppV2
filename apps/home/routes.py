# -*- encoding: utf-8 -*-

from apps.home import blueprint
from flask import render_template, request,Flask,redirect,request,url_for
from flask_login import login_required
from jinja2 import TemplateNotFound
from apps import db
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField
from wtforms.validators import DataRequired
from datetime import datetime
from apps.authentication.models import Troncon,Feeder,RapportGenere
from flask_login import current_user
from werkzeug.utils import secure_filename
from io import BytesIO
import zlib
import base64
import logging
import os
import base64
from apps.authentication.models import UserProfile, Users, ImageUploadVisible, ImageUploadInvisible
from flask import render_template, jsonify, send_file



@blueprint.route('/<template>')
@login_required
def route_template(template):
    print(template)
    try:
        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment, active_menu, parent, segment_name = get_segment( request )

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template(
            "home/" + template, 
            segment=segment, 
            active_menu=active_menu,
            parent=parent,
            segment_name=segment_name
        )

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment( request ): 

    try:

        segment     = request.path.split('/')[-1]
        active_menu = None
        parent = ""
        segment_name = ""

        core = segment.split('.')[0]
        

        if segment == '':
            segment     = 'index'
 
        parent = core.split('-')[0] if core.split('-')[0] else ""
        segment_name = core


        return segment, active_menu, parent, segment_name

    except:
        return 'index', ''  

# Route pour afficher le formulaire et les listes déroulantes
@blueprint.route('/generation_rapport', methods=['GET'])
def generation_rapport_form():
    feeders_existants = Feeder.query.all()
    troncons_existants = Troncon.query.all()
    return render_template('rapport/generation_rapport.html', feeders_existants=feeders_existants, troncons_existants=troncons_existants)

@blueprint.route('/generate_rapport', methods=['POST'])
def generate_rapport():
    feeders_existants = Feeder.query.all()
    troncons_existants = Troncon.query.all()

    feeder_nom = request.form.get('feeder') or request.form.get('feederInput')
    troncon_nom = request.form.get('troncon') or request.form.get('tronconInput')
    date_debut_str = request.form.get('dateDebut')
    date_fin_str = request.form.get('dateFin')
    operateur = current_user.email
    groupement_troncon = request.form.get('groupementTroncon')
    zone = request.form.get('zone')

    # Vérifier si les champs obligatoires sont vides
    if not feeder_nom or not troncon_nom or not date_debut_str or not date_fin_str or not groupement_troncon or not zone:
        return render_template('rapport/generation_rapport.html', feeders_existants=feeders_existants, troncons_existants=troncons_existants, error_message='Veuillez remplir tous les champs obligatoires.')

    # Vérifier si les champs de date sont vides
    if not date_debut_str or not date_fin_str:
        return render_template('rapport/generation_rapport.html', feeders_existants=feeders_existants, troncons_existants=troncons_existants, error_message='Veuillez remplir les champs de date.')

    try:
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d')
    except ValueError:
        return render_template('rapport/generation_rapport.html', feeders_existants=feeders_existants, troncons_existants=troncons_existants, error_message='Format de date incorrect.')
    
    existing_feeder = Feeder.query.filter_by(Nom=feeder_nom).first()
    if existing_feeder:
        feeder_id = existing_feeder.id
    else:
        new_feeder = Feeder(Nom=feeder_nom)
        db.session.add(new_feeder)
        db.session.commit()
        feeder_id = new_feeder.id

    existing_troncon = Troncon.query.filter_by(Nom=troncon_nom).first()
    if existing_troncon:
        troncon_id = existing_troncon.id
    else:
        new_troncon = Troncon(Nom=troncon_nom)
        db.session.add(new_troncon)
        db.session.commit()
        troncon_id = new_troncon.id

    new_report = RapportGenere(
        nom_operateur=operateur,
        feeder=feeder_nom,
        troncon=troncon_nom,
        date_debut=date_debut,
        date_fin=date_fin,
        zone=zone,
        groupement_troncon=groupement_troncon
    )
    db.session.add(new_report)
    db.session.commit()

    # Ajouter l'id du rapport généré aux cookies
    response = redirect(url_for('home_blueprint.confirmation_page'))
    response.set_cookie('rapportGenereId', str(new_report.id))
    
    return response

# Nouvelle route pour afficher la page avec les deux boutons et le texte explicatif
@blueprint.route('/confirmation_page', methods=['GET'])
def confirmation_page():
    return render_template('rapport/confirmation_page.html')


@blueprint.route('/apropos')
def apropos():
    return render_template('home/apropos.html', segment='apropos')




@blueprint.route('/acceuil')
def acceuil():
    return render_template('home/acceuil.html')



@blueprint.route('/get_map_data')
def get_map_data():
    # Récupérer les données nécessaires de la base de données
    image_points = ImageUploadVisible.query.all()

    # Préparer les données pour la carte
    map_data = []
    for point in image_points:
        data = {
            'latitude': point.latitude,
            'longitude': point.longitude,
            'type_defaut': point.type_defaut,
            'feeder': point.feeder,
            'troncon': point.troncon,
            'zone': point.zone,
            'filename': point.filename,
            'nom_operateur': point.nom_operateur,
            'upload_date': point.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
            'image_binary': point.data

        }
        map_data.append(data)

    return jsonify(map_data)

@blueprint.route('/localisation_page')
def localisation_page():
    return render_template('home/localisation_defauts.html')