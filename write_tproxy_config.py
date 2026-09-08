#!/usr/bin/env python3
import json
import os
import stat

# Секрет MTProxy берётся из переменной окружения MTPROXY_SECRET (не хранится в репозитории).
SECRET = os.environ["MTPROXY_SECRET"]
profiles = {"profiles": [
    {
        "name": "default",
        "secret": SECRET,
        "backend": "127.0.0.1:2398",
        "carrier_mode": "https"
    }
]}

config = {
    "public_hostname": "max.evgdan.ru",
    "listen": "127.0.0.1:8080",
    "admin_listen": "127.0.0.1:8081",
    "public_upstream": "http://127.0.0.1:8000",
    "static_routes": "exact",
    "token_key_file": "/etc/tproxy-server/token.key",
    "profiles_file": "/run/credentials/tproxy-server.service/profiles.json",
    "enable_pprof": False,
}

# Split long lines for readability; python json compact, then wrap.
config_text = json.dumps(config, indent=2)
profiles_text = json.dumps(profiles, indent=2)


def write(path, text, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(path, mode)


write("/etc/tproxy-server/config.json", config_text + "\n", 0o640)
write("/etc/tproxy-server/profiles.json", profiles_text + "\n", 0o400)

print("wrote /etc/tproxy-server/config.json")
print("wrote /etc/tproxy-server/profiles.json")
print("--- config ---")
print(config_text)
print("--- profiles ---")
print(profiles_text)
print("--- perms ---")
os.system("stat -c '%a %U:%G %n' /etc/tproxy-server/config.json /etc/tproxy-server/profiles.json")