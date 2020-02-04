__all__ = ["NicoJob", "NicoDownloader"]

import sys

# init variable
from configparser import ConfigParser
import pkgutil
config = ConfigParser()
config.read_string(pkgutil.get_data(__package__, "config/data.cfg").decode())

import logging
handler = logging.StreamHandler(sys.stdout)
base_logger = logging.getLogger(__package__)
base_logger.setLevel(config["USER"]["loglevel"])
base_logger.addHandler(handler)

if config["USER"].getboolean("key_in_config"):
    lk = lambda: config["USER"]["nico_login"].split()
else:
    from .getin import lk

# start loading
from .worker import NicoJob
from .views import NicoDownloader
