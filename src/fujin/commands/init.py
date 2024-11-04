from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cappa
import tomli_w

from fujin.commands import BaseCommand
from fujin.config import tomllib


@cappa.command(help="Generate a sample configuration file")
class Init(BaseCommand):
    profile: Annotated[
        str, cappa.Arg(choices=["simple", "falco"], short="-p", long="--profile")
    ] = "simple"

    def __call__(self):
        fujin_toml = Path("fujin.toml")
        if fujin_toml.exists():
            raise cappa.Exit("fujin.toml file already exists", code=1)
        profile_to_func = {"simple": simple_config, "falco": falco_config}
        app_name = Path().resolve().stem.replace("-", "_").replace(" ", "_").lower()
        config = profile_to_func[self.profile](app_name)
        if not Path(".python-version").exists():
            config["python_version"] = "3.12"
        pyproject_toml = Path("pyproject.toml")
        if pyproject_toml.exists():
            pyproject = tomllib.loads(pyproject_toml.read_text())
            config["app"] = pyproject.get("project", {}).get("name", app_name)
            if pyproject.get("project", {}).get("version"):
                # fujin will read the version itself from the pyproject
                config.pop("version")
        fujin_toml.write_text(tomli_w.dumps(config))
        self.stdout.output(
            "[green]Sample configuration file generated successfully![/green]"
        )


def simple_config(app_name) -> dict:
    return {
        "app": app_name,
        "version": "0.1.0",
        "build_command": "uv build && uv pip compile pyproject.toml -o requirements.txt",
        "distfile": f"dist/{app_name}-{{version}}-py3-none-any.whl",
        "webserver": {
            "upstream": "localhost:8000",
            "type": "fujin.proxies.caddy",
        },
        "release_command": f"{app_name} migrate",
        "processes": {
            "web": f".venv/bin/gunicorn {app_name}.wsgi:application --bind 0.0.0.0:8000"
        },
        "aliases": {"shell": "server exec --appenv -i bash"},
        "host": {
            "ip": "127.0.0.1",
            "user": "root",
            "domain_name": f"{app_name}.com",
            "envfile": ".env.prod",
        },
    }


def falco_config(app_name: str) -> dict:
    config = simple_config(app_name)
    config.update(
        {
            "release_command": f"{config['app']} setup",
            "processes": {
                "web": f".venv/bin/{config['app']} prodserver",
                "worker": f".venv/bin/{config['app']} qcluster",
            },
            "aliases": {
                "console": "app exec -i shell_plus",
                "dbconsole": "app exec -i dbshell",
                "print_settings": "app exec print_settings --format=pprint",
                "shell": "server exec --appenv -i bash",
            },
        }
    )
    return config
