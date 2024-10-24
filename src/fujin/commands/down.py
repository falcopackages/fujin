import cappa

@cappa.command(help="Set")
class Down:
    """
    ask double confirmation
    Run everything necessary to deploy app on a fresh server
    remove project dir
    stop all services
    delete all services files
    """