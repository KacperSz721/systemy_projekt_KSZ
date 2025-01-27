import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from stopwords import get_stopwords
from nltk.stem import WordNetLemmatizer
import string
import re

nltk.download('punkt')
nltk.download('stopwords')


def extract_named_entities_rule_based(text):

    ENGLISH_STOPWORDS = set(stopwords.words('english'))
    POLISH_STOPWORDS = set(['Ta', 'Jego', 'Jej', "Jemu","W","I","Książka","Lektura","Książce"])  # Dodatkowe polskie stopwords
    STOPWORDS_pl = set(get_stopwords('pl'))  # Użycie niestandardowych stop-words

    pattern = r'\b\w*(jąc|ść|nie|ąca|ący|ące|az|na|niej|łam|łem|am)\b'
    matched_words = re.findall(pattern, text)

    stop_words = ENGLISH_STOPWORDS | POLISH_STOPWORDS | STOPWORDS_pl | set(matched_words)
    lemmatizer = WordNetLemmatizer()

    sentences = sent_tokenize(text)
    named_entities = []

    for sentence in sentences:
        words = word_tokenize(sentence)
        # Przekształcenie słów do formy podstawowej (lematyzacja)
        words = [lemmatizer.lemmatize(word) for word in words]

        # Wyłapanie słów zaczynających się wielką literą, pomijając stop-słowa i interpunkcję
        for i, word in enumerate(words):
            # Sprawdzamy, czy wyraz zaczyna się wielką literą
            if word[0].isupper() and word not in stop_words and word not in string.punctuation:
                # Sprawdzamy, czy kolejne słowo też może być częścią nazwy własnej
                if i + 1 < len(words) and words[i + 1][0].isupper():
                    named_entities.append(f"{word} {words[i + 1]}")
                else:
                    named_entities.append(word)

    return list(set(named_entities))





