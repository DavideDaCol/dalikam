import os
import platform

if platform.system() == "Linux":
    os.environ["QT_QPA_PLATFORM"] = "xcb"