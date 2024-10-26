import json

import msgspec

from fujin.config import Config
from fujin.host import Host


class WebProxy(msgspec.Struct):
    host: Host
    config: Config

    def install(self):
        self.host.run_uv("tool install caddy-bin")
        self.host.run(f"/home/{self.host.config.user}/.local/bin/caddy start", pty=True)

    def setup(self):
        with self.host.cd_project_dir(self.config.app):
            self.host.run(f"echo '{json.dumps(self._generate_config())}' > caddy.json")
            self.host.run(
                f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
            )

    def teardown(self):
        empty_config = {"apps": {"http": {"servers": {self.config.app: {}}}}}
        self.host.run(f"echo '{json.dumps(empty_config)}' > caddy.json")
        self.host.run(
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
                                    "match": [{"host": [self.host.config.domain_name]}],
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
