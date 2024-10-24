import cappa

@cappa.command(help="Set")
class Up:
    """
    Run everything necessary to deploy app on a fresh server
    create project dir
    bootstrap
    deploy
    """