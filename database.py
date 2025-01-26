import pandas as pd
import sqlite3

csv_file = 'merged_data_books.csv'

db_file = 'books_sql_db.db'

df = pd.read_csv(csv_file)

conn = sqlite3.connect(db_file)

table_name = 'books'
df.to_sql(table_name, conn, if_exists='replace', index=False)

conn.close()
print(f'Plik CSV załadowano do bazy danych "{db_file}" jako tabelę "{table_name}".')
