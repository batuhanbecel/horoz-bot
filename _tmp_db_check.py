import sqlite3, json
try:
    conn = sqlite3.connect("/root/Zomboid/db/servertest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    result = {"tables": [t[0] for t in tables]}
    for t in tables:
        cursor.execute(f"SELECT * FROM {t[0]}")
        rows = cursor.fetchall()
        result[t[0]] = rows
    conn.close()
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": str(e)}))
