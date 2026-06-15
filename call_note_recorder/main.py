"""Call Note Recorder — entry point.

Startup order (per spec):
  1. ensure storage dirs       4. QApplication
  2. set up logging            5. system tray
  3. load config               6. icon widget + background model/update threads
"""

import sys

# Runtime HTTPS through Zscaler — patches certifi to trust the Windows cert
# store. Non-critical on non-corporate machines.
try:
    import pip_system_certs.wrapt_requests  # noqa: F401
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication

from utils import paths
from utils.logger import setup_logging
from data.config_store import ConfigStore
from data.training_store import TrainingStore
from app.main_window import AppController
from app.tray_manager import TrayManager
from version import APP_VERSION


def main():
    paths.ensure_dirs()
    log = setup_logging()
    log.info("Starting Call Note Recorder v%s (user=%s)", APP_VERSION, paths.USERNAME)

    config = ConfigStore()
    training = TrainingStore()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # tray app — closing windows hides them

    controller = AppController(config, training)
    controller.tray = TrayManager(controller)
    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
