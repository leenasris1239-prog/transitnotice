import zipfile, sqlite3, csv, os, sys

try:
    zip_name = "in-delhi-delhi-transport-corporation-gtfs-3139.zip"
    if not os.path.exists("gtfs"):
        zipfile.ZipFile(zip_name).extractall("gtfs")

    con = sqlite3.connect("transitnotice.db")
    c = con.cursor()

    tables = ["routes", "stops", "trips", "stop_times"]

    for t in tables:
        c.execute(f"DROP TABLE IF EXISTS {t}")

    for t in tables:
        path = f"gtfs/{t}.txt"
        if not os.path.exists(path):
            path = f"{t}.txt"
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        header = rows[0]
        ncols = len(header)
        cols = ", ".join([f"col{i} TEXT" for i in range(ncols)])
        c.execute(f"CREATE TABLE {t} ({cols})")
        c.executemany(f"INSERT INTO {t} VALUES ({','.join(['?']*ncols)})", rows[1:])

    con.commit()
    counts = {t: c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
    con.close()
    print("SUCCESS")
    for t, n in counts.items():
        print(t, n)
except Exception as e:
    print("ERROR:", type(e).__name__, e)
    sys.exit(1)