import msgspec

from fujin.config import Config
from fujin.host import Host

CERTBOT_EMAIL = ""

# TODO: this is a wip


class WebProxy(msgspec.Struct):
    host: Host
    config: Config

    def install(self):
        # TODO: won"t always install the latest version, install certbot with uv ?
        self.host.sudo(
            "apt install -y nginx libpq-dev python3-dev python3-certbot-nginx sqlite3"
        )

    def setup(self):
        self.host.sudo(
            f"echo '{self._get_config()}' | sudo tee /etc/nginx/sites-available/{self.config.app}",
            hide="out",
        )
        self.host.sudo(
            f"ln -sf /etc/nginx/sites-available/{self.config.app} /etc/nginx/sites-enabled/{self.config.app}"
        )
        self.host.sudo(
            f"certbot --nginx -d {self.host.config.domain_name} --non-interactive --agree-tos --email {CERTBOT_EMAIL} --redirect"
        )
        # Updating local Nginx configuration
        self.host.get(
            f"/etc/nginx/sites-available/{self.config.app}",
            f".fujin/{self.config.app}",
        )
        # Enabling certificate auto-renewal
        self.host.sudo("systemctl enable certbot.timer")
        self.host.sudo("systemctl start certbot.timer")

    def teardown(self):
        pass

    def _get_config(self) -> str:
        return f"""
server {{
   listen 80;
   server_name {self.host.config.domain_name};

   location / {{
      proxy_pass {self.config.webserver.upstream};
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
   }}
}}

"""
