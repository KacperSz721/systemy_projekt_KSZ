import sqlite3
import base64
import io
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import matplotlib.pyplot as plt
from stopwords import get_stopwords
from wordcloud import WordCloud

# Załaduj dane językowe w NLTK
nltk.download('stopwords')
nltk.download('wordnet')

# Inicjalizacja lematyzera
lemmatizer = WordNetLemmatizer()
# Pobieranie stopwords z NLTK i stopwords z pakietu
ENGLISH_STOPWORDS = set(stopwords.words('english'))
STOPWORDS_pl = set(get_stopwords('pl'))
POLISH_STOPWORDS =set(['jego', 'jej', 'oni', 'także', 'tego', 'tak', 'jako', 'tylko', 'tym', 'temu',
    'książka', 'książki', 'lektura', 'książce', 'książki', 'życia', 'życiu',
    'która','której','któremu','jednak','jeszcze','sobie','siebie',
    'lat','roku','opisu','posiada','lata','oraz','ale','który','był','była','autor','też','tej','ta',
    'pod','aby','lata','dzięki','przez','które','których','ludzi','nad','tych','gdy','życie',
    'będzie','life','również','latach','było','swoje','swoją','wiele','wielu','świata','można','wieku','sposób',
    'new','i"m','he"s','ktoś','serii','między','którzy','nawet','którym','zarówno','autora','człowieka'
    'jaki','jaka','jakie','jakim','historii','polski','polsce','polskim','polskiego','polskich','historię','były',
    'wojny','temat','przy','w','jak','innych','lecz','coś','swojego','ani','wciąż','bowiem','mogą','miała','miał',
    'końcu','m','teraz','nie','takich','swój','mój','moje','dwoje','wie','nikt','ponad','przedstawia','czy','s','czyli'])

STOPWORDS = ENGLISH_STOPWORDS | POLISH_STOPWORDS | STOPWORDS_pl


def get_most_common_words_by_genre():
    """
    Analizuje bazę danych, aby znaleźć najpopularniejsze słowa w opisach/tytułach dla każdego gatunku.
    :return: Słownik z gatunkami jako kluczami i najczęstszymi słowami jako wartościami.
    """
    database = 'books_sql_db.db'
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # Pobierz dane: gatunek i tekst (np. tytuł + opis)
    query = """
        SELECT genre, title || ' ' || description AS text
        FROM books
        WHERE genre IS NOT NULL AND text IS NOT NULL
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    genre_word_counts = {}

    # Przetwarzanie danych książek
    for genre, text in rows:
        # Sprawdź, czy tekst zawiera frazę "Ta książka nie zawiera jeszcze opisu"
        if "ta książka nie zawiera jeszcze opisu" in text.lower():
            continue  # Pomiń książki z takim opisem

        # Tokenizacja i czyszczenie tekstu
        text = text.lower()

        # Tokenizacja z usunięciem znaków interpunkcyjnych
        words = [word.strip(",.!?:;()[]\"'") for word in text.split() if len(word) > 2]

        # Filtracja i lematyzacja
        cleaned_words = [
            lemmatizer.lemmatize(word) for word in words
            if word not in STOPWORDS
        ]

        if genre not in genre_word_counts:
            genre_word_counts[genre] = Counter()
        genre_word_counts[genre].update(cleaned_words)

    most_common_words = {
        genre: genre_word_counts[genre].most_common(10) for genre in genre_word_counts
    }

    return most_common_words


def create_bar_chart(data, genre):
    """
    Tworzy wykres słupkowy najpopularniejszych słów dla danego gatunku.
    :param data: Lista krotek (słowo, liczba wystąpień).
    :param genre: Nazwa gatunku.
    :return: Obrazek w formacie Base64 do osadzenia w HTML.
    """
    words, counts = zip(*data)

    plt.figure(figsize=(10, 6))
    plt.bar(words, counts, color='skyblue')
    plt.title(f"Najpopularniejsze słowa w gatunku: {genre}")
    plt.xlabel("Słowa")
    plt.ylabel("Liczba wystąpień")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Zapisz wykres do pamięci jako Base64
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    base64_img = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close()
    return base64_img

def create_wordcloud(year):
    """
    Tworzy chmurę słów z tekstów książek wydanych w wybranym roku.
    :param year: Rok, który ma być uwzględniony w analizie.
    :return: Obrazek chmury słów w formacie Base64.
    """
    database = 'books_sql_db.db'
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # Pobierz dane: tytuł + opis książki z wybranego roku
    query = """
        SELECT title || ' ' || description AS text
        FROM books
        WHERE year = ? AND text IS NOT NULL
    """
    cursor.execute(query, (year,))
    rows = cursor.fetchall()
    conn.close()

    # Zbieranie słów z książek w wybranym roku
    text = " ".join([row[0] for row in rows])

    # Tokenizacja i lematyzacja
    words = [word.strip(",.!?:;()[]\"'") for word in text.lower().split() if len(word) > 2]
    cleaned_words = [
        lemmatizer.lemmatize(word) for word in words
        if word not in STOPWORDS
    ]

    # Tworzenie chmury słów
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(" ".join(cleaned_words))

    # Zapisz chmurę słów do pamięci jako Base64
    img = io.BytesIO()
    wordcloud.to_image().save(img, format='PNG')
    img.seek(0)
    base64_img = base64.b64encode(img.getvalue()).decode('utf-8')
    return base64_img
