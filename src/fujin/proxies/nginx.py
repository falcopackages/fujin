import os

import msgspec
from fabric import Connection

from fujin.config import Config

CERTBOT_EMAIL = os.getenv("CERTBOT_EMAIL")


# TODO: this is a wip


class WebProxy(msgspec.Struct):
    conn: Connection
    domain_name: str
    config: Config

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
        self.conn.run(
            f"sudo echo '{self._get_config()}' | sudo tee /etc/nginx/sites-available/{self.config.app}",
            hide="out",
        )
        self.conn.run(
            f"sudo ln -sf /etc/nginx/sites-available/{self.config.app} /etc/nginx/sites-enabled/{self.config.app}"
        )
        self.conn.run("sudo systemctl restart nginx")
        self.conn.run(
            f"certbot --nginx -d {self.domain_name} --non-interactive --agree-tos --email {CERTBOT_EMAIL} --redirect"
        )
        # Updating local Nginx configuration
        self.conn.get(
            f"/etc/nginx/sites-available/{self.config.app}",
            f".fujin/{self.config.app}",
        )
        # Enabling certificate auto-renewal
        self.conn.run("sudo systemctl enable certbot.timer")
        self.conn.run("sudo systemctl start certbot.timer")

    def teardown(self):
        pass

    def _get_config(self) -> str:
        return f"""
server {{
   listen 80;
   server_name {self.domain_name};

   location / {{
      proxy_pass {self.config.webserver.upstream};
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
   }}
}}

"""
