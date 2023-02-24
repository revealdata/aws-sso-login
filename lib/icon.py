import os
import base64
import logging

class ICON():
    def __init__(self, icon_file):
        self.logger = logging.getLogger(__name__)
        self.icon_file = f"resources/{icon_file}"
        self.base64 = None
        self.search_path = [
            ".",
            "resources",
            "../Resources"
        ]
        self.__find_icon_file()
        self.load_icon()

    def __find_icon_file(self):
        for path in self.search_path:
            if os.path.isfile(f"{path}{os.sep}{self.icon_file}"):
                self.icon_file = f"{path}{os.sep}{self.icon_file}"
            else:
                self.logger.debug(f"Icon file not found: {self.icon_file}")
                return None

    def load_icon(self):
        if os.path.isfile(self.icon_file):
            with open(self.icon_file, "rb") as img_file:
                self.base64 = base64.b64encode(img_file.read())
        else:
            self.base64 = None

    def get_icon(self):
        return self.base64
