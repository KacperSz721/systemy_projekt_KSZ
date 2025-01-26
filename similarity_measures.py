import sqlite3
import math
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import numpy as np
import Levenshtein

def get_db_connection():
    """Nawiązywanie połączenia z bazą danych SQLite."""
    conn = sqlite3.connect('books_sql_db.db')
    conn.row_factory = sqlite3.Row  # Umożliwia dostęp do kolumn po nazwach
    return conn

def process_text(tekst):
    """Tokenizuje tekst do listy słów."""
    slowa = re.split(r'[,\.\?!: ]+', tekst.lower())
    return ' '.join([slowo.strip() for slowo in slowa if slowo])

def dot_product(v1, v2):
    """Oblicza iloczyn skalarny (dot product) dwóch wektorów."""
    return np.dot(v1, v2)

def levenshtein_distance(str1, str2):
    """Oblicza odległość Levenshteina między dwoma ciągami znaków."""
    return Levenshtein.distance(str1, str2)

def calculate_lsi(tfidf_matrix, n_components=100):
    svd = TruncatedSVD(n_components=n_components)
    reduced_matrix = svd.fit_transform(tfidf_matrix)

    # Oddzielenie wektorów dokumentów i wektora zapytania
    reduced_doc_vectors = reduced_matrix[:-1]  # Dokumenty
    reduced_query_vector = reduced_matrix[-1]  # Zapytanie

    return reduced_doc_vectors, reduced_query_vector

def cosine_similarity(v1, v2):
    """Oblicza miarę podobieństwa Cosine'a."""
    norm_m = np.linalg.norm(v1) * np.linalg.norm(v2)
    return np.dot(v1, v2) / norm_m if norm_m > 0 else 0

# def dice_similarity(v1, v2):
#     """Oblicza miarę podobieństwa Dice'a."""
#     dot_p = np.dot(v1, v2)
#     result = np.sum(v1**2) + np.sum(v2**2)
#
#     return (2 * dot_p) / result if result > 0 else 0

def jaccard_sim(v1, v2):
    """Oblicza miarę podobieństwa Jaccarda."""
    dot_p = np.dot(v1, v2)
    denom = np.sum(v1**2) + np.sum(v2**2) - dot_p

    return dot_p / denom if denom > 0 else 0

def calculate_measures(query_text, search_by, similarity_measure, lsi_enabled=False):
    conn = get_db_connection()

    # Pobieranie danych tylko dla wybranego pola
    cursor = conn.execute(f"SELECT {search_by}, title, author, description, genre, format, year FROM books")
    books_data = cursor.fetchall()

    documents = []
    for book in books_data:
        text = book[search_by]  # Pobieranie tekstu z wybranego pola

        # Jeśli tekst jest typu string, obniżamy wielkość liter i używamy go jako dokumentu
        if isinstance(text, str):
            documents.append(text.lower())  # Dodajemy tekst w formie ciągu znaków

        # Jeśli tekst jest listą, łączymy elementy listy w jeden ciąg
        elif isinstance(text, list):
            combined_text = ' '.join(map(str, text))  # Łączenie elementów listy w jeden ciąg
            documents.append(combined_text.lower())  # Dodajemy tekst w formie ciągu znaków

        # Jeśli tekst jest innego typu, dodajemy pusty ciąg
        else:
            documents.append('')

    # Przetwarzanie zapytania
    query_text = process_text(query_text)

    # Obliczanie TF-IDF dla dokumentów i zapytania jednocześnie
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents + [query_text])  # Dokumenty + zapytanie
    if lsi_enabled:
        doc_vectors, query_vector = calculate_lsi(tfidf_matrix, n_components=100)
    else:
        query_vector = tfidf_matrix[-1].toarray().flatten()
        doc_vectors = tfidf_matrix[:-1].toarray()

    # Wybór miary podobieństwa
    similarity_funcs = {
        "cosine_similarity": cosine_similarity,
        #"dice_similarity": dice_similarity,
        "jaccard_sim": jaccard_sim
    }

    if similarity_measure not in similarity_funcs:
        conn.close()
        raise ValueError(f"Unsupported similarity measure: {similarity_measure}")

    similarity_func = similarity_funcs[similarity_measure]
    similarities = [similarity_func(doc_vector, query_vector) for doc_vector in doc_vectors]

    # Dodanie Levenshteina do porównań
    levenshtein_similarities = []
    for book in books_data:
        title = book['title']
        # Obliczanie odległości Levenshteina między zapytaniem a tytułem
        levenshtein_dist = levenshtein_distance(query_text, title.lower())
        levenshtein_similarities.append(levenshtein_dist)

    # Możesz połączyć wyniki Levenshteina z wynikami innych miar (np. przez ważenie ich)
    # Dla przykładu, biorąc odwrotność odległości Levenshteina jako miarę podobieństwa:
    levenshtein_similarity_scores = [1 / (1 + dist) for dist in levenshtein_similarities]  # Odwrócona odległość

    # Pobieranie informacji o książkach z najwyższymi wartościami podobieństwa
    top_indices = np.argsort(similarities)[-5:][::-1]  # Indeksy 5 najlepszych książek
    top_books_full = []
    for index in top_indices:
        book_info = books_data[index]
        similarity_percentage = round(similarities[index] * 100, 2)  # Procent podobieństwa
        levenshtein_similarity_percentage = round(levenshtein_similarity_scores[index] * 100, 2)

        # Formatowanie wyników w żądany sposób (tytuł, autor, podobieństwo, opis)
        book_data = {
            "title": book_info['title'],
            "similarity_percentage": f"{similarity_percentage}",
            "levenshtein_similarity": f"{levenshtein_similarity_percentage}",
            "author": book_info['author'],
            "genre": book_info['genre'],
            "format": book_info['format'],
            "year": book_info['year'],
            "description": book_info['description']
        }
        top_books_full.append(book_data)

    conn.close()
    return top_books_full
