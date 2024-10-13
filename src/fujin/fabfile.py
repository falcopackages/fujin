import os
import secrets

from fabric import Connection
from fabric import task
from falco.fabutils import curl_binary_download_cmd
from falco.fabutils import with_progress

# Configuration
PROJECT_NAME = "torch"
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", default="tobi")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SERVER_USER = "tobi"
SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PASSWORD = os.getenv("SERVER_PASSWORD")
SERVER_PROJECT_DIR = f"/home/{SERVER_USER}/djangoprojects/{PROJECT_NAME}"
SERVER_PROJECT_BINARY = f"{SERVER_PROJECT_DIR}/{PROJECT_NAME}"
DOMAIN = "torch.com"
CERTBOT_EMAIL = "tobidegnon@proton.me"


def get_connection(use_root=False):
    """Establish a connection to the server."""
    user = "root" if use_root else SERVER_USER
    return Connection(host=SERVER_HOST, user=user, connect_kwargs={"password": SERVER_PASSWORD})


# Deployment Tasks


@task
@with_progress("Provisioning server")
def provision(_, set_password=False, progress=None):
    """Set up the server with necessary dependencies and create a new user."""
    conn = get_connection(use_root=True)

    progress("Updating system and installing dependencies")
    conn.sudo("apt update && apt upgrade -y")
    conn.sudo("apt install -y nginx libpq-dev python3-dev python3-certbot-nginx sqlite3")

    progress(f"Creating and configuring user: {SERVER_USER}")
    conn.sudo(f"adduser --disabled-password --gecos '' {SERVER_USER}")
    if set_password:
        password = secrets.token_urlsafe(16)
        conn.sudo(f"echo '{SERVER_USER}:{password}' | chpasswd")
        print(f"Generated password for {SERVER_USER}: {password}")
        print("Please store this password securely and change it upon first login.")

    # Set up SSH and sudo access
    conn.sudo(f"mkdir -p /home/{SERVER_USER}/.ssh")
    conn.sudo(f"cp ~/.ssh/authorized_keys /home/{SERVER_USER}/.ssh/")
    conn.sudo(f"chown -R {SERVER_USER}:{SERVER_USER} /home/{SERVER_USER}/.ssh")
    conn.sudo(f"chmod 700 /home/{SERVER_USER}/.ssh")
    conn.sudo(f"chmod 600 /home/{SERVER_USER}/.ssh/authorized_keys")
    conn.sudo(f"echo '{SERVER_USER} ALL=(ALL) NOPASSWD:ALL' | sudo tee -a /etc/sudoers")

    progress("Creating project directory")
    conn.run(f"mkdir -p {SERVER_PROJECT_DIR}")


@task
@with_progress("Performing initial deployment")
def up(c, progress=None):
    """Perform the initial deployment of the project."""
    conn = get_connection()

    progress("Transferring files to server")
    transfer_files(c)
    conn.sudo(f"ln -sf /etc/nginx/sites-available/{PROJECT_NAME} /etc/nginx/sites-enabled/{PROJECT_NAME}")

    progress("Setting up project and services")
    apprun(c, "setup")
    reload_services(c)
    conn.sudo(f"systemctl enable --now {PROJECT_NAME}.socket")


@task
@with_progress("Deploying code changes")
def deploy(c, progress=None):
    """Deploy code changes to the server."""
    progress("Transferring updated files")
    transfer_files(c, code_only=True)

    progress("Updating project setup")
    apprun(c, "setup")

    progress("Restarting wsgi service")
    get_connection().sudo(f"systemctl restart {PROJECT_NAME}")


# Maintenance Tasks


@task
@with_progress("Refreshing application")
def refresh(c, progress=None):
    """Refresh the application by reloading configurations and restarting services."""
    progress("Updating all files")
    transfer_files(c)

    progress("Reloading configurations and restarting services")
    reload_services(c)


@task
@with_progress("Setting up domain with SSL")
def setup_domain(_, progress=None):
    """Set up a domain with SSL using Certbot."""
    conn = get_connection()

    progress("Obtaining SSL certificate")
    conn.sudo(f"certbot --nginx -d {DOMAIN} --non-interactive --agree-tos --email {CERTBOT_EMAIL} --redirect")

    progress("Updating local Nginx configuration")
    conn.get(
        f"/etc/nginx/sites-available/{PROJECT_NAME}",
        f"deploy/etc/nginx/sites-available/{PROJECT_NAME}",
    )

    progress("Enabling certificate auto-renewal")
    conn.sudo("systemctl enable certbot.timer")
    conn.sudo("systemctl start certbot.timer")


# Utility Tasks


@task
def transfer_files(_, code_only=False):
    """Transfer project files to the server."""
    conn = get_connection()

    # Download and set up binary
    binary_download_cmd = curl_binary_download_cmd(owner=GITHUB_USERNAME, repo=PROJECT_NAME, token=GITHUB_TOKEN)
    conn.run(f"{binary_download_cmd} -o {SERVER_PROJECT_BINARY}")
    conn.run(f"chmod +x {SERVER_PROJECT_BINARY}")
    conn.put(".env.prod", f"{SERVER_PROJECT_DIR}/.env")

    if not code_only:
        # Transfer configuration files
        config_files = [
            (
                f"deploy/etc/nginx/sites-available/{PROJECT_NAME}",
                f"/etc/nginx/sites-available/{PROJECT_NAME}",
            ),
            (
                f"deploy/etc/systemd/system/{PROJECT_NAME}.socket",
                f"/etc/systemd/system/{PROJECT_NAME}.socket",
            ),
            (
                f"deploy/etc/systemd/system/{PROJECT_NAME}.service",
                f"/etc/systemd/system/{PROJECT_NAME}.service",
            ),
        ]
        for src, dest in config_files:
            filename = os.path.basename(src)
            conn.put(src, f"{SERVER_PROJECT_DIR}/{filename}")
            conn.sudo(f"mv {SERVER_PROJECT_DIR}/{filename} {dest}")


@task
def apprun(_, cmd, pty=False):
    """Run a command in the application environment."""
    with get_connection().cd(SERVER_PROJECT_DIR):
        get_connection().run(f"source .env && ./{PROJECT_NAME} '{cmd}'", pty=pty)


@task
def console(c, shell_type="bash"):
    """Open an interactive shell on the server."""
    conn = get_connection()
    if shell_type == "python":
        apprun(c, "manage shell_plus", pty=True)
    elif shell_type == "db":
        apprun(c, "manage dbshell", pty=True)
    else:
        conn.run("bash", pty=True)


@task
def reload_services(_):
    """Reload Nginx and systemd configurations, and restart the project service."""
    conn = get_connection()
    conn.sudo("systemctl daemon-reload")
    conn.sudo("systemctl reload nginx")
    conn.sudo(f"systemctl restart {PROJECT_NAME}")


@task
def logs(_, follow=False):
    """View the last n lines of the project's log file."""
    get_connection().sudo(f"sudo journalctl -u {PROJECT_NAME} -r {'-f' if follow else ''}")


if __name__ == "__main__":
    from fabric.main import Program, Collection

    ns = Collection(
        provision, up, deploy, refresh, setup_domain, transfer_files, apprun, console, reload_services, logs
    )
    program = Program(namespace=ns)
    program.run()
