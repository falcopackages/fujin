Configuration
=============

.. automodule:: fujin.config


Example
-------

This is a minimal working example.

.. jupyter-execute::
    :hide-code:

    from fujin.commands.config import simple_config
    from tomli_w import dumps

    print(dumps(simple_config("bookstore")))