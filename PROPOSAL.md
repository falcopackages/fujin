# Refactoring Proposal: Ejectable Defaults & Configuration Management

This document outlines a proposal to refactor `fujin` to adopt an "ejectable defaults" philosophy, simplifying configuration management and improving transparency.

## 1. Core Philosophy (Exposed Configuration)

Currently, `fujin` abstracts away much of the underlying configuration (Systemd units, Caddy routes) within its Python codebase. While this makes getting started easy, it hides complexity and makes customization difficult.

**The new philosophy:** `fujin` should expose all configurations by default. There are no "internal defaults" hidden from the user at deploy time. When you initialize a project, `fujin` scaffolds the necessary configuration files (Systemd units, Caddyfile) directly into your project directory. You own these files from day one.

## 2. The "Exposed by Default" Pattern

Instead of an "eject" command, the `fujin init` command will generate a `config/` (or `.fujin/`) directory containing:
- `fujin.toml` (High-level metadata)
- `Caddyfile` (Web server config snippet)
- `systemd/` (Service and socket units)

**Deployment:** The `fujin deploy` command will **always** read these local files, render any necessary variables (like paths), and upload them to the server. This eliminates the ambiguity of "am I using the default or my local override?".

## 3. Caddy: File-Based Imports

The user noted that Caddy typically loads configuration from a single file. However, Caddy supports the `import` directive, which allows including other files or glob patterns.

**Proposed Strategy:**
- **Server Setup:** We will ensure the main Caddy instance on the server (e.g., `/etc/caddy/Caddyfile`) includes a line like `import /etc/caddy/conf.d/*.caddy`.
- **App Config:** `fujin` will generate a `Caddyfile` snippet for your app locally.
- **Deployment:** `fujin` uploads this snippet to `/etc/caddy/conf.d/<app>.caddy` on the server and reloads Caddy.
- **Benefit:** This allows multiple `fujin` apps (or other services) to coexist on the same server without fighting over the main Caddyfile.

## 4. Removing "Dummy" Proxy

The `Dummy` proxy (`src/fujin/proxies/dummy.py`) serves as a no-op implementation. This abstraction is likely unnecessary and can be removed.

- If a user does not require a reverse proxy (e.g., they are exposing the service directly or using an external load balancer), this should be handled by the core deployment logic (e.g., "no proxy" mode) rather than a fake proxy class.
- This simplifies the `proxies` module and removes dead code.

## 5. Configuration Architecture & Templating

To avoid confusion about where configuration lives (in `fujin.toml` vs. local templates), we establish a clear separation of concerns:

### A. `fujin.toml`: The Source of Truth (Data)
This file defines the **variables** and **metadata** specific to your application deployment. It is the single source of truth for values that are shared across multiple templates or required by the deployment logic itself.

*   **`app`**: The application name (used for service naming, paths).
*   **`host.domain_name`**: The domain (used in Caddyfile).
*   **`webserver.upstream`**: The socket or port (used in *both* Caddyfile and Systemd units).
*   **`processes`**: A dictionary of process names to commands.
    *   *Key*: Determines the service name (e.g., `web` -> `myapp.service`, `worker` -> `myapp-worker.service`).
    *   *Value*: The command string passed to the Systemd template.

### B. `.fujin/`: The Structure (Templates)
The files in `.fujin/` are **templates**. They define the *structure* of your configuration. They contain placeholders that `fujin` replaces at deploy time using data from `fujin.toml`.

#### 1. `.fujin/Caddyfile`
*   **Default Content:**
    ```caddy
    {domain_name} {{
        reverse_proxy {upstream}
    }}
    ```
*   **Variables Available:** `{domain_name}`, `{upstream}`, `{app_name}`.

#### 2. `.fujin/systemd/` (Service Templates)
This directory contains Jinja2 templates for Systemd units.

*   **`web.service.j2`**: Template for the main web process.
*   **`default.service.j2`**: The fallback template for any process that doesn't have a specific template.
*   **`socket.service.j2`**: Template for socket activation units.

**Enhanced Process Configuration:**
To support advanced features like socket activation per-process, we will upgrade the `processes` configuration in `fujin.toml` to use dictionaries for all entries. This ensures consistency and simplifies parsing.

```toml
[processes]
# Simple case (uses default.service.j2)
worker = { command = "celery -A myapp worker" }

# Advanced case (uses web.service.j2 + socket activation)
web = { command = "gunicorn myapp.wsgi:application", socket = true }
```

**Jinja2 Templating:**
We will switch to **Jinja2** for rendering. This allows logic within the templates, making them much more powerful.

*   **Example `web.service.j2`:**
    ```ini
    [Unit]
    Description={{ app_name }} {{ process_name }}
    {% if process.socket %}
    Requires={{ app_name }}-{{ process_name }}.socket
    {% endif %}

    [Service]
    ExecStart={{ app_dir }}/{{ process.command }}
    ...
    ```

**Rendering Logic with Jinja2:**
1.  **Iterate Processes:** For each process defined in `fujin.toml`:
2.  **Select Template:**
    *   Check for `<process_name>.service.j2` (e.g., `web.service.j2`).
    *   If not found, use `default.service.j2`.
3.  **Render:** Pass the full context (app config + specific process config) to Jinja2.
4.  **Socket Activation:** If `socket = true` is set for a process:
    *   Render `socket.service.j2` (or `<process_name>.socket.j2` if it exists) as `<app_name>-<process_name>.socket`.
    *   Ensure the main service unit depends on this socket (handled via Jinja2 logic as shown above).

This approach gives us:
*   **Consistency:** All processes are defined in the same way.
*   **Flexibility:** Complex needs (sockets, custom templates) are supported via the same structure.
*   **Power:** Jinja2 allows conditional logic in templates (e.g., "only add this flag if X is true").

### C. Renaming `fujin.toml`
To avoid the redundancy of `fujin.toml` inside a project that might also have a `.fujin` folder, and to align with modern tools, we will rename the configuration file to **`fujin.config.toml`** (or simply keep it at the root as `fujin.toml` while the templates live in `.fujin/`).

*Decision:* We will keep **`fujin.toml` at the project root** (standard practice for tools like `pyproject.toml`, `cargo.toml`). The `.fujin/` folder is strictly for *configuration assets* (templates), similar to how `.github/` holds workflows.

### D. Rendering Logic
At deployment time (`fujin deploy`), the workflow is:
1.  **Read Data:** Load `fujin.toml`.
2.  **Read Templates:** Load files from `.fujin/`.
3.  **Render:** Replace placeholders in the templates with data from `fujin.toml`.
    *   *Note:* If a template does not contain a placeholder (e.g., user removed `{upstream}` from Caddyfile), `fujin` simply uses the text as-is.
4.  **Upload:** Write the rendered content to the server.

This ensures that `fujin.toml` remains the central place for *values* (like "what port?" or "what domain?"), while `.fujin/` files control the *implementation details* (like "how to proxy?" or "how to restart?").

## 6. Summary of Workflow Changes

The user workflow will evolve to support these changes:

1.  **`fujin init`**: (Unchanged) Sets up the basic `fujin.toml`.
2.  **`fujin eject` (New)**: Optional command. Copies default Systemd and Caddy templates to the local project for customization.
3.  **`fujin deploy`**:
    - Checks for local templates.
    - Renders templates (local or default) with current config variables.
    - Uploads rendered configs to the server (e.g., `/etc/systemd/system/`, `/etc/caddy/conf.d/`).
    - Reloads daemons (Systemd, Caddy).

This refactoring will make `fujin` more robust, transparent, and developer-friendly.
