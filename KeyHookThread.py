# -*- coding: utf-8 -*-
from pynput import keyboard
from PyQt5.QtCore import QThread, pyqtSignal


class KeyHooker(QThread):
    # シグナル
    pushCtrlSignal = pyqtSignal()
    releaseCtrlSignal = pyqtSignal()
    pushShiftSignal = pyqtSignal()
    releaseShiftSignal = pyqtSignal()
    pushCommandSignal = pyqtSignal()
    releaseCommandSignal = pyqtSignal()

    def __init__(self):
        super().__init__()

    # キーが押された時に発動
    # ctrl,shift,spaceなら，それぞれのシグナルを発信
    # 他のキーだったら，shiftが離された時のシグナルを発信
    # (auto-completeで大文字入力中の誤射ループを防ぐため)
    def on_press(self, key):
        try:
            if key == keyboard.Key.ctrl:
                self.pushCtrlSignal.emit()
            elif key == keyboard.Key.shift:
                self.pushShiftSignal.emit()
            elif key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                self.pushCommandSignal.emit()
            else:
                self.releaseShiftSignal.emit()
        except AttributeError:
            # キー入力でExceptionが起こるが何もさせない
            pass

    # キーが離された時に発動
    def on_release(self, key):
        # print('{0} released'.format(key))
        if key == keyboard.Key.ctrl:
            self.releaseCtrlSignal.emit()
        elif key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
            self.releaseCommandSignal.emit()
        else:
            pass

    def run(self):
        # globalキーロガー開始
        with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release) as listener:
            listener.join()
