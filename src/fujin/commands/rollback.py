from dataclasses import dataclass

import cappa

from fujin.commands import BaseCommand


@cappa.command(help="")
@dataclass
class Rollback(BaseCommand):
    pass
