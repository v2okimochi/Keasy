# -*- coding: utf-8 -*-
# AppKit, Quartz, FoundationはPyCharmの自動補完に引っかからないけど使える
import time
import sys
import os
import subprocess
from AppKit import NSWorkspace
from Quartz import CGWindowListCopyWindowInfo
from Quartz import kCGWindowListOptionOnScreenOnly, kCGNullWindowID
from Foundation import NSAppleScript
import pyautogui
from KeyHookThread import KeyHooker
from MacTimerThread import TimeCounter


class ControlWindowForMac:
    def __init__(self, gui):
        """
        :type gui: WindowGUI.WindowGUI
        """
        super().__init__()
        # 別スレッドでグローバルキーフックを常駐
        self.keyHooker = KeyHooker()
        self.keyHooker.start()
        self.keyHooker.pushCtrlSignal.connect(
            lambda: self.onPressCtrl_global(gui))
        self.keyHooker.releaseCtrlSignal.connect(self.onReleasedCtrl_global)
        self.keyHooker.releaseShiftSignal.connect(self.onReleasedShift_global)
        self.keyHooker.pushShiftSignal.connect(
            lambda: self.onPressShift_global(gui))
        self.keyHooker.pushCommandSignal.connect(
            lambda: self.onPressCommand_global(gui)
        )
        self.keyHooker.releaseCommandSignal.connect(
            lambda: self.onReleaseCommand_global(gui)
        )
        # キーが押される度に別スレッドを作って並行処理(処理後はスレッド離脱)
        self.timer_ctrl = TimeCounter()
        self.timer_ctrl.TimeoutSignal.connect(self.ctrlTimeout)
        self.timer_shift = TimeCounter()
        self.timer_shift.TimeoutSignal.connect(self.shiftTimeout)
        self.timer_command = TimeCounter()
        self.timer_command.TimeoutSignal.connect(self.commandTimeout)
        # トレイクリック時
        gui.tray.activated.connect(lambda: self.appShow_or_Hide(gui))
        # キー連続入力の判定用
        self.pressedCommand = False
        self.commandTimeLimit = False
        self.pressedCtrl = False
        self.ctrlTimeLimit = False
        self.pressedShift = False
        self.shiftTimeLimit = False

    # Ctrlが押された時
    def onPressCtrl_global(self, gui):
        # if Ctrl*2:ウィンドウをタスクトレイに引っ込める/出す
        # else:Ctrl押されたフラグ立てとく
        if self.ctrlTimeLimit:
            self.ctrlTimeLimit = False
            self.appShow_or_Hide(gui)
        else:
            # print('press ctrl')
            self.ctrlTimeLimit = True
            self.timer_ctrl.start()  # 別スレッドを作って時間経過を監視
            self.pressedCtrl = True

    # Ctrlが離された時
    def onReleasedCtrl_global(self):
        # print('release ctrl')
        self.pressedCtrl = False

    def onPressCommand_global(self, gui):
        if self.commandTimeLimit:
            # print('command -> command')
            gui.switchMemorize()
            # デスクトップに通知
            mes = ['ユーザID/Mail', 'パスワード']
            gui.tray.showMessage(
                mes[gui.cmdEvt.completeTarget] + 'を自動入力できます',
                'Ctrl+(Shift -> Shift)', msecs=0
            )
            self.commandTimeLimit = False
        else:
            self.commandTimeLimit = True
            self.timer_command.start()  # 別スレッドを作って時間経過を監視
        self.pressedCommand = True

    def onReleaseCommand_global(self, gui):
        # print('release command')
        self.pressedCommand = False

    # Shiftが押された時
    def onPressShift_global(self, gui):
        # if Ctrl + Shift*2:Single auto-completeする
        # elif Command + Shift*2:Single auto-completeする
        # elif Shift*2:auto-completeする
        # else: Shift押されたフラグ立てとく
        if self.shiftTimeLimit and self.pressedCtrl:
            # print('ctrl + shift -> shift')
            self.shiftTimeLimit = False
            self.autoComplete_single(gui)
            return  # pressedShift=Trueをスキップ
        elif self.shiftTimeLimit and self.pressedCommand:
            # print('command + shift -> shift')
            self.shiftTimeLimit = False
            self.autoComplete_single(gui)
            return
        elif self.shiftTimeLimit:
            # print('shift -> shift')
            self.shiftTimeLimit = False
            self.autoComplete(gui)
        else:
            self.shiftTimeLimit = True
            self.timer_shift.start()  # 別スレッドを作って時間経過を監視
        self.pressedShift = True

    # Shiftが離された時
    # Shift + any(ctrl,spaceどちらでもない)の時も発動させる
    # auto-completeの大文字入力で誤射ループに入らないための措置
    def onReleasedShift_global(self):
        self.pressedShift = False
        self.shiftTimeLimit = False

    # Ctrlが押されてから0.3秒経過した時
    def ctrlTimeout(self):
        # print('timeout')
        self.ctrlTimeLimit = False
        self.timer_ctrl.quit()

    # Shiftが押されてから0.3秒経過した時
    def shiftTimeout(self):
        # print('timeout')
        self.shiftTimeLimit = False
        self.timer_shift.quit()

    # Commandが押されてから0.3秒経過した時
    def commandTimeout(self):
        self.commandTimeLimit = False
        self.timer_command.quit()

    # ユーザID/Mailとパスワードの自動入力
    def autoComplete(self, gui):
        # 一時記憶したユーザID/Mailとパスワードを取得
        Memorize = gui.cmdEvt.getMemorize()
        IDorMail = Memorize['user']
        passWord = Memorize['pass']
        # IDorMailが取得されてないなら中止
        if IDorMail == "":
            return

        clipboard = self.getClipboardData()  # クリップボードの内容を退避
        time.sleep(0.2)  # Shiftを話す間に入力開始しないよう遅らせる
        # IDorMailをクリップボードにセット=>貼り付け
        # Passwordをクリップボードにセット=>貼り付け
        self.setClipboardData(IDorMail)
        pyautogui.hotkey('command', 'v')
        pyautogui.keyDown('tab')
        pyautogui.keyUp('tab')
        self.setClipboardData(passWord)
        pyautogui.hotkey('command', 'v')
        self.setClipboardData(clipboard)  # クリップボードの内容を復元

    # ユーザ名かパスワードの片方を自動入力
    def autoComplete_single(self, gui):
        # 一時記憶したユーザID/Mailとパスワードを取得
        Memorize = gui.cmdEvt.getMemorize()
        IDorMail = Memorize['user']
        passWord = Memorize['pass']
        # print('memorized data...ID:' + IDorMail + ' , PASS:' + passWord)
        # IDorMailが取得されているなら，片方を自動入力
        # print(IDorMail)
        if IDorMail == "":
            return

        clipboard = self.getClipboardData()  # クリップボードの内容を退避
        # 0:ID/Mail, 1:passWord
        if gui.cmdEvt.completeTarget == 0:
            # IDorMailをクリップボードにセット
            self.setClipboardData(IDorMail)
        else:
            # Passwordをクリップボードにセット
            self.setClipboardData(passWord)
        time.sleep(0.2)  # Shiftを話す間に入力開始しないよう遅らせる
        pyautogui.keyUp('ctrl')  # ctrl+command+vを回避するためctrl入力を解除
        pyautogui.hotkey('command', 'v')
        self.setClipboardData(clipboard)  # クリップボードの内容を復元

    # クリップボードのデータを取得
    def getClipboardData(self) -> str:
        p = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
        retcode = p.wait()
        data = p.stdout.read()
        txt = data.decode('utf-8')  # str型に戻す
        return txt

    # クリップボードのデータを変更
    def setClipboardData(self, data: str):
        p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        p.stdin.write(data.encode())  # バイト型を扱う
        p.stdin.close()
        retcode = p.wait()

    # 1文字ずつ見て，数字記号（#$%&）どれかがある限り1文字ずつ自動入力
    # 最初の文字が数字記号でないor途中で数字記号じゃなくなったら全文字まとめて自動入力
    # (1文字目で数字記号を自動入力してくれないバグ対応)
    def inputter(self, text: str):
        print(text)
        for i, char in enumerate(text):
            isFigureSymbol = False
            # 数字記号（Shiftを押す前は数字）である限り1文字ずつ自動入力
            for symbol in '#$%&':
                if char == symbol:
                    print(char)
                    pyautogui.keyDown('shift')
                    pyautogui.keyDown(char)
                    pyautogui.keyUp(char)
                    pyautogui.keyUp('shift')
                    isFigureSymbol = True
                    break
            # 数字記号じゃなくなったら残りの文字列を全て自動入力
            if not isFigureSymbol:
                txt = ''.join(text[i:])
                print(txt)
                pyautogui.typewrite(txt)
                return

    # ブラウザで開いているURLからアカウントを取得して一時保存
    def autoMemorize(self, gui):
        pyautogui.hotkey('command', 'l')
        pyautogui.hotkey('command', 'c')
        copiedURL = self.getClipboardData()
        # 何もコピーされていないなら中止
        if copiedURL == '':
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

    # アクティブウィンドウ(最前面のアプリ)の名前を取得
    def getActiveAppName(self) -> str:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        activeWindow = str(app.localizedName())
        print('active is: ' + activeWindow)
        return activeWindow

    def getActiveAppPID(self, appTitle: str) -> int:
        # オンスクリーン上のウィンドウ情報を取得(ウィンドウ順)
        options = kCGWindowListOptionOnScreenOnly
        windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
        activeAppPID = 0
        for num, window in enumerate(windowList):
            windowNumber = window['kCGWindowNumber']
            windowOwnerPID = window['kCGWindowOwnerPID']
            ownerName = window['kCGWindowOwnerName']
            windowTitle = window.get('kCGWindowName', u'Unknown')
            # print(
            #     str(windowNumber) + ':'
            #     + str(windowOwnerPID) + ':'
            #     + str(ownerName) + ':'
            #     + str(windowTitle))
            # デバッグ時はownerName:PythonでwindowTitle:Keasy)
            if (ownerName == 'Python' and windowTitle == appTitle) \
                    or (ownerName == appTitle and windowTitle == appTitle):
                activeAppPID = str(windowList[num]['kCGWindowOwnerPID'])
                # print('activePID: ' + activeAppPID)
        # print('=========================')
        return activeAppPID

    # Keasyの真後ろにあるウィンドウのタイトルを取得する
    def getBehindAppName(self, appTitle: str) -> str:
        # オンスクリーン上のウィンドウ情報を取得(ウィンドウ順)
        options = kCGWindowListOptionOnScreenOnly
        windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
        behindAppName = 'Finder'
        for num, window in enumerate(windowList):
            windowNumber = window['kCGWindowNumber']
            windowOwnerPID = window['kCGWindowOwnerPID']
            ownerName = window['kCGWindowOwnerName']
            windowTitle = window.get('kCGWindowName', u'Unknown')
            print(
                str(windowNumber) + ':'
                + str(windowOwnerPID) + ':'
                + str(ownerName) + ':'
                + str(windowTitle))
            # デバッグ時はownerName:PythonでwindowTitle:Keasy)
            if (ownerName == 'Python' and windowTitle == appTitle) \
                    or (ownerName == appTitle and windowTitle == appTitle):
                behindAppName = str(windowList[num + 1]['kCGWindowOwnerName'])
                print('behind: ' + behindAppName)
        print('=========================')
        return behindAppName

    # 引数で受け取った名前のアプリをアクティブ化する
    def activateApp(self, appName: str):
        # request = 'if app "' \
        #           + appName \
        #           + '" is running then tell app "' \
        #           + appName \
        #           + '" to activate'
        request = 'tell app "' + appName + '" to activate'
        command = NSAppleScript.alloc().initWithSource_(request)
        command.executeAndReturnError_(None)

    def activateAppByPID(self, pid: int):
        # request = 'if app "' \
        #           + appName \
        #           + '" is running then tell app "' \
        #           + appName \
        #           + '" to activate'
        request = 'tell app "System Events"\n' \
                  'tell (process id ' + str(pid) + ') to activate'
        command = NSAppleScript.alloc().initWithSource_(request)
        command.executeAndReturnError_(None)

    def activateMe(self, gui):
        appName = gui.appTitle
        # request = 'if app "' \
        #           + appName \
        #           + '" is running then tell app "' \
        #           + appName \
        #           + '" to activate'
        request = 'if app "Keasy" is running then ' \
                  'tell app "Keasy" to activate'
        command = NSAppleScript.alloc().initWithSource_(request)
        command.executeAndReturnError_(None)

    # Keasyをタスクトレイに引っ込めたり出したりする
    def appShow_or_Hide(self, gui):
        # ウィンドウの表示or非表示
        if gui.isHidden():
            # アクティブウィンドウがブラウザだったらアカウント自動検索
            activeAppName = self.getActiveAppName()
            if activeAppName == 'Firefox' or \
                    activeAppName == 'Google Chrome' or \
                    activeAppName == 'Safari':
                self.autoMemorize(gui)
            gui.show()
            pid = self.getActiveAppPID(gui.appTitle)
            time.sleep(0.1)  # 遅延させないと新たにアプリ起動してしまう
            # self.activateApp(gui.appTitle)  # ウィンドウをアクティブ化
            # self.activateAppByPID(pid)
            self.activateMe(gui)
        else:
            # 真後ろのウィンドウのタイトルを取得
            behindAppName = self.getBehindAppName(gui.appTitle)
            gui.hide()
            time.sleep(0.1)
            self.activateApp(behindAppName)  # 真後ろのウィンドウをアクティブ化
