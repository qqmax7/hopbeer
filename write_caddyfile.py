#!/usr/bin/env python3
import os

caddyfile = r"""{
	email admin@evgdan.ru
	admin off
	servers {
		protocols h1 h2
		timeouts {
			read_header 10s
			read_body 60s
		}
	}
}

max.evgdan.ru {
	encode zstd gzip
	header {
		-Via
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
	}
	handle /media/* {
		root * /opt/hopbeer
		file_server
	}
	reverse_proxy 127.0.0.1:8080 {
		transport http {
			response_header_timeout 40s
		}
	}
	handle_errors {
		header {
			Cache-Control "no-store"
			Strict-Transport-Security "max-age=31536000; includeSubDomains"
		}
		respond "{http.error.status_code} {http.error.status_text}" {http.error.status_code}
	}
}

www.max.evgdan.ru {
	redir https://max.evgdan.ru{uri} permanent
}
"""

with open("/etc/caddy/Caddyfile", "w") as f:
    f.write(caddyfile)
    f.flush()
    os.fsync(f.fileno())
os.chmod("/etc/caddy/Caddyfile", 0o644)
print("wrote /etc/caddy/Caddyfile")
print(open("/etc/caddy/Caddyfile").read())