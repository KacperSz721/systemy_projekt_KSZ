import matplotlib.pyplot as plt
import io
import base64
import squarify


def create_tree_map(labels, values, title):
    """Generuje wykres typu tree map i zwraca go w formacie Base64."""
    # Sortowanie kategorii i wartości malejąco
    sorted_labels, sorted_values = zip(*sorted(zip(labels, values), key=lambda x: x[1], reverse=True))

    # Normalizacja wartości, aby pasowały do przestrzeni wykresu
    norm_values = squarify.normalize_sizes(sorted_values, sum(sorted_values), 100)

    # Oblicz procentowy udział każdej kategorii
    total_value = sum(sorted_values)
    percentages = [v / total_value * 100 for v in sorted_values]

    # Przygotowanie etykiet: wyświetlamy tylko pierwsze słowo i procentowy udział
    sorted_labels_short = [label.split(',')[0] for label in sorted_labels]  # Pierwsze słowo w etykiecie
    labels_with_percentage = [
        f"{l} ({p:.1f}%)" for l, p in zip(sorted_labels_short, percentages)
    ]

    # Tworzenie wykresu typu tree map, z określeniem układu
    plt.figure(figsize=(12, 8))  # Zwiększenie rozmiaru wykresu dla lepszej czytelności
    squarify.plot(sizes=norm_values, label=labels_with_percentage, color=plt.cm.Paired.colors[:len(sorted_labels)], alpha=.7, pad=True)

    # Tylko dla estetyki, wyłączenie osi i ustawienie tytułu
    plt.title(title)
    plt.axis('off')  # Wyłączenie osi, ponieważ nie są potrzebne w tree mapie

    # Zapisz wykres do pamięci jako Base64
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')  # Dodanie tight bbox, aby nie było zbędnej przestrzeni
    img.seek(0)
    base64_img = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close()
    return base64_img

def generate_bar_chart(labels, values, title, xlabel, ylabel):
    """Generuje wykres poziomy (słupkowy) i zwraca go w formacie Base64."""
    sorted_labels, sorted_values = zip(*sorted(zip(labels, values), key=lambda x: x[1], reverse=False))

    plt.figure(figsize=(10, 6))
    plt.barh(sorted_labels, sorted_values, color='darkcyan')  # Wykres poziomy
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    # Dodanie wartości procentowych na końcu słupków
    for i, v in enumerate(sorted_values):
        plt.text(v / 2, i, f'{v:.1f}', va='center', ha='center', fontweight='bold')

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    base64_img = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close()
    return base64_img

def create_histogram(values, bins, title, xlabel, ylabel):
    """
    Tworzy histogram.
    :param values: Lista wartości.
    :param bins: Liczba przedziałów (lub lista przedziałów).
    :param title: Tytuł wykresu.
    :param xlabel: Etykieta osi X.
    :param ylabel: Etykieta osi Y.
    :return: Obrazek w formacie Base64 do osadzenia w HTML.
    """
    plt.figure(figsize=(10, 6))
    plt.hist(values, bins=bins, color='green', edgecolor='black', alpha=0.7)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()

    # Zapisz wykres do pamięci jako Base64
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    base64_img = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close()
    return base64_img

