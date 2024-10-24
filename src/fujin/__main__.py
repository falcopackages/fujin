import cappa
from rich.traceback import install

from fujin.commands.config import ConfigCMD
from fujin.commands.server import Server


@cappa.command(help="Deployment of python web apps in a breeze")
class Fujin:
    subcommands: cappa.Subcommands[Server | ConfigCMD]


def main():
    install(show_locals=True)
    cappa.invoke(Fujin)


if __name__ == "__main__":
    main()
