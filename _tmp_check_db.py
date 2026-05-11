import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='46.235.8.120', port=22667, username='root', password='XM2KZ51f6aj7tNl', timeout=15, look_for_keys=False, allow_agent=False)

# Check if DB exists
stdin, stdout, stderr = client.exec_command('ls -la /root/Zomboid/db/servertest.db 2>/dev/null || echo NO_DB')
stdin.close()
print('DB exists:', stdout.read().decode().strip())

# Check tables
stdin2, stdout2, stderr2 = client.exec_command('sqlite3 /root/Zomboid/db/servertest.db ".tables" 2>/dev/null || echo NO_TABLES')
stdin2.close()
print('Tables:', stdout2.read().decode().strip())

# Check admin table schema
stdin3, stdout3, stderr3 = client.exec_command('sqlite3 /root/Zomboid/db/servertest.db ".schema admin" 2>/dev/null || echo NO_ADMIN_TABLE')
stdin3.close()
print('Admin schema:', stdout3.read().decode().strip())

# Check current admins
stdin4, stdout4, stderr4 = client.exec_command('sqlite3 /root/Zomboid/db/servertest.db "SELECT * FROM admin;" 2>/dev/null || echo NO_DATA')
stdin4.close()
print('Current admins:', stdout4.read().decode().strip())

client.close()
