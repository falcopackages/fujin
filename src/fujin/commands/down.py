import cappa

from fujin.commands.base import HostCommand


@cappa.command(help="Remove application configuration, files, and stop application services")
class Down(HostCommand):
    """
    ask double confirmation
    Run everything necessary to deploy app on a fresh server
    remove project dir
    stop all services
    delete all services files
    """
