"""
Horoz Bot — Otomatik VPS Deploy Scripti
========================================
Kullanım:  python deploy.py

Paramiko kurulu değilse otomatik yükler, ardından SSH ile VPS'ye bağlanıp
git pull + systemctl restart işlemlerini yapar.
"""
from __future__ import annotations

import sys
import subprocess
import time

# ── Paramiko kontrolü / otomatik kurulum ───────────────────────────────────────
try:
    import paramiko
except ImportError:
    print("[!] paramiko bulunamadı. Otomatik yükleniyor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "--quiet"])
    import paramiko  # noqa: F811
    print("[✓] paramiko yüklendi.\n")


# ── Yapılandırma ──────────────────────────────────────────────────────────────
HOST     = "46.235.8.120"
PORT     = 22667
USER     = "root"
PASSWORD = "XM2KZ51f6aj7tNl"
REMOTE_DIR = "/opt/horoz_bot"
SERVICE  = "horoz-bot"


def run_remote(ssh: paramiko.SSHClient, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Tek bir komut çalıştırır; (exit_code, stdout, stderr) döner."""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=True)
    # PTY açıkken bazen şifre prompt'u vs. gelir; otomatik cevap vermek için stdin'i kapat
    stdin.close()
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return exit_code, out, err


def deploy() -> int:
    print(f"[→] Bağlanılıyor: {USER}@{HOST}:{PORT}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=HOST,
            port=PORT,
            username=USER,
            password=PASSWORD,
            timeout=15,
            look_for_keys=False,      # sadece şifre dene
            allow_agent=False,        # SSH agent devre dışı
        )
    except paramiko.AuthenticationException:
        print("[✗] Kimlik doğrulama başarısız — şifre reddedildi.")
        print("    Muhtemel nedenler:")
        print("    • Sunucu 'PasswordAuthentication=no' ile çalışıyor (anahtar zorunlu)")
        print("    • Root login kapalı (PermitRootLogin=no)")
        print("    • Şifre değişmiş / expire olmuş")
        return 1
    except Exception as exc:
        print(f"[✗] Bağlantı hatası: {exc}")
        return 1

    print("[✓] Bağlantı kuruldu.\n")

    # 0) Python cache temizliği (eski .pyc dosyaları yeni kodu gizleyebilir)
    print(f"[→] {REMOTE_DIR} → __pycache__ temizleniyor...")
    ec, out, err = run_remote(client, f"cd {REMOTE_DIR} && find . -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null; echo 'Cache temizlendi'")
    print(out)

    # 1) Git pull
    print(f"[→] {REMOTE_DIR} → git pull origin master")
    ec, out, err = run_remote(client, f"cd {REMOTE_DIR} && git pull origin master")
    print(out)
    if err:
        print(f"[!] stderr: {err}")
    if ec != 0:
        print(f"[✗] git pull başarısız (exit {ec})")
        client.close()
        return 1
    print("[✓] Kod güncellendi.\n")

    # 2) Servisi yeniden başlat
    print(f"[→] systemctl restart {SERVICE}")
    ec, out, err = run_remote(client, f"systemctl restart {SERVICE}")
    if ec != 0:
        print(f"[✗] Restart başarısız (exit {ec})")
        print(f"    stderr: {err}")
        client.close()
        return 1
    print("[✓] Servis restart edildi.\n")

    # 3) Durum kontrolü
    print(f"[→] systemctl status {SERVICE} --no-pager")
    ec, out, err = run_remote(client, f"systemctl status {SERVICE} --no-pager")
    print(out)
    if "active (running)" in out.lower():
        print("\n[✓✓✓] Bot aktif ve çalışıyor!")
    else:
        print("\n[!] Bot durumu 'active (running)' değil — logları kontrol edin.")

    # 4) Log kontrolü (son 20 satır)
    print(f"\n[→] Son loglar (journalctl -u {SERVICE} -n 20 --no-pager)")
    ec, out, err = run_remote(client, f"journalctl -u {SERVICE} -n 20 --no-pager")
    print(out)
    if err:
        print(f"[!] stderr: {err}")

    client.close()
    print("\n[→] Bağlantı kapatıldı.")
    return 0


if __name__ == "__main__":
    sys.exit(deploy())
