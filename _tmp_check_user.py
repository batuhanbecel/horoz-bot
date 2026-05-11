import paramiko, io

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='46.235.8.120', port=22667, username='root', password='XM2KZ51f6aj7tNl', timeout=15, look_for_keys=False, allow_agent=False)

# Check full whitelist table
script = '''
import sqlite3
conn = sqlite3.connect("/root/Zomboid/db/servertest.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(whitelist);")
cols = cursor.fetchall()
print("Columns:", [c[1] for c in cols])
cursor.execute("SELECT * FROM whitelist WHERE username='Batuhan';")
print("Batuhan row:", cursor.fetchall())
cursor.execute("SELECT * FROM role;")
print("Roles:", cursor.fetchall())
conn.close()
'''
sftp = client.open_sftp()
sftp.putfo(io.BytesIO(script.encode()), '/tmp/check_user.py')
sftp.close()

stdin, stdout, stderr = client.exec_command('python3 /tmp/check_user.py')
stdin.close()
out = stdout.read().decode().strip()
print('OUT:')
print(out)

client.close()
