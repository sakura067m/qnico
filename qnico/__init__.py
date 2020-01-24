import sys
from .getin import lk

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

# start loading
from .worker import NicoJob
from .views import NicoDownloader
