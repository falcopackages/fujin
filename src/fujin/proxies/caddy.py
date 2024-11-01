from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import ClassVar

import msgspec

from fujin.config import Config
from fujin.config import HostConfig
from fujin.connection import Connection

DEFAULT_VERSION = "2.8.4"
GH_TAR_FILENAME = "caddy_{version}_linux_amd64.tar.gz"
GH_DOWNL0AD_URL = (
        "https://github.com/caddyserver/caddy/releases/download/v{version}/"
        + GH_TAR_FILENAME
)
GH_RELEASE_LATEST_URL = "https://api.github.com/repos/caddyserver/caddy/releases/latest"


class WebProxy(msgspec.Struct):
    conn: Connection
    domain_name: str
    app_name: str
    upstream: str
    config_file: ClassVar[Path] = Path(".fujin/caddy.json")

    @classmethod
    def create(
            cls, config: Config, host_config: HostConfig, conn: Connection
    ) -> WebProxy:
        return cls(
            conn=conn,
            domain_name=host_config.domain_name,
            upstream=config.webserver.upstream,
            app_name=config.app_name,
        )

    def run_pty(self, *args, **kwargs):
        return self.conn.run(*args, **kwargs, pty=True)

    def install(self):
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
        self.conn.run(
            f"echo '{systemd_service}' | sudo tee /etc/systemd/system/caddy-api.service",
            hide="out",
            pty=True,
        )
        self.run_pty("sudo systemctl daemon-reload")
        self.run_pty("sudo systemctl enable --now caddy-api")

    def uninstall(self):
        self.stop()
        self.run_pty("sudo systemctl disable caddy-api")
        self.run_pty("sudo rm /usr/bin/caddy")
        self.run_pty("sudo rm /etc/systemd/system/caddy-api.service")
        self.run_pty("sudo userdel caddy")
        self.run_pty("sudo groupdel caddy")

    def setup(self):
        config = json.loads(self.config_file.read_text()) if self.config_file.exists() else self._get_config()
        self.conn.run(f"echo '{json.dumps(config)}' > caddy.json")
        self.conn.run(
            f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
        )
        # TODO: stop when received an {"error":"loading config: loading new config: http app module: start: listening on :443: listen tcp :443: bind: permission denied"}, not a 200 ok

    def teardown(self):
        empty_config = {"apps": {"http": {"servers": {self.app_name: {}}}}}
        self.conn.run(f"echo '{json.dumps(empty_config)}' > caddy.json")
        self.conn.run(
            f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
        )

    def start(self) -> None:
        self.run_pty("sudo systemctl start caddy-api")

    def stop(self) -> None:
        self.run_pty("sudo systemctl stop caddy-api")

    def status(self) -> None:
        self.run_pty("sudo systemctl status caddy-api", warn=True)

    def restart(self) -> None:
        self.run_pty("sudo systemctl restart caddy-api")

    def logs(self) -> None:
        self.run_pty(f"sudo journalctl -u caddy-api -f", warn=True)

    def export_config(self) -> None:
        self.config_file.write_text(json.dumps(self._get_config()))

    def _get_config(self) -> dict:
        return {
            "apps": {
                "http": {
                    "servers": {
                        self.app_name: {
                            "listen": [":443"],
                            "routes": [
                                {
                                    "match": [{"host": [self.domain_name]}],
                                    "handle": [
                                        {
                                            "handler": "reverse_proxy",
                                            "upstreams": [{"dial": self.upstream}],
                                        }
                                    ],
                                }
                            ],
                        }
                    }
                }
            }
        }


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
# caddy-api.service
#
# For using Caddy with its API.
#
# This unit is "durable" in that it will automatically resume
# the last active configuration if the service is restarted.
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
Group=www-data
ExecStart=/usr/bin/caddy run --environ --resume
TimeoutStopSec=5s
LimitNOFILE=1048576
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
"""
