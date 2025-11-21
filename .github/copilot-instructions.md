# Fujin AI Coding Instructions

## Project Overview

Fujin is a CLI deployment tool for Python and binary applications, similar to Capistrano or Dokku but simpler. It automates deployment to a VPS using **systemd** for process management and **Caddy** (default) or Nginx as a reverse proxy.

- **Core Stack**: Python 3.10+, `cappa` (CLI), `fabric` (SSH), `msgspec` (Config/Serialization), `jinja2` (Templates).
- **Build System**: `hatchling` with `uv` for dependency management.
- **Task Runner**: `just`.

## Architecture & Core Concepts

### CLI Structure

- Built with **Cappa**. Entry point is `src/fujin/__main__.py`.
- Commands are defined in `src/fujin/commands/`.
- `Deploy` command (`src/fujin/commands/deploy.py`) orchestrates the main deployment flow.

### Configuration (`fujin.toml`)

- Configuration is defined in `fujin.toml` and parsed into `msgspec.Struct` objects in `src/fujin/config.py`.
- Key sections: `[app]`, `[host]`, `[processes]`, `[webserver]`.
- **Pattern**: Use `msgspec.Struct` with `kw_only=True` for configuration classes.

### Deployment Flow

1.  **Build**: Runs `build_command` locally.
2.  **Connect**: Establishes SSH connection via `fabric`.
3.  **Transfer**: Uploads distribution file (wheel/binary) and requirements.
4.  **Install**:
    - For Python packages: Uses `uv` on the remote server to create venv and install dependencies.
    - For Binaries: Symlinks the binary.
5.  **Configure**: Generates systemd units and Caddyfile from Jinja2 templates (`src/fujin/templates/`).
6.  **Restart**: Reloads systemd and restarts services.

### Remote Execution

- Uses `fabric` (wrapped in `src/fujin/connection.py`).
- **Pattern**: Use `conn.run(cmd, pty=True)` for commands that need output streaming or sudo.
- **Environment**: A `.appenv` file is generated on the server to source environment variables.

## Development Workflow

### Task Runner (`just`)

Use `just` for all common tasks. Do not run `pytest` or `uv` directly if a `just` command exists.

- `just run [cmd]`: Run command in dev environment.
- `just test`: Run unit tests.
- `just fmt`: Format code (ruff).
- `just lint`: Lint code (mypy).
- `just recreate-vm`: Rebuild the Vagrant VM for testing.
- `just ssh`: SSH into the Vagrant VM.
- `just fujin [args]`: Run fujin against the `examples/django/bookstore` project.

### Testing

- **Unit Tests**: Located in `tests/`.
- **Integration**: The `examples/django/bookstore` project is used for manual/integration testing against the Vagrant VM.
- **Vagrant**: Used to simulate a remote VPS. Ensure the VM is running (`just recreate-vm`) when testing deployment logic.

## Code Conventions

- **Typing**: Strong typing with `msgspec` structs for data models.
- **CLI**: Use `cappa` decorators (`@cappa.command`, `@cappa.arg`).
- **Async/Concurrency**: Uses `gevent` for parallel remote execution (e.g., restarting multiple services).
- **Templates**: Systemd and Proxy configs are Jinja2 templates. When adding new service types, add corresponding `.j2` files in `src/fujin/templates/`.
- **Path Handling**: Use `pathlib.Path` over `os.path`.

## Key Files

- `src/fujin/config.py`: Configuration schema definition.
- `src/fujin/commands/deploy.py`: Main deployment logic.
- `src/fujin/templates/`: Jinja2 templates for systemd/Caddy.
- `examples/django/bookstore/fujin.toml`: Reference configuration.
