import json

import msgspec
from fabric import Connection

from fujin.config import Config


class WebProxy(msgspec.Struct):
    conn: Connection
    domain_name: str
    config: Config

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
        empty_config = {"apps": {"http": {"servers": {self.config.app: {}}}}}
        self.conn.run(f"echo '{json.dumps(empty_config)}' > caddy.json")
        self.conn.run(
            f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
        )

    def _generate_config(self) -> dict:
        return {
            "apps": {
                "http": {
                    "servers": {
                        self.config.app: {
                            "listen": [":443"],
                            "routes": [
                                {
                                    "match": [{"host": [self.domain_name]}],
                                    "handle": [
                                        {
                                            "handler": "reverse_proxy",
                                            "upstreams": [
                                                {"dial": self.config.webserver.upstream}
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
