from __future__ import annotations

import os
from pathlib import Path

import msgspec

from fujin.config import Config
from fujin.connection import Connection

CERTBOT_EMAIL = os.getenv("CERTBOT_EMAIL")


# TODO: this is a wip


class WebProxy(msgspec.Struct):
    conn: Connection
    domain_name: str
    app_name: str
    upstream: str
    local_config_dir: Path

    @property
    def config_file(self) -> Path:
        return self.local_config_dir / f"{self.app_name}.conf"

    @classmethod
    def create(cls, config: Config, conn: Connection) -> WebProxy:
        return cls(
            conn=conn,
            domain_name=config.host.domain_name,
            upstream=config.webserver.upstream,
            app_name=config.app_name,
            local_config_dir=config.local_config_dir,
        )

    def install(self):
        # TODO: won"t always install the latest version, install certbot with uv ?
        # https://certbot.eff.org/instructions?ws=nginx&os=pip
        self.conn.run(
            "sudo apt install -y nginx libpq-dev python3-dev python3-certbot-nginx"
        )

    def uninstall(self):
        pass

    def setup(self):
        # TODO should not be running all this everytime
        conf = (
            self.config_file.read_text()
            if self.config_file.exists()
            else self._get_config()
        )
        self.conn.run(
            f"sudo echo '{conf}' | sudo tee /etc/nginx/sites-available/{self.app_name}.conf",
            hide="out",
            pty=True,
        )
        self.conn.run(
            f"sudo ln -sf /etc/nginx/sites-available/{self.app_name}.conf /etc/nginx/sites-enabled/{self.app_name}.conf",
            pty=True,
        )
        self.conn.run("sudo systemctl restart nginx", pty=True)
        self.conn.run(
            f"certbot --nginx -d {self.domain_name} --non-interactive --agree-tos --email {CERTBOT_EMAIL} --redirect"
        )
        # Updating local Nginx configuration
        self.conn.get(
            f"/etc/nginx/sites-available/{self.app_name}.conf",
            str(self.config_file),
        )
        # Enabling certificate auto-renewal
        self.conn.run("sudo systemctl enable certbot.timer", pty=True)
        self.conn.run("sudo systemctl start certbot.timer", pty=True)

    def teardown(self):
        pass

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def status(self) -> None: ...

    def restart(self) -> None: ...

    def logs(self) -> None: ...

    def export_config(self) -> None:
        self.config_file.write_text(self._get_config())

    def _get_config(self) -> str:
        return f"""None
server {{
   listen 80;
   server_name {self.domain_name};

   location / {{
      proxy_pass {self.upstream};
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
   }}
}}

"""
