
Tutorial
========

First make sure you follow the `installation </installation.html>`_ instructions and have the ``fujin`` command available globally in your shell.
``fujin`` allows you to interact with your remote server and your deployed apps from your local shell.


Prerequisites
--------------

.. note::

    In this section I describe stuff that need you to have a project with a ``fujin.toml``, the next two section ``Python package`` and ``Binary`` show how to get one
    so you''l need to read back this section after initslizing the projects.

Linux Box
*********

``fujin`` has no hard requirements on the virtual private server you choose (VPS) apart from the fact it must be running a recent version of ubuntu or a debian based system.
I've mainly run my test with various version of ubuntu, 20.04, 22.04 and 24.04. Other than that use what the best option for your app, or the cheapest option you can find.

You also need root ssh access to the server and a custom user. ``fujin`` might work with the root but I've notice some issues with it so I highly recommend creating a custom user.
For that you'll need firs the root user with an ssy access setup to the server. You'll have to change the  initial configuration in the ``fujin.toml`` file to look like this:

.. code-block:: toml

    [host]
    ip = "52.0.56.137"
    user = "root"
    ....

Then you'll run the the command ``fujin server create-user`` with the username you want to user, you can for example use **fujin** as the username.
for example

.. code-block:: shell

    fujin server create-user fujin

This will create a new **fujin** user on your server, add it to the ``sudo`` group with the option to run all commands without having to type a password, and will
copy the authoried key from the **root** to your new user so that the ssh setup you made for the root user still work with this new one.

Domain name
***********

You can get one from a popular register like `namecheat <https://www.namecheap.com/>`_ or `godaddy <https://www.godaddy.com>`_ for if your re only using thing for testing you can use
`sslip <https://sslip.io/>`_. Example of what it will look like in the ``fujin.toml`` file assuming your server ip address is ``52.0.56.137``

.. code-block:: toml

    [host]
    domain_name = "52.0.56.137.sslip.io"
    ...

If you've bough a new domain, make sure you created an **A record** to point to the server IP address, with a sslip.io you don't do that.

.. tip::

    You don't need to specify both the ``ip`` and ``domain_name`` key, when the ``ip`` is missing ``fujin`` will use the domain to connect
    connect to the server.

Python package
--------------

.. note::

    If you are deploying a binary or self contained executable skip to the `next section </tutorial.html#binary>`_


Project Setup
*************

If you are deploying a python project with ``fujin``, you need your project to package and ideally having an entry point. We will be using django as an examples here, but the same step
can be applied to any other python project and you can find examples with more framework in the `examples <https://github.com/falcopackages/fujin/tree/main/examples/>`_ folder on github.

Let's start by installing and initliaying a simple django project.

.. code-block:: toml

    uv tool install django # this will give you access to the django-admin command globally on your system
    django-admin startproject bookstore
    cd bookstore
    uv init --package .
    uv add django gunicorn

The ``uv init`` command make your project mostly ready to be used with fujin. It inilaized a `packaged application <https://docs.astral.sh/uv/concepts/projects/#packaged-applications>`_ using uv,
meaning the app can can be package and distribute via pypi for an example and define an entry point, which are the two requirements of ``fujin``.
This is the content you'll get in the  ``pyproject.toml`` file, the imported part have being highlighted.

.. code-block:: toml
    :linenos:
    :emphasize-lines: 15-16,18-20

    [project]
    name = "bookstore"
    version = "0.1.0"
    description = "Add your description here"
    readme = "README.md"
    authors = [
        { name = "Tobi", email = "tobidegnon@proton.me" }
    ]
    requires-python = ">=3.12"
    dependencies = [
        "django>=5.1.3",
        "gunicorn>=23.0.0",
    ]

    [project.scripts]
    bookstore = "bookstore:main"

    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

The ``build-system`` section is what allows us to build our project into a wheel file (python package format) and the ``project.scripts`` defines a cli entry point for our app.
This mean that if our app is installed there (either with ``pip install`` or ``uv tool install`` for example) there will be ``bookstore`` available globally on our system to run the project.

.. note::

    If you installing it in a virtual envirnomment then there will be a file ``.venv/bin/bookstore`` that will run this cli entry point. This is what ``fujin`` expect internally.
    When it deployed your python project it setup and  install a virtuaenv environnmen in the app directory in a .venv folder and expect this entry point to be able to run
    command with the ``fujin app exec <command>`` command.

Currently our entry point will run a main function in the ``src/bookstore/__init__.py`` file, let's change that.

.. code-block:: shell

    rm -r src
    mv manage.py bookstore/__main__.py

With first remove the ``src`` folder, we won't use that since our django project will reside in the top level ``bookstore`` folder, I also recommend keeping all
you django code in that folder, including new apps, this make things easier for packaging purpose.
We the next command you are now able to do this:

.. code-block:: shell
    uv run bookstore migrate # equivalent to python manage.py migrate if we kept the manage.py file

Now to finisu update the ``scripts`` section your ``pyproject.toml`` file.

.. code-block:: toml

    [project.scripts]
    bookstore = "bookstore.__main__.py:main"

Now the cli that will be install with your project will do the job of the ``manage.py`` file, to test this out, run the following command

.. code-block:: shell

    uv sync # needed because we updated the scripts section
    source .venv/bin/activate
    bookstore runserver


.. admonition:: falco
    :class: tip dropdown

    If you want a django will all this pre requesistes in place chekcout `falco <https://github.com/falcopackages/falco-cli>`_.
    It also automatically provide a ``start_app`` command that moves the app in the right folder.

fujin init
**********

Now that our project is ready run, at the root of it run ``fujin init``

