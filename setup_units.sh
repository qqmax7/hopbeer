#!/usr/bin/env bash
set -euo pipefail

# 1. mtproxy.env (root:mtproxy 0640) — MTPROXY_SECRET is the client secret.
#    Секрет берётся из переменной окружения MTPROXY_SECRET (не хранится в репозитории).
cat > /etc/mtproxy/mtproxy.env <<EOF
MTPROXY_SECRET=${MTPROXY_SECRET:?Задайте MTPROXY_SECRET в окружении}
MTPROXY_WORKERS=1
MTPROXY_MAX_CONNECTIONS=4096
EOF
chown root:mtproxy /etc/mtproxy/mtproxy.env
chmod 0640 /etc/mtproxy/mtproxy.env
echo "wrote /etc/mtproxy/mtproxy.env"

# 2. Install systemd units (installed from /opt/tproxy-server/deploy).
install -m 0644 /opt/tproxy-server/deploy/tproxy-server.service /etc/systemd/system/tproxy-server.service
install -m 0644 /opt/tproxy-server/deploy/mtproxy.service /etc/systemd/system/mtproxy.service
install -m 0644 /opt/tproxy-server/deploy/tproxy-firewall.service /etc/systemd/system/tproxy-firewall.service
install -m 0644 /opt/tproxy-server/deploy/refresh-mtproxy-config.service /etc/systemd/system/refresh-mtproxy-config.service
install -m 0644 /opt/tproxy-server/deploy/refresh-mtproxy-config.timer /etc/systemd/system/refresh-mtproxy-config.timer
install -m 0644 /opt/tproxy-server/deploy/firewall.nft /etc/tproxy-server/firewall.nft
install -m 0755 /opt/tproxy-server/deploy/refresh-mtproxy-config.sh /usr/local/sbin/refresh-mtproxy-config
echo "installed units"

# 3. Check relay config again through the real unit credential path as much as possible.
/usr/local/bin/tproxy-server -config /etc/tproxy-server/config.json -profiles-file /etc/tproxy-server/profiles.json -check
echo "relay config valid"

# 4. daemon-reload + enable/start tproxy-firewall first (nftables drops 2398/8888 externally).
systemctl daemon-reload
systemctl enable --now tproxy-firewall.service
echo "firewall enabled"

# 5. Start mtproxy (needs proxy-secret, proxy-multi.conf, mtproxy.env all present).
systemctl enable --now mtproxy.service
systemctl restart mtproxy.service
echo "mtproxy enabled"

# 6. Start tproxy-server (LoadCredential profiles.json from /etc/tproxy-server/profiles.json).
systemctl enable --now tproxy-server.service
systemctl restart tproxy-server.service
echo "tproxy-server enabled"

# 7. Refresh timer (daily re-fetch of mtproxy routing config).
systemctl enable --now refresh-mtproxy-config.timer
echo "refresh timer enabled"

echo "ALL_UNITS_CONFIGURED"