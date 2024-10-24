import cappa

@cappa.command(help="Set")
class Up:
    """
    Run everything necessary to deploy app on a fresh server
    create project dir
    host.connection.run(f"mkdir -p {host.project_dir}")
    bootstrap
    deploy
    """