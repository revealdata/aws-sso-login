#!/usr/bin/env python3
import sys
from config import APP, ARGUMENTS
from lib.ui import QApp, MainWindow

# Global variables

def __retval_to_bool(int):
    """ Convert the return value of a subprocess to a boolean """
    if int == 0:
        return True
    else:
        return False


if __name__ == "__main__":
    """ Main entry point for the application """
    ui_args = {
        "app": APP,
        "arguments": ARGUMENTS
    }
    app = QApp
    window = MainWindow(**ui_args)
    window.show()
    sys.exit(app.exec())
