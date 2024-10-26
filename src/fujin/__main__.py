import sys
from pathlib import Path

import cappa

from fujin.commands.app import App
from fujin.commands.config import ConfigCMD
from fujin.commands.deploy import Deploy
from fujin.commands.down import Down
from fujin.commands.redeploy import Redeploy
from fujin.commands.server import Server
from fujin.commands.up import Up

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@cappa.command(help="Deployment of python web apps in a breeze :)")
class Fujin:
    subcommands: cappa.Subcommands[
        Up | Deploy | Redeploy | App | Server | ConfigCMD | Down
    ]


def main():
    # install(show_locals=True)
    alias_cmd = _parse_aliases()
    if alias_cmd:
        cappa.invoke(Fujin, argv=alias_cmd)
    else:
        cappa.invoke(Fujin)


def _parse_aliases() -> list[str] | None:
    fujin_toml = Path("fujin.toml")
    if not fujin_toml.exists():
        return
    data = tomllib.loads(fujin_toml.read_text())
    aliases = data.get("aliases")
    if not aliases:
        return
    if len(sys.argv) == 1:
        return
    if sys.argv[1] not in aliases:
        return
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else []
    return [*aliases.get(sys.argv[1]).split(), *extra_args]


if __name__ == "__main__":
    main()
