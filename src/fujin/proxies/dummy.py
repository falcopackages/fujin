from fabric import Connection

from fujin.config import Config


class WebProxy:
    conn: Connection
    domain_name: str
    config: Config

    def install(self):
        pass

    def uninstall(self):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass
