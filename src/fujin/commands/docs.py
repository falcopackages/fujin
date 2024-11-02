from __future__ import annotations

import cappa

import fujin.config
from fujin.commands import BaseCommand


@cappa.command(help="Configuration documentation")
class Docs(BaseCommand):
    def __call__(self):
        docs = f"""
            # Fujin Configuration
            {fujin.config.__doc__}
            """
        self.stdout.output(docs)
