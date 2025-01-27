from flask import Flask, render_template, request, flash,jsonify
import sqlite3
from similarity_measures import calculate_measures
from charts import create_bar_chart, get_most_common_words_by_genre,create_wordcloud
from desc_stat_charts import create_tree_map,generate_bar_chart
from names_ent import extract_named_entities_rule_based
from flask_caching import Cache


app = Flask(__name__)

app.config['CACHE_TYPE'] = 'simple'  # Możesz zmienić na 'redis', 'memcached', itp.
app.config['CACHE_DEFAULT_TIMEOUT'] = 600  # 5 minut

cache = Cache(app)

# Konfiguracja bazy danych
database = 'books_sql_db.db'


def get_db_connection():
    """Nawiązywanie połączenia z bazą danych."""
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    return conn

@app.context_processor
def utility_functions():
    """Globalne funkcje pomocnicze."""
    return dict(min=min)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Strona główna z wyszukiwarką, filtrem oraz miarami podobieństwa."""
    search_query = request.args.get('search_query', '')
    similarity_type = request.args.get('similarity_type', 'tfidf')   # Pobierz miarę podobieństwa z formularza
    current_page = int(request.args.get('page', 1))

    # Pobieranie filtrów
    filters = {
        'year': request.args.getlist('year'),
        'format': request.args.getlist('format'),
        'genre': request.args.getlist('genre'),
        'language': request.args.getlist('language'),
        'has_description': request.args.get('has_description', 'True') #nowe
    }

    sort_by = request.args.get('sort_by', 'reviews')  # Domyślnie sortowanie po reviews
    sort_order = request.args.get('sort_order', 'desc')

    items_per_page = 15
    offset = (current_page - 1) * items_per_page

    conn = get_db_connection()

    # Pobranie unikalnych wartości dla kolumn filtra (w tym posortowanego roku)
    filter_options = {}
    for column in ['year', 'format', 'genre', 'language']:
        if column == 'year':
            # Sortowanie 'year' od najnowszego
            filter_options[column] = [row[0] for row in conn.execute(f"SELECT DISTINCT {column} FROM books ORDER BY {column} DESC").fetchall()]
        else:
            filter_options[column] = [row[0] for row in conn.execute(f"SELECT DISTINCT {column} FROM books").fetchall()]

    if sort_by == 'ratings':
        order_column = 'ratings'
    elif sort_by == 'page_count':
        order_column = 'page_count'
    elif sort_by == 'avg_score':
        order_column = 'avg_score'
    else:
        order_column = 'reviews'

    # Budowa zapytania SQL z wyszukiwaniem i filtrami
    query = "SELECT * FROM books WHERE (title LIKE ? OR author LIKE ? OR description LIKE ?)"
    params = [f'%{search_query}%', f'%{search_query}%', f'%{search_query}%']

    # Dodawanie filtrów do zapytania
    for column, values in filters.items():
        if column == 'has_description':
            # Obsługa filtru has_description (domyślnie True, kolumna kodowana binarnie)
            if values in ['True', 'False']:
                query += " AND has_description = ?"
                params.append(1 if values == 'True' else 0)
        elif values:
            query += f" AND {column} IN ({','.join(['?'] * len(values))})"
            params.extend(values)

    query += f" ORDER BY {order_column} {sort_order}"
    # Dodanie paginacji do zapytania SQL
    query += " LIMIT ? OFFSET ?"
    params.extend([items_per_page, offset])

    cursor = conn.execute(query, params)
    books = cursor.fetchall()

    # Obliczenie liczby książek
    total_books_query = "SELECT COUNT(*) FROM books WHERE (title LIKE ? OR author LIKE ? OR description LIKE ?)"
    total_books_params = [f'%{search_query}%', f'%{search_query}%', f'%{search_query}%']

    # Dodanie filtrów do zapytania o liczbę książek
    for column, values in filters.items():
        if column == 'has_description':
            if values in ['True', 'False']:
                total_books_query += " AND has_description = ?"
                total_books_params.append(1 if values == 'True' else 0)
        elif values:
            total_books_query += f" AND {column} IN ({','.join(['?'] * len(values))})"
            total_books_params.extend(values)

    total_books = conn.execute(total_books_query, total_books_params).fetchone()[0]
    total_pages = (total_books + items_per_page - 1) // items_per_page

    # Obsługa formularza POST
    selected_book_id = None
    named_entities = []
    similar_books = []
    if request.method == 'POST':
        title = request.form.get('title')  # Tytuł książki przekazywany w formularzu
        selected_book_id = title

        # Pobranie opisu książki z bazy
        cursor = conn.execute("SELECT description FROM books WHERE title = ?", (title,))
        book = cursor.fetchone()
        conn.close()

        if book and book['description']:
            description = book['description']
            named_entities = extract_named_entities_rule_based(description)
            return jsonify({"success": True, "named_entities": named_entities})

        return jsonify({"success": False, "error": "Not found."})
    conn.close()

    return render_template(
        'index.html',
        books=books,
        search_query=search_query,
        #similarity_measure=similarity_type,  # Przekazanie wybranej miary podobieństwa do szablonu
        filter_options=filter_options,
        filters=filters,
        current_page=current_page,
        total_pages=total_pages,
        results_count=total_books,
        sort_by=sort_by,  # Przekazanie wybranego sortowania
        sort_order=sort_order,
        named_entities=named_entities,
        selected_book_id=selected_book_id,
        similar_books=similar_books
    )

@app.route('/descriptive_statistics', methods=['GET', 'POST'])
@cache.cached(timeout=300, query_string=True)
def descriptive_statistics():
    """Strona z wykresami statystyk opisowych dla książek."""
    selected_chart = request.args.get('chart', 'category_share')  # Domyślnie udział kategorii
    conn = get_db_connection()

    # Pobranie danych do wykresów
    if selected_chart == 'average_page_count':
        # Średnia liczba stron dla kategorii
        query = """
            SELECT genre, AVG(page_count) as avg_pages
            FROM books
            WHERE page_count IS NOT NULL AND genre IS NOT NULL
            GROUP BY genre
            ORDER BY avg_pages DESC
        """
        data = conn.execute(query).fetchall()
        labels = [row[0] for row in data]
        values = [row[1] for row in data]
        chart_image = generate_bar_chart(labels, values, 'Average page number for category', 'Category',
                                         'Average page number')

    elif selected_chart == 'average_score':
        # Średnia wartość cechy avg_score
        query = """
            SELECT genre, AVG(avg_score) as avg_score
            FROM books
            WHERE avg_score IS NOT NULL AND genre IS NOT NULL
            GROUP BY genre
            ORDER BY avg_score DESC
        """
        data = conn.execute(query).fetchall()
        labels = [row[0] for row in data]
        values = [row[1] for row in data]
        chart_image = generate_bar_chart(labels, values, 'Average score for category', 'Category',
                                         'Average score')

    elif selected_chart == 'category_share':
        # Udział poszczególnych kategorii w całości książek
        query = """
            SELECT genre, COUNT(*) as count
            FROM books
            WHERE genre IS NOT NULL
            GROUP BY genre
            ORDER BY count DESC
        """
        data = conn.execute(query).fetchall()
        labels = [row[0] for row in data]
        values = [row[1] for row in data]
        chart_image = create_tree_map(labels, values, 'Category share')

    elif selected_chart == 'format_share':
        # Udział formatów książek w całości
        query = """
            SELECT format, COUNT(*) as count
            FROM books
            WHERE format IS NOT NULL
            GROUP BY format
            ORDER BY count DESC
        """
        data = conn.execute(query).fetchall()
        labels = [row[0] for row in data]
        values = [row[1] for row in data]
        chart_image = create_tree_map(labels, values, 'Format share')

    conn.close()

    return render_template(
        'descriptive_statistics.html',
        selected_chart=selected_chart,
        labels=labels,
        values=values,
        chart_image=chart_image
    )


@app.route('/popular_words_by_year', methods=['GET', 'POST'])
def popular_words_by_year():
    """
    Strona z wykresem chmury słów, zależnym od roku.
    """
    year = 2024  # Domyślny rok
    if request.method == 'POST':
        # Pobierz wybrany rok z formularza
        year = int(request.form['year'])  # Pobierz rok z formularza POST

    # Tworzenie chmury słów na podstawie wybranego roku
    wordcloud_img = create_wordcloud(year)

    return render_template('popular_words_by_year.html', wordcloud_img=wordcloud_img, year=year)


@app.route('/popular_words', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def popular_words():
    selected_genre = request.args.get('genre')
    most_common_words = get_most_common_words_by_genre()

    # Twórz wykresy dla każdego gatunku
    charts = {}
    if selected_genre:
        if selected_genre in most_common_words:
            charts[selected_genre] = create_bar_chart(most_common_words[selected_genre], selected_genre)
    else:
        # Domyślnie generujemy wykresy dla wszystkich gatunków
        for genre, data in most_common_words.items():
            charts[genre] = create_bar_chart(data, genre)

    return render_template('charts.html', charts=charts, genres=list(most_common_words.keys()),
                           selected_genre=selected_genre)

@app.route('/similarity_search', methods=['GET', 'POST'])
@cache.cached(timeout=300, query_string=True)
def similarity_search():
    search_query = request.args.get('search_query', '')
    similarity_type = request.args.get('similarity_type', 'cosine_similarity')  # Pobierz miarę podobieństwa z formularza
    search_by = request.args.get('search_by', 'title')  # Dodane: pole wyszukiwania (domyślnie 'title')
    lsi_enabled = request.args.get('lsi_enabled', 'false') == 'true'
    current_page = int(request.args.get('page', 1))

    # Pobieranie filtrów
    filters = {
        'year': request.args.getlist('year'),
        'format': request.args.getlist('format'),
        'genre': request.args.getlist('genre'),
        'language': request.args.getlist('language')
    }

    items_per_page = 15
    offset = (current_page - 1) * items_per_page

    # Zastosowanie funkcji calculate_measures z zapytaniem
    if search_query:
        results = calculate_measures(search_query, search_by, similarity_measure=similarity_type,lsi_enabled=lsi_enabled)  # Przekazanie pola wyszukiwania do funkcji
    else:
        results = []

    return render_template(
        'similarity_screen.html',
        books=results,
        search_query=search_query,
        search_by=search_by,  # Dodane: przekazanie wybranego pola wyszukiwania do szablonu
        similarity_measure=similarity_type,  # Przekazanie wybranej miary podobieństwa do szablonu
        filter_options={},  # Możesz dodać odpowiednie opcje filtrów
        filters=filters,
        lsi_enabled=lsi_enabled,
        current_page=current_page,
        total_pages=1,  # Można dodać logikę paginacji dla wyników
        results_count=len(results)  # Liczba wyników
    )

if __name__ == '__main__':
    app.run(debug=True)
