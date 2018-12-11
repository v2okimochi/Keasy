# -*- coding: utf-8 -*-
from PyQt5.QtCore import QThread, pyqtSignal
import time


class TimerThread(QThread):
    CtrlTimeoutSignal = pyqtSignal()
    ShiftTimeoutSignal = pyqtSignal()
    
    # 一定時間後にctrl入力フラグをタイムアウトさせる
    def timer_ctrl(self):
        time.sleep(0.3)
        self.CtrlTimeoutSignal.emit()

    # 一定時間後にshift入力フラグをタイムアウトさせる
    def timer_shift(self):
        time.sleep(0.3)
        self.ShiftTimeoutSignal.emit()
