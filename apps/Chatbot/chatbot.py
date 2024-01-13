import random
import json
import torch
from nltk_utils import tokenize, bag_of_words, detect_language
from model import NeuralNet
from datetime import datetime
from datetime import time
import time
import uuid
from fuzzywuzzy import fuzz
import mysql.connector
import config
import nltk

# Télécharger les ressources nécessaires pour nltk
#nltk.download('punkt', download_dir='C:/nltk_data')
#nltk.download('wordnet', download_dir='C:/nltk_data')


conn = mysql.connector.connect(
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    database= config.DB_DATABASE,
    host=config.DB_HOST,
)
c = conn.cursor()
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

with open('./apps/Chatbot/data/french/random_mess.json', 'r', encoding='utf-8') as f:
    messages_fr = json.load(f)

with open('./apps/Chatbot/data/french/remember.json', 'r') as f:
    remember_fr = json.load(f)

with open('./apps/Chatbot/data/english/random_mess_en.json', 'r', encoding='utf-8') as f:
    messages_en = json.load(f)

with open('./apps/Chatbot/data/english/remember_en.json', 'r') as f:
    remember_en = json.load(f)

with open('./apps/Chatbot/data/full/intents.json', 'r', encoding='utf-8') as f:
    start = time.time()
    intents = json.load(f)
    end = time.time()
    print(f'Time taken to load json file: {end-start:.5f} seconds')

FILE = "./apps/Chatbot/model/data.pth"
try:
    data = torch.load(FILE)
except:
    data = torch.load(FILE,map_location=torch.device('cpu'))

input_size = data["input_size"]
hidden_size = data["hidden_size"]
output_size = data["output_size"]
all_words = data['all_words']
tags = data['tags']
model_state = data["model_state"]

model = NeuralNet(input_size, hidden_size, output_size).to(device)
try:
    model.load_state_dict(model_state)
except:
    model.load_state_dict(model_state,map_location=torch.device('cpu'))
model.eval()

bot_name = "lanc"

context = {
    'last_question': None,
    'last_response': None
}


# Création de la table pour stocker les conversations
c.execute('''CREATE TABLE IF NOT EXISTS conversations
         (id INT AUTO_INCREMENT PRIMARY KEY, session_id VARCHAR(255), user_id VARCHAR(255), user_message TEXT,
              bot_response TEXT, intent_tag TEXT, date DATETIME)''')

c.execute('''CREATE TABLE IF NOT EXISTS remember
         (id INT AUTO_INCREMENT PRIMARY KEY, user_id VARCHAR(255), phrase TEXT)''')


# Ajout de la colonne session_id si elle n'existe pas
c.execute("DESCRIBE conversations")
columns = [col[0] for col in c.fetchall()]
if 'session_id' not in columns:
    c.execute("ALTER TABLE conversations ADD COLUMN session_id text")

# Ajout de la colonne user_id si elle n'existe pas
if 'user_id' not in columns:
    c.execute("ALTER TABLE conversations ADD COLUMN user_id text")

if 'date' not in columns:
    c.execute("ALTER TABLE conversations ADD COLUMN date text")

# Fonction pour générer un identifiant de session unique


def generate_session_id():
    return str(uuid.uuid4())


def remember_conversation(question, answer):
    # Ajouter la question et la réponse à la mémoire de conversation
    context['last_question'] = question
    context['last_response'] = answer


def generate_response(question, msg):
    # Vérifier si la question correspond à la dernière question posée
    if 'last_question' in context and context['last_question'] == question:
        # Renvoyer la dernière réponse enregistrée
        return context['last_response']
    else:
        # Exécuter le code existant pour générer une réponse
        # Ajouter le paramètre msg ici
        response = get_response(session_id, user_id, msg)
        # Enregistrer la question et la réponse actuelles dans le contexte
        context['last_question'] = question
        context['last_response'] = response
        return response


def save_phrase(user_id, phrase):
    c = conn.cursor()
    c.execute("INSERT INTO remember (user_id, phrase) VALUES (%s, %s)",
              (user_id, phrase))
    conn.commit()
    conn.close()


