import nltk
import numpy as np
import unidecode
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from langdetect import detect
from transformers import pipeline, AutoTokenizer, AutoModel
from collections import Counter
from spellchecker import SpellChecker
import langid

# Télécharger les ressources nécessaires pour nltk
#nltk.download('punkt', download_dir='C:/nltk_data')
#nltk.download('wordnet', download_dir='C:/nltk_data')


# Initialize stemmer, spell checker, and synonym dictionary
stemmers = {
    'fr': nltk.stem.SnowballStemmer('french'),
    'en': nltk.stem.SnowballStemmer('english')
}
spellers = {
    'fr': SpellChecker(language='fr'),
    'en': SpellChecker(language='en')
}
synonyms = {}
ignore_words = {
    'fr': {'?', '.', '!', '<', '>', ',', '-', '_', ':', ';', '(', ')', '[', ']', 'é', 'ë', 'è', 'ê', 'à', 'â', 'ô', 'î', 'ù', 'û', 'ç', '£', '$', '€', '¥', '§', '%', '*', '&', '@', '#'},
    'en': {'?', '.', '!', '<', '>', ',', '-', '_', ':', ';', '(', ')', '[', ']', 'é', 'ë', 'è', 'ê', 'à', 'â', 'ô', 'î', 'ù', 'û', 'ç', '£', '$', '€', '¥', '§', '%', '*', '&', '@', '#'}
}


def detect_language(msg):
    try:
        lang, _ = langid.classify(msg)
        if lang in ['fr', 'en']:
            return lang
    except Exception as e:
        print(f"Language detection failed: {str(e)}")
    return None


def tokenize(sentence, lang):
    if lang is None:
        return []
    elif lang in spellers:
        corrected = correct_spelling(sentence, lang)
        return word_tokenize(corrected)
    elif lang == 'fr':
        model_name = 'camembert/camembert-large'
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    else:
        model_name = 'bert-large-uncased'
        tokenizer = AutoTokenizer.from_pretrained(model_name)

    tokens = tokenizer.tokenize(sentence)
    return tokens


def stem(word, lang):
    if lang is not None and lang in stemmers:
        stemmer = stemmers[lang]
        return unidecode.unidecode(stemmer.stem(word)).lower()
    else:
        return word


def tfidf_vectorize(sentences):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(sentences)
    feature_names = vectorizer.get_feature_names()
    return vectors, feature_names


def correct_spelling(sentence, lang):
    if lang is None or lang not in spellers:
        return sentence

    words = sentence.split()
    corrected = []
    spell = spellers[lang]
    for word in words:
        if word not in ignore_words[lang] and not word.startswith("http"):
            corrected_word = spell.correction(word)
            corrected.append(corrected_word)
        else:
            corrected.append(word)

    corrected = [word for word in corrected if isinstance(word, str)]
    return " ".join(corrected)


def load_language_model(lang):
    if lang == 'fr':
        return 'camembert/camembert-large'
    elif lang == 'en':
        return 'bert-large-uncased'
    else:
        return None


def get_synonyms_bert(word, lang):
    if word in synonyms:
        return list(synonyms[word])

    model_name = load_language_model(lang)
    if model_name is None:
        return []

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    nlp = pipeline('text2text-generation', model=model, tokenizer=tokenizer)

    try:
        results = nlp(f"Translate: {word}",
                      max_length=200, num_return_sequences=1)
        if results and 'generated_text' in results[0]:
            generated_text = results[0]['generated_text']
            generated_words = word_tokenize(generated_text)
            synonyms_list = [
                generated_word for generated_word in generated_words if generated_word != word]
            synonyms[word] = set(synonyms_list)
            return synonyms_list
    except Exception as e:
        print(f"Failed to retrieve synonyms for '{word}': {str(e)}")

    return []


def expand_expressions(tokenized_sentence, lang):
    expanded_sentence = []
    for word in tokenized_sentence:
        expanded_sentence.append(word)
        synonyms_list = get_synonyms_bert(word, lang)
        expanded_sentence.extend(synonyms_list)
    return expanded_sentence


def get_ngrams(tokenized_sentence, n):
    grams = nltk.ngrams(tokenized_sentence, n)
    return [' '.join(gram) for gram in grams]


def preprocess_sentence(sentence, lang):
    tokenized_sentence = tokenize(sentence, lang)
    expanded_sentence = expand_expressions(tokenized_sentence, lang)
    ngrams_2 = get_ngrams(expanded_sentence, 2)
    ngrams_3 = get_ngrams(expanded_sentence, 3)
    preprocessed_sentence = tokenized_sentence + \
        expanded_sentence + ngrams_2 + ngrams_3
    return preprocessed_sentence


def bag_of_words(tokenized_sentence, all_words, lang):
    stemmed_words = [stem(word, lang) for word in tokenized_sentence]
    ngrams_2 = get_ngrams(tokenized_sentence, 2)
    ngrams_3 = get_ngrams(tokenized_sentence, 3)
    sentence_words = stemmed_words + ngrams_2 + ngrams_3

    bag = np.zeros(len(all_words), dtype=np.float32)
    word_counts = Counter(sentence_words)

    for idx, word in enumerate(all_words):
        stemmed_word = stem(word, lang)
        if stemmed_word in word_counts:
            bag[idx] = word_counts[stemmed_word]

    return bag


def tfidf_bow_vectorize(sentences, lang):
    preprocessed_sentences = (preprocess_sentence(
        sentence, lang) for sentence in sentences)
    vectors, feature_names = tfidf_vectorize(preprocessed_sentences)
    return vectors, feature_names


def vectorize_sentences(sentences, lang):
    vectors, feature_names = tfidf_bow_vectorize(sentences, lang)
    return vectors.toarray()


def get_tfidf_feature_names(lang):
    preprocessed_sentence = preprocess_sentence("", lang)
    _, feature_names = tfidf_vectorize([preprocessed_sentence])
    return feature_names
