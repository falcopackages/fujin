from __future__ import annotations

import json
import urllib.request

import msgspec
from fujin.config import Config
from fujin.connection import Connection

DEFAULT_VERSION = "2.8.4"
GH_TAR_FILENAME = "caddy_{version}_linux_amd64.tar.gz"
GH_DOWNL0AD_URL = (
    "https://github.com/caddyserver/caddy/releases/download/v{version}/"
    + GH_TAR_FILENAME
)
GH_RELEASE_LATEST_URL = "https://api.github.com/repos/caddyserver/caddy/releases/latest"


class Caddy(msgspec.Struct):
    conn: Connection
    config: Config

    @classmethod
    def create(cls, config: Config, conn: Connection) -> Caddy:
        return cls(conn=conn, config=config)

    def run_pty(self, *args, **kwargs):
        return self.conn.run(*args, **kwargs, pty=True)

    def install(self):
        result = self.conn.run(f"command -v caddy", warn=True, hide=True)
        if result.ok:
            return
        version = get_latest_gh_tag()
        download_url = GH_DOWNL0AD_URL.format(version=version)
        filename = GH_TAR_FILENAME.format(version=version)
        with self.conn.cd("/tmp"):
            self.conn.run(f"curl -O -L {download_url}")
            self.conn.run(f"tar -xzvf {filename}")
            self.run_pty("sudo mv caddy /usr/bin/")
            self.conn.run(f"rm {filename}")
            self.conn.run("rm LICENSE && rm README.md")
        self.run_pty("sudo groupadd --force --system caddy")
        self.conn.run(
            "sudo useradd --system --gid caddy --create-home --home-dir /var/lib/caddy --shell /usr/sbin/nologin --comment 'Caddy web server' caddy",
            pty=True,
            warn=True,
        )

        # Setup directories
        self.run_pty("sudo mkdir -p /etc/caddy/conf.d")
        self.run_pty("sudo chown -R caddy:caddy /etc/caddy")

        # Create main Caddyfile
        main_caddyfile = "import conf.d/*.caddy\n"
        self.conn.run(
            f"echo '{main_caddyfile}' | sudo tee /etc/caddy/Caddyfile",
            hide="out",
            pty=True,
        )

        self.conn.run(
            f"echo '{systemd_service}' | sudo tee /etc/systemd/system/caddy.service",
            hide="out",
            pty=True,
        )
        self.run_pty("sudo systemctl daemon-reload")
        self.run_pty("sudo systemctl enable --now caddy")

    def uninstall(self):
        self.stop()
        self.run_pty("sudo systemctl disable caddy")
        self.run_pty("sudo rm /usr/bin/caddy")
        self.run_pty("sudo rm /etc/systemd/system/caddy.service")
        self.run_pty("sudo userdel caddy")
        self.run_pty("sudo rm -rf /etc/caddy")

    def setup(self):
        rendered_content = self.config.get_caddyfile()

        remote_path = f"/etc/caddy/conf.d/{self.config.app_name}.caddy"
        self.conn.run(
            f"echo '{rendered_content}' | sudo tee {remote_path}",
            hide="out",
            pty=True,
        )
        self.reload()

    def teardown(self):
        remote_path = f"/etc/caddy/conf.d/{self.config.app_name}.caddy"
        self.run_pty(f"sudo rm {remote_path}", warn=True)
        self.reload()

    def start(self) -> None:
        self.run_pty("sudo systemctl start caddy")

    def stop(self) -> None:
        self.run_pty("sudo systemctl stop caddy")

    def status(self) -> None:
        self.run_pty("sudo systemctl status caddy", warn=True)

    def restart(self) -> None:
        self.run_pty("sudo systemctl restart caddy")

    def reload(self) -> None:
        self.run_pty("sudo systemctl reload caddy")

    def logs(self) -> None:
        self.run_pty(f"sudo journalctl -u caddy -f", warn=True)


def get_latest_gh_tag() -> str:
    with urllib.request.urlopen(GH_RELEASE_LATEST_URL) as response:
        if response.status != 200:
            return DEFAULT_VERSION
        try:
            data = json.loads(response.read().decode())
            return data["tag_name"][1:]
        except (KeyError, json.JSONDecodeError):
            return DEFAULT_VERSION


systemd_service = """
# caddy.service
#
# For using Caddy with a config file.
#
# See https://caddyserver.com/docs/install for instructions.

[Unit]
Description=Caddy
Documentation=https://caddyserver.com/docs/
After=network.target network-online.target
Requires=network-online.target

[Service]
Type=notify
User=caddy
Group=caddy
ExecStart=/usr/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/bin/caddy reload --config /etc/caddy/Caddyfile --force
TimeoutStopSec=5s
LimitNOFILE=1048576
LimitNPROC=512
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
"""
