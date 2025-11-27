Configuration
=============

Fujin uses a **fujin.toml** file at the root of your project for configuration. Below are all available configuration options.

app
---
The name of your project or application. Must be a valid Python package name.

version
--------
The version of your project to build and deploy. If not specified, automatically parsed from **pyproject.toml** under *project.version*.

python_version
--------------
The Python version for your virtualenv. If not specified, automatically parsed from **.python-version** file. This is only
required if the installation mode is set to **python-package**

requirements
------------
Optional path to your requirements file. This will only be used when the installation mode is set to *python-package*

versions_to_keep
----------------
The number of versions to keep on the host. After each deploy, older versions are pruned based on this setting. By default, it keeps the latest 5 versions,
set this to `None` to never automatically prune.

build_command
-------------
The command to use to build your project's distribution file.

distfile
--------
Path to your project's distribution file. This should be the main artifact containing everything needed to run your project on the server.
Supports version placeholder, e.g., **dist/app_name-{version}-py3-none-any.whl**

installation_mode
-----------------

Indicates whether the *distfile* is a Python package or a self-contained executable. The possible values are *python-package* and *binary*.
The *binary* option disables specific Python-related features, such as virtual environment creation and requirements installation. ``fujin`` will assume the provided
*distfile* already contains all the necessary dependencies to run your program.

release_command
---------------
Optional command to run at the end of deployment (e.g., database migrations) before your application is started.

secrets
-------

Optional secrets configuration. If set, ``fujin`` will load secrets from the specified secret management service.
Check out the `secrets </secrets.html>`_ page for more information.

adapter
~~~~~~~
The secret management service to use. The currently available options are *bitwarden*, *1password*, *doppler*

password_env
~~~~~~~~~~~~
Environment variable containing the password for the service account. This is only required for certain adapters.

Webserver
---------

Caddy web server configurations.

upstream
~~~~~~~~
The address where your web application listens for requests. Supports any value compatible with your chosen web proxy:

- HTTP address (e.g., *localhost:8000* )
- Unix socket caddy (e.g., *unix//run/project.sock* )

config_dir
~~~~~~~~~~
The directory where the Caddyfile for the project will be stored on the host. Default: **/etc/caddy/conf.d/**

statics
~~~~~~~

Defines the mapping of URL paths to local directories for serving static files. The directories you map should be accessible by caddy, meaning
with read permissions for the *www-data* group; a reliable choice is **/var/www**.

Example:

.. code-block:: toml
    :caption: fujin.toml

    [webserver]
    upstream = "unix//run/project.sock"
    statics = { "/static/*" = "/var/www/myproject/static/" }

processes
---------

A mapping of process names to commands that will be managed by the process manager. Define as many processes as needed, but
when using any proxy other than *fujin.proxies.dummy*, a *web* process must be declared.

Example:

.. code-block:: toml
    :caption: fujin.toml

    [processes]
    web = ".venv/bin/gunicorn myproject.wsgi:application"


.. note::

    Commands are relative to your *app_dir*. When generating systemd service files, the full path is automatically constructed.
    Refer to the *apps_dir* setting on the host to understand how *app_dir* is determined.
    Here are the templates for the service files:

    - `web.service <https://github.com/falcopackages/fujin/blob/main/src/fujin/templates/web.service>`_
    - `web.socket <https://github.com/falcopackages/fujin/blob/main/src/fujin/templates/web.socket>`_
    - `simple.service <https://github.com/falcopackages/fujin/blob/main/src/fujin/templates/simple.service>`_ (for all additional processes)

Host Configuration
-------------------

ip
~~
The IP address or anything that resolves to the remote host IP's. This is use to communicate via ssh with the server, if omitted it's value will default to the one of the *domain_name*.

domain_name
~~~~~~~~~~~
The domain name pointing to this host. Used for web proxy configuration.

user
~~~~
The login user for running remote tasks. Should have passwordless sudo access for optimal operation.

.. note::

    You can create a user with these requirements using the ``fujin server create-user`` command.

envfile
~~~~~~~
Path to the production environment file that will be copied to the host.

env
~~~
A string containing the production environment variables. In combination with the secrets manager, this is most useful when
you want to automate deployment through a CI/CD platform like GitLab CI or GitHub Actions. For an example of how to do this,
check out the `integrations guide </integrations.html>`_

.. important::

    *envfile* and *env* are mutually exclusive—you can define only one.

apps_dir
~~~~~~~~

Base directory for project storage on the host. Path is relative to user's home directory.
Default: **.local/share/fujin**. This value determines your project's **app_dir**, which is **{apps_dir}/{app}**.

password_env
~~~~~~~~~~~~

Environment variable containing the user's password. Only needed if the user cannot run sudo without a password.

ssh_port
~~~~~~~~

SSH port for connecting to the host. Default to **22**.

key_filename
~~~~~~~~~~~~

Path to the SSH private key file for authentication. Optional if using your system's default key location.

aliases
-------

A mapping of shortcut names to Fujin commands. Allows you to create convenient shortcuts for commonly used commands.

Example:

.. code-block:: toml
    :caption: fujin.toml

    [aliases]
    console = "app exec -i shell_plus" # open an interactive django shell
    dbconsole = "app exec -i dbshell" # open an interactive django database shell
    shell = "server exec --appenv -i bash" # SSH into the project directory with environment variables loaded


Example
-------

This is a minimal working example.

.. tab-set::

    .. tab-item:: python package

        .. exec_code::
            :language_output: toml

            # --- hide: start ---
            from fujin.commands.init import simple_config
            from tomli_w import dumps

            print(dumps(simple_config("bookstore"),  multiline_strings=True))
            #hide:toggle

    .. tab-item:: binary mode

        .. exec_code::
            :language_output: toml

            # --- hide: start ---
            from fujin.commands.init import binary_config
            from tomli_w import dumps

            print(dumps(binary_config("bookstore"),  multiline_strings=True))
            #hide:toggle
