import cappa

@cappa.command(help="Deploy project")
class Deploy:
    """
    run build command
    move wheel file and requirements to server
    create and override .env file
    add .python-version file
    sync requirements with uv (will create .venv)
    install wheel file project file
    generate services files and ovewritte existing ones
    reload systemd daoemin
    enable socket
    start / or restart all services
    generate caddy config and update caddy

    if code changes only, skip caddy, services files generation, socket enabling and daemon reload
    """