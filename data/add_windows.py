import sqlite3
conn = sqlite3.connect("transit.db")
for col in ("effective_start", "effective_end"):
    try:
        conn.execute(f"ALTER TABLE advisories ADD COLUMN {col} TEXT")
    except sqlite3.OperationalError:
        pass
conn.commit()
conn.close()
print("Effective window columns ready.")