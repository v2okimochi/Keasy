# -*- coding: utf-8 -*-
import sys
import traceback
from ctypes import byref
from ctypes.wintypes import POINT
from os import path as os_path
from re import search as re_search
from time import sleep as time_sleep
from WinTimerThread import TimerThread
# Keasy uses keyboard ver.0.11.0.
import keyboard
from PyQt5.QtGui import QIcon, QPixmap

# import pywinautoの前にスレッドモードを切り替えている．
# これはスレッドモードのSTA/MTA切り替えの問題で，
# OSError:スレッドモードを設定してから変更できないと言われる
sys.coinit_flags = 2  # STA
# Keasy uses pywinauto ver.0.6.5
from pywinauto import findwindows, clipboard, keyboard as pywinauto_keyboard
from pywinauto.mouse import win32functions, move
from pywinauto.controls.common_controls import hwndwrapper


class ControlWindowForWindows:
    def __init__(self, gui):
        """
        :type gui:PyQt5.WindowGUI.WindowGUI
        """
        super().__init__()
        # gui.setWindowIcon(QIcon(self.resource_path(gui.icon_path)))
        # gui.icon_area.setPixmap(
        #     QPixmap(self.resource_path(gui.icon_path)).scaled(30, 30))
        self.mousePos_pointer = POINT()  # マウスカーソル座標の変更用
        self.pressedCtrl = False
        self.pressedShift = False
        # タイマー処理のインスタンス(別スレッド)
        self.timerThread = TimerThread()
        self.timerThread.start()
        self.timerThread.CtrlTimeoutSignal.connect(self.timeout_Ctrl)
        self.timerThread.ShiftTimeoutSignal.connect(self.timeout_Shift)
        # グローバルホットキーに反応 ===========================
        # 同じキーを押し続けると連続発動するので，
        # trigger_on release:Trueによって離すまで発動を止める
        keyboard.add_hotkey('ctrl', lambda: self.onPressCtrl_global(gui),
                            trigger_on_release=True)
        keyboard.add_hotkey('shift', lambda: self.onPressShift_global(gui),
                            trigger_on_release=True)
        keyboard.add_hotkey('ctrl+shift,ctrl+shift',
                            lambda: self.autoComplete_single(gui),
                            trigger_on_release=True)
        keyboard.add_hotkey('ctrl+space', gui.switchMemorize,
                            trigger_on_release=True)
        keyboard.add_hotkey('shift+tab', gui.rollBack_at_flag,
                            trigger_on_release=True)
        # このアプリのハンドルを取得 ===========================
        self.thisHandle = findwindows.find_window(
            title='Keasy', class_name='Qt5QWindowIcon')
        self.thisWindowWrapper = hwndwrapper.HwndWrapper(self.thisHandle)
    
    # pyinstallerでexe化した後でもアイコン画像を使えるようにパス変更
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os_path.join(sys._MEIPASS, relative_path)
        return os_path.join(os_path.abspath("."), relative_path)

    # Ctrlが押された場合
    def onPressCtrl_global(self, gui):
        if keyboard.is_pressed('shift'):
            return
        if self.pressedCtrl:
            self.appShow_or_Hide(gui)
            self.pressedCtrl = False
        else:
            self.pressedCtrl = True
            self.timerThread.timer_ctrl()
    
    # Shiftが押された場合
    def onPressShift_global(self, gui):
        if keyboard.is_pressed('ctrl'):
            return
        if self.pressedShift:
            self.autoComplete(gui)
            self.pressedShift = False
        else:
            self.pressedShift = True
            self.timerThread.timer_shift()
    
    # Ctrl入力フラグを一定時間後に消す
    def timeout_Ctrl(self):
        self.pressedCtrl = False
    
    # Shift入力フラグを一定時間後に消す
    def timeout_Shift(self):
        self.pressedShift = False
    
    # ウィンドウのトレイ格納/再表示
    # ブラウザが最前面にある & そのページのURLと一致するアカウントが1つだけ
    # の場合に限り，ユーザID/Mailとパスワードを一時保存(自動memorize)
    # そうでなかった場合，トレイ格納/再表示だけを行う
    def appShow_or_Hide(self, gui):
        try:
            # 既にKeasyウィンドウが非表示だった場合
            if gui.isHidden():
                # 吹っ飛ぶ前のマウス位置を記憶======================
                win32functions.GetCursorPos(byref(self.mousePos_pointer))
                beforeX = self.mousePos_pointer.x
                beforeY = self.mousePos_pointer.y
                # time.sleep(0.01)  # 一旦止めないと不自然な挙動をする
                # ブラウザを開いていれば，URLからアカウントを一時保存
                self.autoMemorize(gui)
                # トレイ格納時のウィンドウサイズに戻す
                if self.savedMyGeometry != None:
                    gui.restoreGeometry(self.savedMyGeometry)
                gui.show()  # ウィンドウ表示
                self.thisWindowWrapper.set_focus()  # アクティブにする＋フォーカスする
                move(coords=(beforeX, beforeY))  # マウスを移動し直す
                gui.console.setFocus()  # コンソールにフォーカス(カーソル表示)
            # Keasyウィンドウが表示されている場合
            else:
                # 吹っ飛ぶ前のマウス位置を記憶======================
                win32functions.GetCursorPos(byref(self.mousePos_pointer))
                beforeX = self.mousePos_pointer.x
                beforeY = self.mousePos_pointer.y
                time_sleep(0.01)  # 一旦止めないと不自然な挙動をする
                # 開いているウィンドウのハンドル一覧を取得
                windowHandles = self.getWindowHandles()
                for i in range(len(windowHandles) - 1):
                    # 最後面以外のどこかにKeasyウィンドウがあれば，
                    # Keasyの次のウィンドウにフォーカス
                    if windowHandles[i] == self.thisHandle:
                        # 次ウィンドウのハンドル取得
                        nextWindow = hwndwrapper.HwndWrapper(
                            windowHandles[i + 1]
                        )
                        nextWindow.set_focus()  # 次ウィンドウにフォーカス
                        break
                
                # Keasyウィンドウが最後面だった場合は，
                # Keasyの前のウィンドウにフォーカス
                if windowHandles[len(windowHandles) - 1] == self.thisHandle:
                    # 前ウィンドウのハンドル取得
                    previousWindow = hwndwrapper.HwndWrapper(
                        windowHandles[(len(windowHandles) - 1) - 1]
                    )
                    previousWindow.set_focus()  # 前ウィンドウにフォーカス
                # 格納時のウィンドウサイズを記憶
                self.savedMyGeometry = gui.saveGeometry()
                gui.hide()  # ウィンドウ非表示
                move(coords=(beforeX, beforeY))  # マウスを移動し直す
        except:
            traceback.print_exc()
    
    # ブラウザで開いているURLからアカウントを取得して一時保存
    def autoMemorize(self, gui):
        # クリップボードのコピー内容を消去
        clipboard.EmptyClipboard()
        # 開いているウィンドウのハンドル一覧を取得
        windowHandles = self.getWindowHandles()
        
        # 最前面にあるウィンドウがブラウザならURLを取得
        firstElememt = findwindows.find_element(
            handle=windowHandles[0]
        )
        # Mozilla FirefoxからURL取得
        if re_search('Mozilla Firefox', str(firstElememt)) is not None:
            keyboard.send('ctrl+l,shift,ctrl+c')
        elif re_search('Google Chrome', str(firstElememt)) is not None:
            keyboard.send('ctrl+l,shift,ctrl+c')
        else:
            # 対応ブラウザでない場合は取得中止
            return
        # 0.5秒までの間にクリップボードにコピーされたら途中で抜ける
        for t in range(5):
            if clipboard.GetClipboardFormats() != []:
                break
            time_sleep(0.1)  # コピーが間に合わなければ0.1秒待つ
        # クリップボードが空なら中止(フォーマットが取得されないことで判定)
        if clipboard.GetClipboardFormats() == []:
            return
        # クリップボードにコピーしたURLを取得
        copiedURL = clipboard.GetData()
        # print(copiedURL)
        # 何もコピーされていないなら中止
        if len(copiedURL) == 0:
            return
        URL_pattern = []
        # URL文字数を30から順に区切る
        if len(copiedURL) >= 15:
            if len(copiedURL) >= 20:
                if len(copiedURL) >= 25:
                    if len(copiedURL) >= 30:
                        URL_pattern.append(copiedURL[0:30])
                    URL_pattern.append(copiedURL[0:25])
                URL_pattern.append(copiedURL[0:20])
            URL_pattern.append(copiedURL[0:15])
        else:
            URL_pattern.append(copiedURL)
        
        # URL文字数を30,25,20,15の順に減らしながら，含まれるアカウントを探す
        # 該当アカウントが1つだけならユーザID/Mailとパスワードを取得
        for i in range(len(URL_pattern)):
            # print(URL_pattern[i])
            IDandPass = gui.cmdEvt.autoFindByURL(URL_pattern[i])
            if IDandPass != {}:
                serviceName = IDandPass['Service']
                IDorMail = IDandPass['ID']
                passWord = IDandPass['Pass']
                # ユーザID/Mailとパスワードの一時保存
                # つまり自動memorize
                gui.cmdEvt.setMemorize(serviceName, IDorMail, passWord)
                break
    
    # 開いているウィンドウのハンドルを最前面から順に取得
    def getWindowHandles(self) -> list:
        windowList = findwindows.find_windows()  # ウィンドウのハンドル値
        windowHandles = []  # windowListから余計なウィンドウを省いたリスト
        # 先頭5個までのウィンドウだけ扱う
        if len(windowList) > 5:
            num = 5
        else:
            num = len(windowList)
        # print('##########################################')
        for i in range(num):
            element = findwindows.find_element(
                handle=windowList[i])
            # title='' or 'None'のウィンドウをリストから除外
            if re_search('\'\'', str(element)) is None \
                    and re_search('None', str(element)) is None:
                windowHandles.append(windowList[i])
                # print(str(i) + ':' + str(element))  # debug
        return windowHandles
    
    # 文字列の記号に{}を付けて返す
    # pywinauto_keyboard.SendKeysで記号を打ち込むため
    def transStringForPywinauto(self, text) -> str:
        check = '~!@#$%^&*()_+{}|:"<>?'  # 比較する記号群
        translated = ''
        # 記号にだけ{}をつける：例えば'f$7%' => 'f{$}7{%}'
        for i in text:
            match = False
            for j in check:
                if i == j:
                    match = True
            if match:
                translated = ''.join([translated, '{' + i + '}'])
            else:
                translated = ''.join([translated, i])
        return translated
    
    # ユーザID/Mailとパスワードの自動入力
    def autoComplete(self, gui):
        try:
            # 一時記憶したユーザID/Mailとパスワードを取得
            Memorize = gui.cmdEvt.getMemorize()
            IDorMail = Memorize['user']
            passWord = Memorize['pass']
            # print('memorized data...ID:' + IDorMail + ' , PASS:' + passWord)
            # IDorMailが取得されているなら自動入力
            if IDorMail == "":
                return
            # 記号を打ち込めるように変換
            IDorMail_translated = self.transStringForPywinauto(IDorMail)
            passWord_translated = self.transStringForPywinauto(passWord)
            pywinauto_keyboard.SendKeys(
                IDorMail_translated +
                '{TAB}' +
                passWord_translated, pause=0
            )
        except:
            traceback.print_exc()
    
    # ユーザ名かパスワードの片方を自動入力
    def autoComplete_single(self, gui):
        try:
            # 一時記憶したユーザID/Mailとパスワードを取得
            Memorize = gui.cmdEvt.getMemorize()
            IDorMail = Memorize['user']
            passWord = Memorize['pass']
            # print('memorized data...ID:' + IDorMail + ' , PASS:' + passWord)
            # IDorMailが取得されているなら，片方を自動入力
            if IDorMail == "":
                return
            # 記号を打ち込めるように変換
            IDorMail_translated = self.transStringForPywinauto(IDorMail)
            passWord_translated = self.transStringForPywinauto(passWord)
            # 0:ID/Mail, 1:passWord
            if gui.cmdEvt.completeTarget == 0:
                pywinauto_keyboard.SendKeys(IDorMail_translated, pause=0)
            else:
                pywinauto_keyboard.SendKeys(passWord_translated, pause=0)
        except:
            traceback.print_exc()
