# -*- encoding: utf-8 -*-

from apps.home import blueprint
from flask import render_template,Flask,redirect,request,url_for
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
from apps.authentication.models import UserProfile, Users, ImageUploadVisible, ImageUploadInvisible,RapportGenere,DocumentRapportGenere
from flask import render_template, jsonify, send_file
import json
from sqlalchemy import func
from sqlalchemy import select
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, Border, Side
import io


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
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)

    image_points = ImageUploadVisible.query.paginate(page=page, per_page=per_page, error_out=False)

    map_data = []
    for point in image_points.items:
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

@blueprint.route('/statistiques')
def statistiques():
    # Récupérer les statistiques des types de défauts avec les informations supplémentaires
    type_defaut_stats = db.session.query(
        ImageUploadVisible.type_defaut,
        ImageUploadVisible.nom_operateur,
        ImageUploadVisible.feeder,
        ImageUploadVisible.troncon,
        ImageUploadVisible.zone,
        db.func.count(ImageUploadVisible.type_defaut)
    ).group_by(
        ImageUploadVisible.type_defaut,
        ImageUploadVisible.nom_operateur,
        ImageUploadVisible.feeder,
        ImageUploadVisible.troncon,
        ImageUploadVisible.zone
    ).all()

    # Convertir les données en format approprié pour le graphique
    labels = [row[0] for row in type_defaut_stats]
    values = [row[5] for row in type_defaut_stats]

    # Préparer les données pour le frontend
    data = {
        'labels': labels,
        'values': values,
        'operateurs': [row[1] for row in type_defaut_stats],
        'feeders': [row[2] for row in type_defaut_stats],
        'troncons': [row[3] for row in type_defaut_stats],
        'zones': [row[4] for row in type_defaut_stats],
    }

    # Convertir les données en JSON
    data_json = json.dumps(data)

    # Rendre la page HTML avec les données
    return render_template('statistics/statistics.html', data=data_json)


@blueprint.route('/localisation_defauts_invisible_page')
def localisation_defauts_invisible_page():
    return render_template('/home/localisation_defauts_invisible.html')


@blueprint.route('/statistics_invisible')
def statistics_invisible():
    return render_template('/statistics/statistics_invisible.html')

@blueprint.route('/rapport_id_page')
def rapport_id_page():
    rapports = RapportGenere.query.all()
    return render_template('rapport/rapport_id_page.html',  rapports=rapports)


@blueprint.route('/mes_inspections/<int:rapport_id>', methods=['GET'])
def mes_inspections(rapport_id):
    rapport = RapportGenere.query.get(rapport_id)
    if rapport:
        images_visibles = ImageUploadVisible.query.filter_by(rapport_genere_id=rapport_id).all()
        return render_template('rapport/mes_inspections.html', rapport=rapport, images_visibles=images_visibles)
    else:
        return redirect(url_for('authentication_blueprint.index'))

@blueprint.route('/generate_resume_rapport_page')
def generate_resume_rapport_page():
    rapports = RapportGenere.query.all()
    return render_template('rapport/creer_un_rapport.html',  rapports=rapports)


