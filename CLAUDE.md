# Fujin Development Guide

## Build/Test/Lint Commands
- Format code: `just fmt`
- Lint code: `just lint` (includes mypy for type checking)
- Serve documentation: `just docs-serve`
- Update doc requirements: `just docs-requirements`
- Build binary: `just build-bin`
- Bump version: `just bumpver VERSION`

## Code Style Guidelines
- **Formatting**: Black-compatible, 88 char line limit, double quotes
- **Imports**: Standard library first, then third-party, then local
- **Types**: Use type annotations everywhere
- **Classes**: Prefer dataclasses for structured data
- **Error handling**: Use custom error classes from `errors.py`
- **CLI output**: Use rich library for formatted output
- **Documentation**: Include docstrings for public functions/classes
- **Python target**: 3.12+

## Project Structure
- Command-based CLI app with commands in `src/fujin/commands/`
- Configuration via TOML files using msgspec
- Integration with Systemd, proxies (Caddy/Nginx), and secrets management