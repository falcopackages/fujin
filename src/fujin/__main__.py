import cappa
from rich.traceback import install

from fujin.commands.config import ConfigCMD
from fujin.commands.server import Server
from fujin.commands.deploy import Deploy
from fujin.commands.redeploy import Redeploy
from fujin.commands.up import Up


@cappa.command(help="Deployment of python web apps in a breeze")
class Fujin:
    subcommands: cappa.Subcommands[Up | Deploy | Redeploy | Server | ConfigCMD]


def main():
    install(show_locals=True)
    cappa.invoke(Fujin)


if __name__ == "__main__":
    main()
