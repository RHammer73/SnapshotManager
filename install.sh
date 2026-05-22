#!/bin/bash
# SnapshotManager Installationsscript
# Voraussetzungen: Debian/Ubuntu, root-Rechte
set -e

# Installationsverzeichnis = Verzeichnis des Scripts (kein hardcodierter Pfad)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
SERVICE_USER="snapshotmgr"
VENV="$APP_DIR/backend/venv"

echo "=== SnapshotManager Installation ==="

# 1. System-Abhängigkeiten installieren
echo "[1/6] Installiere System-Abhängigkeiten..."
apt-get update -qq
# Python 3.13 ist auf Ubuntu < 24.10 und Debian < 13 nicht im Standard-Repo enthalten.
# deadsnakes-PPA liefert es für Ubuntu; auf Debian wird backports versucht.
if ! python3.13 --version &>/dev/null 2>&1; then
    if command -v add-apt-repository &>/dev/null; then
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update -qq
    else
        # Debian: backports eintragen falls noch nicht vorhanden
        CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
        BACKPORTS="${CODENAME}-backports"
        if ! grep -qr "$BACKPORTS" /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null; then
            echo "deb http://deb.debian.org/debian ${BACKPORTS} main" \
                > /etc/apt/sources.list.d/backports.list
        fi
        apt-get update -qq
    fi
fi
apt-get install -y python3.13 python3.13-venv python3-pip nodejs npm wireguard zfsutils-linux curl

# 2. App-Verzeichnis einrichten
echo "[2/6] Richte App-Verzeichnis ein..."
mkdir -p "$APP_DIR"
mkdir -p /var/lib/snapshotmanager/vm-configs
mkdir -p /etc/wireguard

# APP_DIR ist bereits das Script-Verzeichnis, kein Kopieren nötig

# 3. Python-Virtualenv + Dependencies
echo "[3/6] Installiere Python-Abhängigkeiten..."
python3.13 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$APP_DIR/backend/requirements.txt"

# 4. Frontend bauen
echo "[4/6] Baue Frontend..."
cd "$APP_DIR/frontend"
# node_modules von Windows entfernen (fehlende Linux-Ausführungsrechte)
rm -rf node_modules
npm install --silent
# npx statt npm run build → umgeht Permission-Probleme mit .bin/vite
npx vite build
cd "$APP_DIR"

# 5. Service-User anlegen (kein Login, kein Passwort)
echo "[5/6] Richte Systemd-Service ein..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# Berechtigungen setzen
chown -R root:root "$APP_DIR"
chown -R root:root /var/lib/snapshotmanager

# Service-Datei dynamisch mit korrektem Pfad generieren
cat > /etc/systemd/system/snapshotmanager.service << EOF
[Unit]
Description=SnapshotManager - Proxmox ZFS Backup Manager
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR/backend
ExecStart=$APP_DIR/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
NoNewPrivileges=no
PrivateTmp=false

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable snapshotmanager

# 6. Starten
echo "[6/6] Starte Service..."
systemctl start snapshotmanager

echo ""
echo "=== Installation abgeschlossen! ==="
echo ""
echo "  Web-GUI:    http://$(hostname -I | awk '{print $1}'):8000"
echo "  Logs:       journalctl -u snapshotmanager -f"
echo "  Neustart:   systemctl restart snapshotmanager"
echo ""
echo "Hinweis: ZFS und WireGuard benötigen root-Rechte."
echo "Der Service läuft als root (siehe snapshotmanager.service)."
