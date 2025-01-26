import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import csv

def fetch_page(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response
    else:
        None

def get_book_details(page_soup):
    title = page_soup.find('h1', class_='book__title').text.strip() if page_soup.find('h1',
                                                                                      class_='book__title') else "Unknown"
    author = page_soup.find('a', class_='link-name d-inline-block').text.strip() if page_soup.find('a',
                                                                                                   class_='link-name d-inline-block') else "Unknown"
    description = page_soup.find('div', id='book-description').find('p').text.strip() if page_soup.find('div',
                                                                                                        id='book-description') else "No description"

    details = {dt.text.strip(): dd.text.strip() for dt, dd in zip(page_soup.find_all('dt'), page_soup.find_all('dd'))}

    genre = page_soup.find('a', class_='book__category')
    genre = genre.text.strip() if genre else "Unknown"

    avg_score = page_soup.find('span', class_='big-number')
    if avg_score:
        avg_score = avg_score.text.strip()
        print(avg_score)  # np. "5,7"
    else:
        avg_score = None

    elements = page_soup.find_all('a', class_='btn btn-link book-pages px-0 t-400')
    reviews = None
    ratings = None

    for element in elements:
        text = element.text.strip()

        if 'ocen' in text:
            try:
                reviews = int(text.split()[0])
            except ValueError:
                continue

        elif 'opinii' in text:
            try:
                ratings = int(text.split()[0])
            except ValueError:
                continue

    return title, author, description, details, genre, ratings, reviews, avg_score


def get_book_info(book_link):
    response = fetch_page(book_link)
    if response:
        page_soup = BeautifulSoup(response.text, 'html.parser')
        title, author, description, details, genre, rating, reviews, avg_score = get_book_details(page_soup)
        return {
            'title': title,
            'author': author,
            'description': description,
            'release_date': details.get('Data wydania:'),
            'page_count': details.get('Liczba stron:'),
            'language': details.get('Język:'),
            'publisher': details.get('Wydawnictwo:'),
            'format': details.get('Format:'),
            'ibsn': details.get('ISBN:'),
            'genre': genre,
            'reviews': reviews,
            'ratings': rating,
            'avg_score': avg_score,
            'link': book_link
        }
    return None

def scraping():
    #url = "https://lubimyczytac.pl/katalog?page={}&listId=booksFilteredList&category[]=40&category[]=100&rating[]=0&rating[]=10&publishedYear[]=2000&publishedYear[]=2024&catalogSortBy=published-asc&paginatorType=Standard"
    url = "https://lubimyczytac.pl/katalog?page={}&listId=booksFilteredList&category[]=57&category[]=100&rating[]=0&rating[]=10&publishedYear[]=2000&publishedYear[]=2024&catalogSortBy=published-desc&paginatorType=Standard"
    scraping_output = []

    for page_num in range(1, 100):
        page_url = url.format(page_num)
        page_response = fetch_page(page_url)

        if page_response:
            soup = BeautifulSoup(page_response.text, 'html.parser')
            book_elements = soup.find_all('a', class_='authorAllBooks__singleTextTitle float-left')

            for book_element in book_elements:
                book_link = urljoin(page_url, book_element['href'])
                book_info = get_book_info(book_link)

                if book_info:
                    scraping_output.append(book_info)
                    print(f"Pobrano: {book_info['title']}, {book_info['genre']}")
                print(f"Iteracja {page_num}/100")
    print('Zakończono scraping')
    return scraping_output


def save_data(data, filename="data_books10.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        columns = ['title', 'author', 'release_date', 'page_count', 'language', 'publisher', 'genre', 'format',
                      'reviews', 'ratings', 'description', 'avg_score','ibsn','link']

        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()

        for _ in data:
            writer.writerow(_)

    print(f"Zapisano dane do {filename}")


def main():
    dane_books = scraping()
    save_data(dane_books)


if __name__ == "__main__":
    main()
