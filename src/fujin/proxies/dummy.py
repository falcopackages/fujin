from fujin.config import Config
from fujin.host import Host


class WebProxy:
    host: Host
    config: Config

    def install(self):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass
