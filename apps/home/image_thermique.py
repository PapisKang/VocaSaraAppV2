import traceback
import cv2
import pytesseract
import re
from openpyxl import Workbook
import logging
import datetime
from openpyxl.chart import DoughnutChart, Reference
from database_connection import execute_query, db_config_client
from PIL import Image as IMG
import openpyxl
from openpyxl.styles import Alignment, Font, Border, Side
import json
from flask import flash, Blueprint, redirect, request, make_response, session
from urllib.parse import unquote
import locale
import math
import mysql.connector
from datetime import datetime
from apps.home import blueprint
import xlsxwriter
from flask.login import current_user
from werkzeug.utils import secure_filename
from PIL import Image
from base64 import b64encode
from apps.authentication.models import UserProfile, Users, RapportGenere, ImageUploadInvisible
from flask import Flask, render_template, request, flash, redirect, session, url_for, send_from_directory, send_file, current_app
from flask import jsonify, g
from flask_sqlalchemy import SQLAlchemy
from apps import db, login_manager
import os
import uuid


try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except Exception as e:
    print("Error can't find tesseract:", e)


@login_required
@blueprint.route("/upload_page_invisible")
def upload_page_invisible():
    return render_template('rapport/traitement_invisible.html')


def prepare_image_from_path(file_path):
    img = image.load_img(file_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = preprocess_input(img_array)
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


@blueprint.route('/results_page_invisible/<rapport_genere_id>', methods=['GET'])
def results_page_invisible(rapport_genere_id):
    # Récupérer les images associées au rapport généré
    images = ImageUploadInvisible.query.filter_by(
        rapport_genere_id=rapport_genere_id).all()
    return render_template('rapport/traitement_invisible.html', images=images)


@login_required
@blueprint.route('/upload_and_traitement_invisible', methods=['POST'])
def upload_and_traitement_invisible():
    try:
        files = request.files.getlist('file')
        user_subdirectory = str(uuid.uuid4())
        user_upload_path = os.path.join(
            app.config['UPLOAD_FOLDER'], user_subdirectory)
        os.makedirs(user_upload_path)

        model_path = 'apps/IA/model/trained_tensorflow_model_MobileNetV2_thermo.h5'
        model = load_model(model_path)
        class_labels_path = 'apps/IA/label/class_labels_thermo.txt'
        with open(class_labels_path, 'r') as f:
            class_labels = f.read().splitlines()

        threshold = 0.5
        rapport_genere_id = None

        for file in files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(user_upload_path, filename)
            file.save(file_path)

            img_array = prepare_image_from_path(file_path)
            predictions = model.predict(img_array)
            predicted_class_indices = np.argmax(predictions, axis=1)
            predicted_label = class_labels[predicted_class_indices[0]]

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
                groupement_troncon=request.cookies.get('groupementTroncon'),
                type_image=request.cookies.get('selectedOption'),
                latitude=latitude,
                longitude=longitude,
                type_defaut=predicted_label,
                temperature=temperature
            )

            # Associate the image with the generated report
            if rapport_genere_id is None:
                rapport_genere_id = request.cookies.get('rapportGenereId')
            new_image.rapport_genere_id = rapport_genere_id

            # Add to the database (no need to commit here)
            db.session.add(new_image)

        # Commit here, after processing all files
        db.session.commit()

        # Remove the subdirectory after processing the images
        shutil.rmtree(user_upload_path)

        # Render the template with the success message and results
        return redirect(url_for('authentication_blueprint.results_page_invisible', rapport_genere_id=rapport_genere_id))

    except Exception as main_exception:
        logging.error(
            f"Error in upload_and_traitement_invisible route: {main_exception}")
        return "Internal Server Error", 500

# Flask routes for upload_page_invisible and results_page_invisible would be here


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
        return (nom_image, coordonnée, température, coordinates[0], coordinates[1])
    except Exception as e:
        logging.error(
            'Erreur lors du traitement de l\'image {}: {}'.format(file_path, str(e)))
        return ('', '', '', '', '')
