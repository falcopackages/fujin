import cappa
from rich.traceback import install

from fujin.commands.show_config import ShowConfig
from fujin.config import Config


@cappa.command(help="Deployment of python web apps in a breeze")
class Fujin:
    subcommands: cappa.Subcommands[ShowConfig]


def main():
    install(show_locals=True)
    Config.read()
    cappa.invoke(Fujin)


if __name__ == "__main__":
    main()
