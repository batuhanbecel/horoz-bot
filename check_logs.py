import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('46.235.8.120', port=22667, username='root', password='XM2KZ51f6aj7tNl',
          timeout=15, look_for_keys=False, allow_agent=False)
stdin, stdout, stderr = c.exec_command('journalctl -u horoz-bot --since "1 minute ago" --no-pager', get_pty=True)
stdin.close()
print(stdout.read().decode())
c.close()
