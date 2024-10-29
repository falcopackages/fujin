from __future__ import annotations

import json

import msgspec
from fujin.connection import Connection

from fujin.config import Config, HostConfig


class WebProxy(msgspec.Struct):
    conn: Connection
    domain_name: str
    app_name: str
    upstream: str

    @classmethod
    def create(cls, config: Config, host_config: HostConfig, conn: Connection) -> WebProxy:
        return cls(
            conn=conn,
            domain_name=host_config.domain_name,
            upstream=config.webserver.upstream,
            app_name=config.app_name,
        )

    def install(self):
        self.conn.run("uv tool install caddy-bin")
        self.conn.run(f"caddy start", pty=True)

    def uninstall(self):
        self.conn.run("caddy stop")
        self.conn.run("uv tool uninstall caddy")

    def setup(self):
        self.conn.run(f"echo '{json.dumps(self._generate_config())}' > caddy.json")
        self.conn.run(
            f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
        )

    def teardown(self):
        empty_config = {"apps": {"http": {"servers": {self.app_name: {}}}}}
        self.conn.run(f"echo '{json.dumps(empty_config)}' > caddy.json")
        self.conn.run(
            f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
        )

    def _generate_config(self) -> dict:
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
                                            "upstreams": [
                                                {"dial": self.upstream}
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    }
                }
            }
        }
