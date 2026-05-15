import pandas as pd
import sqlite3
df = pd.read_csv('HACKATHON_FINAL_DB.csv')
conn = sqlite3.connect('farm_data.db')
df.to_sql('products', conn, if_exists='replace', index=False)
conn.close()