@blueprint.route('/generate_resume_rapport' ,methods = ['GET'])
def generate_resume_rapport():
    success_message = None
    error_message = None
    try:
        # Récupérer les données depuis la base de données ImageUploadVisible
        curent_date = datetime.now().strftime("%Y-%m-%d")
        
            # Récupérer les paramètres de la requête
        last_image_data = ImageUploadVisible.query.order_by(ImageUploadVisible.upload_date.desc()).first()
        
        # Charger les normes_conseils des défauts à partir du fichier JSON
        with open('./apps/phrase_normes_conseils/normes_conseils.json', encoding='utf-8') as f:
            normes_conseils_data = json.load(f)

            # Utiliser les valeurs récupérées de la base de données
        feeder = last_image_data.feeder
        date = datetime.now().strftime("%Y-%m-%d")  # Convert the date to a string with the format "YYYY-MM-DD"
        nom_operateur = last_image_data.nom_operateur
        zone = last_image_data.zone
        image_data = ImageUploadVisible.query.filter_by(nom_operateur=nom_operateur).all()
        
        # Créer une copie du fichier
        wb_copy = load_workbook('./apps/Exemple_rapport/resume_rapport_visibles_exemple.xlsx')
        feuille_copy = wb_copy.active

        # Écrire dans les cellules spécifiques du fichier d'origine
        feuille_copy['A8'] = "Feeder : " + feeder
        feuille_copy['F3'] = "Date : " + date
        feuille_copy['G6'] = "Nom opérateur : " + nom_operateur
        feuille_copy['G8'] = "Zone : " + zone
        # Définir les styles de cellule
        font = Font(name='Calibri', size=18)
        alignment = Alignment(horizontal='center', vertical='center')
        border = Border(top=Side(border_style='thick'),
                        bottom=Side(border_style='thick'),
                        left=Side(border_style='thick'),
                        right=Side(border_style='thick'))
        
        # Générer des données pour chaque colonne
        row_num = 12
        for image_info in image_data:
            # Logique pour les normes_conseils_data I et J
            # Logique pour les normes_conseils_data I et J
            if image_info.type_defaut is not None:
                defauts = image_info.type_defaut.split("/")  # Divise les défauts par "/"
                defauts = [defaut.strip() + '/' for defaut in defauts]  # Supprime les espaces blancs avant et après chaque défaut et ajoute "/"
            else:
                # Handle the case where image_info.type_defaut is None
                # You might want to log a warning or handle it in a way that makes sense for your application
                error_message = ("Warning: image_info.type_defaut est None (valeur nul) pour image_info with upload_date:", image_info.upload_date)
            colonne_I_values = []
            colonne_J_values = []

            for defaut in defauts:
                if defaut in normes_conseils_data:
                    colonne_I_values.append(normes_conseils_data[defaut]['I'])
                    colonne_J_values.append(normes_conseils_data[defaut]['J'])

            feuille_copy[f'A{row_num}'] = image_info.upload_date  # Date/Heure
            feuille_copy[f'B{row_num}'] = feeder  # feeder
            feuille_copy[f'C{row_num}'] = image_info.troncon  # troncon
            feuille_copy[f'D{row_num}'] = ""  # longeur (à remplacer par la vraie valeur)
            feuille_copy[f'E{row_num}'] = image_info.filename  # Nom de l'image
            latitude_nom = "Latitude"
            longitude_nom = "Longitude"
            feuille_copy[f'F{row_num}'] = f"{latitude_nom} {float(image_info.latitude):.8f}, {longitude_nom} {float(image_info.longitude):.8f}"
            feuille_copy[f'G{row_num}'] = image_info.type_defaut  # Défaut de l'image
            feuille_copy[f'H{row_num}'] = ""  # urgences (à remplacer par la vraie valeur)
            # Écriture des valeurs dans les colonnes I et J
            feuille_copy[f'I{row_num}'] = ', '.join(colonne_I_values)
            feuille_copy[f'J{row_num}'] = ', '.join(colonne_J_values)
            feuille_copy[f'K{row_num}'] = row_num - 11  # Compter de 1 à n

            # Appliquer les styles aux cellules
            for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']:
                cell = feuille_copy[f'{col}{row_num}']
                cell.alignment = alignment
                cell.font = font
                cell.border = border

            # Définir la hauteur des lignes
            feuille_copy.row_dimensions[row_num].height = 138

            row_num += 1  # Incrémenter le numéro de ligne

        # Appliquer le style au titre "Urgences"
        cell_title = feuille_copy['H11']
        cell_title.fill = openpyxl.styles.PatternFill(fill_type='solid', fgColor='FF0000')  # Rouge
        cell_title.font = Font(color="FFFFFF", bold=True)  # Texte blanc en gras
        nom_du_fichier = "Resume_des_rapport_visibles_du_feeder_{}_du_{}_par_{}.xlsx".format(feeder, curent_date, nom_operateur)
        # Enregistrer le fichier Excel en mémoire
        excel_file = io.BytesIO()
        wb_copy.save(excel_file)
        excel_file.seek(0)
        rapports = RapportGenere.query.all()
        # Enregistrer le fichier dans la base de données
        document = DocumentRapportGenere(
            nom_operateur=nom_operateur,
            nom_du_rapport=nom_du_fichier,
            data=excel_file.read()
        )
        db.session.add(document)
        db.session.commit()
        success_message = "Le rapport a été généré avec succès."
    except Exception as e:
        # Handle exceptions or errors
        error_message = f"Une erreur s'est produite : {str(e)}"

    return render_template('rapport/creer_un_rapport.html', rapports=rapports, success_message=success_message, error_message=error_message)

@blueprint.route('/mes_rapports')
def mes_rapports():
    rapports = DocumentRapportGenere.query.all()
    return render_template('rapport/mes_rapports.html', rapports=rapports)

@blueprint.route('/telecharger_rapport/<int:rapport_id>')
def telecharger_rapport(rapport_id):
    try:
        rapport = DocumentRapportGenere.query.get_or_404(rapport_id)
        message = f"Téléchargement du rapport '{rapport.nom_du_rapport}' réussi."
        return send_file(
            io.BytesIO(rapport.data),
            as_attachment=True,
            download_name=f"{rapport.nom_du_rapport}.xlsx"
        )
    except Exception as e:
        error_message = f"Erreur lors du téléchargement du rapport : {str(e)}"
        rapports = DocumentRapportGenere.query.all()
        return render_template('rapport/mes_rapports.html', error_message=error_message, message=message, rapports=rapports)
