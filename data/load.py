import sqlite3, csv

con = sqlite3.connect('transitnotice.db')
cur = con.cursor()

tables = ['agency', 'calendar', 'routes', 'stops', 'stop_times', 'trips']

for t in tables:
    cur.execute(f'DROP TABLE IF EXISTS {t}')
    with open(f'{t}.txt', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        cur.execute(f"CREATE TABLE {t} ({', '.join(cols)})")
        for row in reader:
            cur.execute(
                f"INSERT INTO {t} VALUES ({','.join('?' * len(cols))})",
                [row.get(c, '') for c in cols]
            )

con.commit()

for t in tables:
    n = cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(t, '=', n)

con.close()
print('DONE - data loaded successfully')