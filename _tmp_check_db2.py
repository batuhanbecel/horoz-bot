import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='46.235.8.120', port=22667, username='root', password='XM2KZ51f6aj7tNl', timeout=15, look_for_keys=False, allow_agent=False)

# Use Python's sqlite3 to check DB
script = '''
import sqlite3, sys
try:
    conn = sqlite3.connect("/root/Zomboid/db/servertest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("TABLES:", [t[0] for t in tables])
    for t in tables:
        cursor.execute(f"SELECT * FROM {t[0]}")
        rows = cursor.fetchall()
        print(f"{t[0]}:", rows)
    conn.close()
except Exception as e:
    print("ERROR:", e)
'''

stdin, stdout, stderr = client.exec_command(f'python3 -c "{script}"')
stdin.close()
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print('OUT:', out)
if err:
    print('ERR:', err)

client.close()
