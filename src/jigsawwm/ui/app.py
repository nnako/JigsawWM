"""This module provides a QApplication instance and a custom exception hook for handling uncaught exceptions."""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from ctypes import *  # pylint: disable=wildcard-import,unused-wildcard-import
from ctypes.wintypes import *  # pylint: disable=wildcard-import,unused-wildcard-import
from functools import partial

from PySide6 import QtWidgets
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)
app = QtWidgets.QApplication(sys.argv)


class ClipboardHelper(QObject):
    """Thread-safe clipboard operations using signals/slots."""
    _executor = ThreadPoolExecutor()
    set_text_async = Signal(str)
    get_text_async = Signal(object)

    def __init__(self):
        super().__init__()
        self.set_text_async.connect(self.set_text)
        self.get_text_async.connect(self.get_text)

    @Slot(str)
    def set_text(self, text):
        """Set clipboard text (must be called on main thread via signal)."""
        app.clipboard().setText(text)

    @Slot(object)
    def get_text(self, done):
        """Get clipboard text (must be called on main thread via signal)."""
        text = app.clipboard().text()
        self._executor.submit(partial(done, text))


clipboard_helper = ClipboardHelper()

WM_POWERBROADCAST = 0x0218
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012


class SystemEventListener(QWidget):
    """A QWidget that listens for system events."""

    on_system_resumed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JigsawWM Event Listener")
        self.resize(300, 100)
        # show then hide in orde to receive events properly
        self.show()
        self.hide()

    def nativeEvent(self, eventType, message):
        if eventType == "windows_generic_MSG":
            msg = MSG.from_address(int(message))
            if msg.message == WM_POWERBROADCAST:
                if msg.wParam == PBT_APMRESUMESUSPEND:
                    print("System resumed from suspension (manual intervention).")
                elif msg.wParam == PBT_APMRESUMEAUTOMATIC:
                    self.on_system_resumed.emit()
        return super().nativeEvent(eventType, message)


system_event_listener = SystemEventListener()