.. admonition:: falco
    :class: tip dropdown

    In a falco project run ``fujin init --profile falco``

Here what you'll get

.. code-block:: toml

    app = "bookstore"
    build_command = "uv build && uv pip compile pyproject.toml -o requirements.txt"
    distfile = "dist/bookstore-{version}-py3-none-any.whl"
    requirements = "requirements.txt"
    release_command = "bookstore migrate"
    installation_mode = "python-package"

    [webserver]
    upstream = "unix//run/bookstore.sock"
    type = "fujin.proxies.caddy"

    [processes]
    web = ".venv/bin/gunicorn bookstore.wsgi:application --bind unix//run/bookstore.sock"

    [aliases]
    shell = "server exec --appenv -i bash"

    [host]
    user = "root"
    domain_name = "bookstore.com"
    envfile = ".env.prod"

Update the host section, it should look something like this, but with yours server IP

.. code-block:: toml

    [host]
    domain_name = "52.0.56.137.sslip.io"
    user = "fujin"
    envfile = ".env.prod"

Create a the root of you project a ``.env.prod``, it can be empty file for now, the only requirements is that the file should exists.
Update your the ``booking/settings.py`` with the changes below:

.. code-block:: python

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = False

    ALLOWED_HOSTS = ["52.0.56.137.sslip.io"]

With the current setup we should already be able to deploy our app with the ``fujin up`` command, but staticfiles won't work, let's make some changes,
first in ``booking/settings.py`` add the line below:

.. code-block:: python
    :linenos:
    :lineno-start: 118
    :emphasize-lines: 119

    STATIC_URL = "static/"
    STATIC_ROOT = "./staticfiles"

The last lines means that when the ``collectstatic`` command is run, the files will be place in a **staticfiles** directory in the current dir.
Now let's update the ``fujin.toml`` file to run ``collectstatic`` before the app is started and move these files in the folder where our web server
can read it

.. code-block:: toml

    ...
    release_command = "bookstore migrate && bookstore collectstatic --no-input && sudo rsync --mkpath -a --delete staticfiles/ /var/www/bookstore/static/"
    ...

    [webserver]
    ...
    statics = { "/static/*" = "/var/www/bookstore/static/" }

.. note::

    If your server have a version of rsync that does not have the ``--mkpath`` option, you can run update the rsync part like to create the folder beforahand

    .. code-block:: text

        && sudo mkdir -p /var/www/bookstore/static/ && sudo rsync -a --delete staticfiles/ /var/www/bookstore/static/"

Now move to the `deploy </tutorial.html#deploy>`_ for the next step.

Binary
------

This mode is intended for self contained executable, for example with languages lke Golang, Rust that can be compiled into single file that is shipped to the server,
and you can get a similar feature in python with tool like `pyapp <https://github.com/ofek/pyapp>`_ and `plex <https://github.com/pex-tool/pex>`_.
For this tutorial we will use a `pocketbase <https://github.com/pocketbase/pocketbase>`_ a go backend that can be run as a standalone app.

.. code-block:: shell

    mkdir pocketbase
    cd pocketbase
    touch .env.prod
    curl -LO https://github.com/pocketbase/pocketbase/releases/download/v0.22.26/pocketbase_0.22.26_linux_amd64.zip
    fujin init --profile binary

With the instructions above we will download a version of pocket to run on linux from their github release, and initailaze a new fujin configuration in ``binary`` mode.
Now update the ``fujin.toml`` file with the changes below:

.. code-block:: toml
    :linenos:
    :emphasize-lines:2,4,5

    app = "pocketbase"
    version = "0.22.26"
    build_command = "unzip pocketbase_0.22.26_linux_amd64.zip"
    distfile = "pocketbase"
    release_command = "pocketbase migrate"
    installation_mode = "binary"

    [webserver]
    upstream = "localhost:8090"
    type = "fujin.proxies.caddy"

    [processes]
    web = "pocketbase serve --http 0.0.0.0:8090"

    [aliases]
    shell = "server exec --appenv -i bash"

    [host]
    domain_name = "52.0.56.137.sslip.io"
    user = "fujin"
    envfile = ".env.prod"

Now you are ready to deploy

Deploy
------

Now that your project is ready run the commands below to deploy for the first time

.. code-block:: shell

    fujin up

The first time the process can take a few minutes, at the end of it you should have a link to your deployed app.
A few notable commands:

.. code-block:: shell
    :caption: Deploy an app on a host where a fujin has already being setup

    fujin deploy

You also use the ``deploy`` commands when you have change fujin config or exported configs:

.. code-block:: shell
    :caption: Export the systemd config being used so that you can edit them

    fujin app export-config

.. code-block:: shell
    :caption: Export the webserver config, in this case caddy

    fujin proxy export-config

and the command you''ll proably be running the most

.. code-block:: shell
    :caption: When you've only made code and envfile related changes

    fujin redeploy

FAQ
---

What about my database ?
************************

I'm currently rocking with sqlite for my side projects, so this isn't really an issue for me at the moment, that's why fujin does not currently help in
any fashion regarding this aspect. But remember, you can still at any time ssh into your server and do what you want, so nothing stopping you from manually
installing postgres or any other database or services you might want to use. With that said I'll still like to have the configuration for any major extra tool
like a redis or cache being managed by fujin when possible. That's why I'm planning to implement a way to declare containers via the ``fujin.toml`` file to add
additionals tool needed for the app. These containers will be managed with ``podman``, podman because it is a rootless and daemonless which mean unless you need these
extra services podamn won't need any ressource on your server. To keep track of the development of this feature subscribe to this `issue <https://github.com/falcopackages/fujin/issues/17>`_.

