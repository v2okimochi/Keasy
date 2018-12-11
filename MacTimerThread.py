# -*- coding: utf-8 -*-
from PyQt5.QtCore import QThread, pyqtSignal
import time


class TimeCounter(QThread):
    TimeoutSignal = pyqtSignal()

    # 0.3秒後にシグナル発信
    def run(self):
        time.sleep(0.3)
        self.TimeoutSignal.emit()