def get_response(session_id, user_id, msg):
    global context
    # Detect the language of the user input
    lang = detect_language(msg)
    if lang is None:
        try:
            lang = 'fr'
        except:
            lang = 'en'
    remember_keywords = []
    remember_phrases = []
    ban_words = []
    not_found_msg = []
    suggest_msg = []
    possible_messages = []
    sorry_msg = []
    same_quest = []
    sentence = []
    # Utiliser les listes dans votre code
    if lang == 'fr':
        not_found_msg = random.choice(messages_fr['not_found_fr'])
        suggest_msg = random.choice(messages_fr['suggest_messages_fr'])
        possible_messages = random.choice(messages_fr['possible_answer_fr'])
        sorry_msg = random.choice(messages_fr['sorry_fr'])
        same_quest = random.choice(messages_fr['same_question_fr'])
        sentences = random.choice(messages_fr['sentences_fr'])
        remember_keywords = remember_fr['remember_keywords_fr']
        remember_phrases = remember_fr['remember_phrases_fr']
        ban_words = ['drogue', 'poison', 'bombe', 'assassinat',
                     "meurtre", "piratage", "mot de passe"]
        ban_msg = random.choice(messages_fr['ban_fr'])
    elif lang == "en":
        not_found_msg = random.choice(messages_en['not_found_en'])
        suggest_msg = random.choice(messages_en['suggest_messages_en'])
        possible_messages = random.choice(messages_en['possible_answer_en'])
        sorry_msg = random.choice(messages_en['sorry_en'])
        same_quest = random.choice(messages_en['same_question_en'])
        sentences = random.choice(messages_en['sentences_en'])
        remember_keywords = remember_en['remember_keywords_en']
        remember_phrases = remember_en['remember_phrases_en']
        ban_words = ['drug', 'poison', 'bomb', 'assassination',
                     "murder", "hack", "password", "hacking"]
        ban_msg = random.choice(messages_en['ban_en'])

    c = conn.cursor()
    # Vérifier si l'utilisateur a déjà une conversation en cours
    c.execute("SELECT * FROM conversations WHERE session_id=%s AND user_id=%s",
              (session_id, user_id))
    conversation = c.fetchone()
    c.fetchall()

    if conversation:
        # Si l'utilisateur a déjà une conversation en cours, récupérer le contexte précédent
        context['intent'] = conversation[4]

        # Vérifier si la question correspond à la dernière question poséeg
        if 'last_question' in context and context['last_question'] == msg:
            response = context['last_response']
            page = context.get('page', None)
            if page:
                response_text = f"{response} ({page})"
            else:
                response_text = response

            # Répondre à l'utilisateur avec la dernière réponse et question
            return f"{same_quest} : {msg}.\nVoici quelle était la réponse à cette question : {response_text}"

    # Vérifier si la question est une demande de mémorisation
    if any(keyword in msg.lower() for keyword in remember_keywords):
        phrase = msg.split(':')[-1].strip()  # Extraire la phrase à mémoriser

        try:
            # Ouvrir un curseur pour exécuter des requêtes
            cursor = conn.cursor()
            # Enregistrer la phrase dans la base de données
            cursor.execute(
                "INSERT INTO remember (user_id, phrase) VALUES (%s, %s)", (user_id, phrase))
            # Valider les modifications dans la base de données
            conn.commit()
            # Fermer le curseur
            cursor.close()
            if lang == "fr":
                return "D'accord, j'ai mémorisé cette phrase."
            elif lang == "en":
                return "Ok i just memorize this sentence"
        except mysql.connector.Error as error:
            # Gérer les erreurs de base de données
            if lang == 'fr':
                return "Désolé, une erreur s'est produite lors de l'enregistrement de la phrase."
            elif lang == "en":
                return "sorry, i can't save this for now, try later"

    # Vérifier si la question est une demande de récupération des phrases mémorisées
    if any(keyword in msg.lower() for keyword in remember_phrases):
        try:
            # Ouvrir un curseur pour exécuter des requêtes
            cursor = conn.cursor()
            # Exécuter la requête pour récupérer les phrases mémorisées
            cursor.execute(
                "SELECT phrase FROM remember WHERE user_id=%s", (user_id,))
            phrases = cursor.fetchall()
            if phrases:
                # Construire une chaîne contenant toutes les phrases mémorisées
                remembered_phrases = '\n- '.join([phrase[0]
                                                 for phrase in phrases])
                return f"{sentences} :\n- {remembered_phrases}"
            else:
                if lang == 'fr':
                    return "Je ne me souviens d'aucune phrase."
                elif lang == 'en':
                    return "i don't rememeber any sentences for now"
            # Fermer le curseur
            cursor.close()
        except mysql.connector.Error as error:
            # Gérer les erreurs de base de données
            if lang == "fr":
                return "Désolé, une erreur s'est produite"
            elif lang == "en":
                return "sorry an error appear, please try again"

    sentence = tokenize(msg, lang)
    X = bag_of_words(sentence, all_words, lang)
    X = X.reshape(1, X.shape[0])
    X = torch.from_numpy(X).to(device)

    output = model(X)
    _, predicted = torch.max(output, dim=1)
    tag = tags[predicted.item()]
    probs = torch.softmax(output, dim=1)
    prob = probs[0][predicted.item()]

    # ...
    if prob.item() > 1:
        for intent in intents['intents']:
            if tag == intent["tag"]:
                # Stocker l'intention actuelle dans le contexte
                context['intent'] = intent['tag']

                # Extraire la réponse pertinente
                response = random.choice(intent['responses'])
                # Extraire la page pertinente (si elle existe)
                page = response.get('page', None)
                # Vérifier si la question contient une demande de page
                if intent.get('page_request', False) and any(word in msg.lower() for word in ['page', 'numéro']):
                    # Ajouter la référence de la page à la réponse
                    response_text = f"{response['text']} ({page})"
                else:
                    # Utiliser la réponse telle quelle
                    response_text = response['text']
                # Stocker la réponse et la page pertinente dans le contexte
                context['response'] = response_text
                context['page'] = page

                # Enregistrer la conversation dans la base de données
                now = datetime.now()
                today = now.strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO conversations (session_id, user_id, user_message, bot_response, intent_tag, date) VALUES (%s, %s, %s, %s, %s, %s)",
                    (session_id, user_id, msg, context["response"], intent["tag"], today))
                conn.commit()
                # Enregistrer la question et la réponse dans la mémoire de conversation
                # Utiliser le paramètre msg ici
                remember_conversation(msg, response_text)

                # Répondre à l'utilisateur
                return context['response']

    best_match = None
    best_score = 0

    # Essayer différentes stratégies de correspondance
    for intent in intents['intents']:
        for pattern in intent['patterns']:
            scores = [
                fuzz.ratio(pattern.lower(), msg.lower()),
                fuzz.partial_ratio(pattern.lower(), msg.lower()),
                fuzz.token_sort_ratio(pattern.lower(), msg.lower())
                # Ajoutez d'autres stratégies si nécessaire
            ]
            ratio = max(scores)

            if ratio > best_score:
                best_score = ratio
                best_match = pattern

    # Limiter la recherche aux intentions reconnues
    if best_match and best_score > 70:
        # Trouver la réponse correspondante à la question la plus proche dans le fichier JSON
        for intent in intents['intents']:
            if best_match in intent['patterns']:
                response = random.choice(intent['responses'])
                # Extraire la page pertinente (si elle existe)
                page = response.get('page', None)
                # Vérifier si la question contient une demande de page
                if intent.get('page_request', False) and any(word in msg.lower() for word in ['page', 'numéro']):
                    # Ajouter la référence de la page à la réponse
                    response_text = f"{response['text']} ({page})"
                else:
                    # Utiliser la réponse telle quelle
                    response_text = response['text']
                # Ajouter la réponse la plus proche à la réponse
                response = response_text
                # Stocker la réponse et la page pertinente dans le contexte
                context['response'] = response
                context['page'] = page
                context['intent'] = intent['tag']
                # Enregistrer la conversation dans la base de données
                now = datetime.now()
                today = now.strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO conversations (session_id, user_id, user_message, bot_response, intent_tag, date) VALUES (%s, %s, %s, %s, %s, %s)",
                    (session_id, user_id, msg, context["response"], intent["tag"], today))
                conn.commit()

                # Enregistrer la question et la réponse dans la mémoire de conversation
                remember_conversation(msg, response_text)

                # Répondre à l'utilisateur
                return context['response']

    # Si le modèle ne parvient pas à prédire une intention avec une probabilité suffisante, rechercher la question la plus proche dans le fichier JSON
    # et proposer une réponse alternative à l'utilisateur.
    # Utiliser la distance de Levenshtein pour trouver la question la plus proche.
    # Si la distance de Levenshtein est inférieure à un seuil, proposer cette question à l'utilisateur.
    # Sinon, renvoyer une réponse par défaut.
    else:
        for word in ban_words:
            if word in msg.lower():
                response = ban_msg
                # Stocker la réponse dans le contexte
                context['response'] = response
                context['page'] = None
                context['intent'] = None
                # Enregistrer la conversation dans la base de données
                now = datetime.now()
                today = now.strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO conversations (session_id, user_id, user_message, bot_response, intent_tag, date) VALUES (%s, %s, %s, %s, %s, %s)",
                    (session_id, user_id, msg, context["response"], None, today))
                conn.commit()

                # Enregistrer la question et la réponse dans la mémoire de conversation
                remember_conversation(msg, response)

                # Répondre à l'utilisateur
                return response

    best_match = None
    best_score = 0

    # Essayer différentes stratégies de correspondance
    for intent in intents['intents']:
        for pattern in intent['patterns']:
            scores = [
                fuzz.ratio(pattern.lower(), msg.lower()),
                fuzz.partial_ratio(pattern.lower(), msg.lower()),
                fuzz.token_sort_ratio(pattern.lower(), msg.lower())
                # Ajoutez d'autres stratégies si nécessaire
            ]
            ratio = max(scores)

            if ratio > best_score:
                best_score = ratio
                best_match = pattern

    # Limiter la recherche aux intentions reconnues
    if best_match and best_score > 60:
        # Trouver la réponse correspondante à la question la plus proche dans le fichier JSON
        for intent in intents['intents']:
            if best_match in intent['patterns']:
                response = random.choice(intent['responses'])
                # Extraire la page pertinente (si elle existe)
                page = response.get('page', None)
                # Vérifier si la question contient une demande de page
                if intent.get('page_request', False) and any(word in msg.lower() for word in ['page', 'numéro']):
                    # Ajouter la référence de la page à la réponse
                    response_text = f"{response['text']} ({page})"
                else:
                    # Utiliser la réponse telle quelle
                    response_text = response['text']
                # Ajouter la réponse la plus proche à la réponse
                response = f"{not_found_msg} '{msg}', {suggest_msg} : '{best_match}'.\n{possible_messages } :\n{response_text}"
                # Stocker la réponse et la page pertinente dans le contexte
                context['response'] = response
                context['page'] = page
                context['intent'] = intent['tag']
                # Enregistrer la conversation dans la base de données
                now = datetime.now()
                today = now.strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO conversations (session_id, user_id, user_message, bot_response, intent_tag, date) VALUES (%s, %s, %s, %s, %s, %s)",
                    (session_id, user_id, msg, context["response"], intent["tag"], today))
                conn.commit()

                # Enregistrer la question et la réponse dans la mémoire de conversation
                remember_conversation(msg, response_text)

                # Répondre à l'utilisateur
                return context['response']

    # Répondre à l'utilisateur avec une réponse par défaut
    response = f"{sorry_msg} : '{msg}'."
    # Stocker la réponse dans le contexte
    context['response'] = response
    context['page'] = None
    context['intent'] = None
    # Enregistrer la conversation dans la base de données
    now = datetime.now()
    today = now.strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO conversations (session_id, user_id, user_message, bot_response, intent_tag, date) VALUES (%s, %s, %s, %s, %s, %s)",
        (session_id, user_id, msg, context["response"], None, today))
    conn.commit()

    # Enregistrer la question et la réponse dans la mémoire de conversation
    remember_conversation(msg, response)

    # Répondre à l'utilisateur
    return response


if __name__ == "__main__":
    print("Let's chat! (type 'quit' to exit)")
    while True:
        session_id = generate_session_id()
        user_id = generate_session_id()
        while True:
            # Obtenir l'entrée de l'utilisateur
            sentence = input(f"Utilisateur: ")
            if sentence == "quit":
                break
            # Obtenir la réponse du bot
            resp = get_response(session_id, user_id, sentence)
            if resp:
                # Afficher la réponse petit à petit
                for char in resp:
                    print(char, end='', flush=True)
                    time.sleep(0.003)
            print(f"{bot_name}: {resp}")
