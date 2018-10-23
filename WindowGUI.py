# -*- coding: utf-8 -*-
from CommandEvents import CommandEvents
from TimerThread import TimerThread
import sys
from os import path as os_path, remove as os_remove, name as os_name
from time import sleep as time_sleep
from re import search as re_search
import traceback
from ctypes.wintypes import POINT
from ctypes import byref
# Keasy uses pywinauto ver.0.6.3.
from pywinauto import findwindows, clipboard, keyboard as pywinauto_keyboard
from pywinauto.mouse import win32functions, move
from pywinauto.controls.common_controls import hwndwrapper
# Keasy uses keyboard ver.0.11.0.
import keyboard
# Keasy uses PyQT5 ver.5.9.
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QSystemTrayIcon, QLabel, QFrame, QTableWidget, QAbstractItemView
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt


class WindowGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.tray = QSystemTrayIcon()  # トレイアイコン（通知領域）
        # コマンド処理のインスタンス
        self.cmdEvt = CommandEvents()
        self.cmdEvt.setObj(self)
        self.cmdEvt.exitSIGNAL.connect(self.exitKeasy)
        # タイマー処理のインスタンス(別スレッド)
        self.timerThread = TimerThread()
        self.timerThread.start()
        self.timerThread.CtrlTimeoutSignal.connect(self.timeout_Ctrl)
        self.timerThread.ShiftTimeoutSignal.connect(self.timeout_Shift)
        self.appTitle = 'Keasy'
        self.version = '1.13'
        self.icon_path = 'icon.ico'
        self.icon2_path = 'icon2.ico'
        self.command_maxLengthTxt = '60字まで'
        self.tray_toolchipTxt = 'Ctrlキーを2回押すことで展開します'
        self.history = ['']  # コマンド履歴用
        self.mousePos_pointer = POINT()  # マウスカーソル座標の変更用
        self.pressedCtrl = False
        self.pressedShift = False
        self.setWindowTitle(self.appTitle)
        self.setWindowFlags(Qt.CustomizeWindowHint)  # タイトルバーを消す
        self.setWindowIcon(QIcon(self.resource_path(self.icon_path)))
        self.setMinimumSize(600, 500)
        self.setMaximumSize(1200, 800)
        self.savedMyGeometry = None  # タスクトレイ格納時のウィンドウサイズ
        self.setStyleSheet(
            'color:rgb(200,200,200);'
            'background:rgb(50,50,50);')
        self.initSystemTray()
        self.initUI()
        # グローバルホットキーに反応 ===========================
        # 同じキーを押し続けると連続発動するので，
        # trigger_on release:Trueによって離すまで発動を止める
        keyboard.add_hotkey('ctrl', self.onPressCtrl_global,
                            trigger_on_release=True)
        keyboard.add_hotkey('shift', self.onPressShift_global,
                            trigger_on_release=True)
        keyboard.add_hotkey('ctrl+shift,ctrl+shift',
                            lambda: self.autoComplete_single(),
                            trigger_on_release=True)
        keyboard.add_hotkey('ctrl+space', lambda: self.switchMemorize(),
                            trigger_on_release=True)
        keyboard.add_hotkey('shift+tab', lambda: self.rollBack_at_flag(),
                            trigger_on_release=True)
        
        self.show()  # ウィンドウ表示
        self.cmdEvt.receiver('')  # 最初にパスワード認証させる
        
        # このアプリのハンドルを取得 ===========================
        self.thisHandle = findwindows.find_window(
            title='Keasy', class_name='Qt5QWindowIcon')
        self.thisWindowWrapper = hwndwrapper.HwndWrapper(self.thisHandle)
    
    # Ctrlが押された場合
    def onPressCtrl_global(self):
        if keyboard.is_pressed('shift'):
            return
        if self.pressedCtrl:
            self.appShow_or_Hide()
            self.pressedCtrl = False
        else:
            self.pressedCtrl = True
            self.timerThread.timer_ctrl()
    
    # Shiftが押された場合
    def onPressShift_global(self):
        if keyboard.is_pressed('ctrl'):
            return
        if self.pressedShift:
            self.autoComplete()
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
    
    # pyinstallerでexe化した後でもアイコン画像を使えるようにパス変更
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os_path.join(sys._MEIPASS, relative_path)
        return os_path.join(os_path.abspath("."), relative_path)
    
    # ウィンドウを左クリックすると発動
    def mousePressEvent(self, QMouseEvent):
        """
        :type QMouseEvent:PyQt5.QtGui.QMouseEvent.QMouseEvent
        """
        try:
            # クリック時のマウス座標を保持
            self.previousMousePos = QMouseEvent.pos()
            self.prevX = self.previousMousePos.x()
            self.prevY = self.previousMousePos.y()
        except:
            traceback.print_exc()
    
    # ウィンドウをマウスドラッグ（左クリックしたままマウス移動）すると発動
    def mouseMoveEvent(self, QMouseEvent):
        """
        :type QMouseEvent:PyQt5.QtGui.QMouseEvent.QMouseEvent
        """
        try:
            # ドラッグ中はマウス座標とウィンドウの座標を取得し続ける
            currentMousePos = QMouseEvent.pos()
            currentX = currentMousePos.x()
            currentY = currentMousePos.y()
            appPos = self.pos()
            appPos_x = appPos.x()
            appPos_y = appPos.y()
        except:
            traceback.print_exc()
        
        # クリック時と現在のマウス座標差分だけ，今のウィンドウ位置から移動
        # ※クリック時マウス位置は不変
        diffPos_x = self.prevX - currentX
        diffPos_y = self.prevY - currentY
        self.move(appPos_x - diffPos_x, appPos_y - diffPos_y)
    
    # ウィンドウにフォーカスしている時のキー入力判定
    def keyPressEvent(self, evt):
        try:
            # Tabキーが押された＆Ctrl,Shift,Altのどれも押されていない場合，
            # Tabキーイベントを発生させる
            if evt.key() == Qt.Key_Tab and \
                    (not evt.modifiers() & Qt.ControlModifier and
                     not evt.modifiers() & Qt.ShiftModifier and
                     not evt.modifiers() & Qt.AltModifier):
                self.tabEvent()
            pass
        except:
            traceback.print_exc()
    
    # 現在のコマンド入力内容でTabキーイベントの処理
    def tabEvent(self):
        text = self.console.text()
        self.cmdEvt.tabReceiver(text)
    
    # 現在のmodeにおけるflag処理を1つ戻す
    def rollBack_at_flag(self):
        self.cmdEvt.shiftTabReceiver()
    
    # autoComplete_singleで自動入力する対象を切り替える
    def switchMemorize(self):
        try:
            # completeTarget=
            # 0: ユーザID/Mail
            # 1:パスワード
            if self.cmdEvt.completeTarget == 0:
                self.cmdEvt.completeTarget = 1
                self.tray.setIcon(
                    QIcon(self.resource_path(self.icon2_path))
                )
            else:
                self.cmdEvt.completeTarget = 0
                self.tray.setIcon(
                    QIcon(self.resource_path(self.icon_path))
                )
            if os_name == 'nt':
                mes = ['ユーザID/Mail', 'パスワード']
                self.tray.showMessage(
                    mes[self.cmdEvt.completeTarget] + 'を自動入力できます',
                    'Ctrl+(Shift -> Shift)', msecs=0
                )
        except:
            traceback.print_exc()
    
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
    def autoComplete(self):
        try:
            # 一時記憶したユーザID/Mailとパスワードを取得
            Memorize = self.cmdEvt.getMemorize()
            IDorMail = Memorize['user']
            passWord = Memorize['pass']
            # print('memorized data...ID:' + IDorMail + ' , PASS:' + passWord)
            # IDorMailが取得されているなら自動入力
            if IDorMail == "":
                return
            # 記号を打ち込めるように変換
            IDorMail_translated = self.transStringForPywinauto(IDorMail)
            passWord_translated = self.transStringForPywinauto(passWord)
            # Windowsの場合
            if os_name == 'nt':
                pywinauto_keyboard.SendKeys(
                    IDorMail_translated +
                    '{TAB}' +
                    passWord_translated, pause=0
                )
        except:
            traceback.print_exc()
    
    # ユーザ名かパスワードの片方を自動入力
    def autoComplete_single(self):
        try:
            # 一時記憶したユーザID/Mailとパスワードを取得
            Memorize = self.cmdEvt.getMemorize()
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
            if self.cmdEvt.completeTarget == 0:
                if os_name == 'nt':
                    pywinauto_keyboard.SendKeys(IDorMail_translated, pause=0)
            else:
                if os_name == 'nt':
                    pywinauto_keyboard.SendKeys(passWord_translated, pause=0)
        except:
            traceback.print_exc()
    
    # システムトレイ（通知領域）の設置
    def initSystemTray(self):
        try:
            self.tray.setIcon(
                QIcon(self.resource_path(self.icon_path))
            )
            self.tray.setToolTip(self.tray_toolchipTxt)
            self.tray.activated.connect(self.appShow_or_Hide)
            self.tray.show()
        except:
            traceback.print_exc()
    
    # コンソールの入力内容を変更
    def changeConsoleText(self, text: str):
        self.console.setText(text)
    
    # コマンドによる処理結果を表示
    def dispResponseText(self, txt):
        try:
            self.responseTxt.setText(txt)
        except:
            traceback.print_exc()
    
    # コマンドを送る度に，現在のモードを表示
    def dispMyMode(self, mode: str):
        self.myMode.setText(mode)
    
    # ウィンドウのトレイ格納/再表示
    # ブラウザが最前面にある & そのページのURLと一致するアカウントが1つだけ
    # の場合に限り，ユーザID/Mailとパスワードを一時保存(自動memorize)
    # そうでなかった場合，トレイ格納/再表示だけを行う
    def appShow_or_Hide(self):
        try:
            # 既にKeasyウィンドウが非表示だった場合
            if self.isHidden():
                # 吹っ飛ぶ前のマウス位置を記憶======================
                win32functions.GetCursorPos(byref(self.mousePos_pointer))
                beforeX = self.mousePos_pointer.x
                beforeY = self.mousePos_pointer.y
                # time.sleep(0.01)  # 一旦止めないと不自然な挙動をする
                # ブラウザを開いていれば，URLからアカウントを一時保存
                self.autoMemorize()
                # トレイ格納時のウィンドウサイズに戻す
                if self.savedMyGeometry != None:
                    self.restoreGeometry(self.savedMyGeometry)
                self.show()  # ウィンドウ表示
                self.thisWindowWrapper.set_focus()  # アクティブにする＋フォーカスする
                move(coords=(beforeX, beforeY))  # マウスを移動し直す
                self.console.setFocus()  # コンソールにフォーカス(カーソル表示)
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
                self.savedMyGeometry = self.saveGeometry()
                self.hide()  # ウィンドウ非表示
                move(coords=(beforeX, beforeY))  # マウスを移動し直す
        except:
            traceback.print_exc()
    
    # ブラウザで開いているURLからアカウントを取得して一時保存
    def autoMemorize(self):
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
            IDandPass = self.cmdEvt.autoFindByURL(URL_pattern[i])
            if IDandPass != {}:
                serviceName = IDandPass['Service']
                IDorMail = IDandPass['ID']
                passWord = IDandPass['Pass']
                # ユーザID/Mailとパスワードの一時保存
                # つまり自動memorize
                self.cmdEvt.setMemorize(serviceName, IDorMail, passWord)
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
    
    # アプリ終了処理
    def exitKeasy(self):
        self.tray.hide()  # 通知領域にアイコンだけ残らないようにする
        # 復号化された状態のDBを削除
        if os_path.exists('./keasy.db'):
            os_remove('./keasy.db')
        sys.exit()
    
    # アプリ内の表示フォント
    def fontSetter(self, txt):
        try:
            # Windowsの場合
            if os_name == 'nt':
                txt.setStyleSheet(
                    'font-family:MS Gothic;'
                    'font-size:14px;')
            # Macの場合？
            if os_name == 'posix':
                txt.setStyleSheet(
                    'font-family:Monospace;'
                    'font-size:14px;')
        except:
            traceback.print_exc()
    
    # コンソールの入力文字を伏せる
    def setConsoleMode_password(self):
        self.console.setEchoMode(QLineEdit.Password)
    
    # コンソールの入力文字を表示する
    def setConsoleMode_raw(self):
        self.console.setEchoMode(QLineEdit.Normal)
    
    # アプリUI設定
    def initUI(self):
        try:
            hline = QFrame()
            hline.setFrameShape(QFrame.HLine)
            vline = QFrame()
            vline.setFrameShape(QFrame.VLine)
            vline.setStyleSheet('color:rgb(0,200,0);')
            vline.setLineWidth(3)
            # 最上部========================================
            topBar = QHBoxLayout()
            icon = QPixmap(self.resource_path(self.icon_path)).scaled(30, 30)
            icon_area = QLabel()
            icon_area.setPixmap(icon)
            title = QLabel(self.appTitle + self.version)
            title.setStyleSheet('font-size:28px;')
            
            topBar.addWidget(icon_area)
            topBar.addWidget(title)
            topBar.addStretch()
            
            # 説明部========================================
            explainBar = QHBoxLayout()
            explainTxt = QLabel(
                'exit : Keasyを終了します\n'
                'find [検索ワード] : アカウントを検索します\n'
                'memorize [サービス名] [ユーザID/Mail] : '
                'IDとパスワードを一時記憶します．\n'
                '       Shiftキーを2回押すことで自動入力できます\n'
                'show : パスワード文字列を表示します\n'
                'hide : パスワードを伏せ字(*)で隠します\n'
                'add  : アカウントを登録します\n'
                'edit [サービス名] [ユーザID/Mail] [変更したい情報の種類] : '
                'アカウントを編集します\n'
                'delete [サービス名] [ユーザID/Mail] : アカウントを削除します\n'
                'master : マスターパスワードを変更します')
            self.fontSetter(explainTxt)
            explainBar.addWidget(explainTxt)
            
            # 区切り========================================
            hSeparater = QHBoxLayout()
            hSeparater.addWidget(hline)
            vSeparater = QHBoxLayout()
            vSeparater.addWidget(vline)
            
            # コマンド履歴部======================================
            historyBar = QHBoxLayout()
            historyMark = QLabel('$ ')
            self.fontSetter(historyMark)
            self.historyTxt = QLabel('aaa')
            self.fontSetter(self.historyTxt)
            historyBar.addWidget(historyMark)
            historyBar.addWidget(self.historyTxt)
            historyBar.addStretch()
            
            # コンソール部======================================
            commandBar = QHBoxLayout()
            self.console = QLineEdit()
            self.console.setMaxLength(60)
            if os_name == 'nt':
                self.console.setStyleSheet(
                    'font-family:MS Gothic;'
                    'font-size:18px;'
                    'color:rgb(0,255,0);'
                    'background:rgb(30,30,30);'
                    'border-style:solid;'
                    'border-width:1px;'
                    'border-color:rgb(0,150,0);')
            if os_name == 'posix':
                self.console.setStyleSheet(
                    'font-family:Monospace;'
                    'font-size:18px;'
                    'color:rgb(0,255,0);'
                    'background:rgb(30,30,30);'
                    'border-style:solid;'
                    'border-width:1px;'
                    'border-color:rgb(0,150,0);')
            # コマンドラインでEnterを押されたら，
            # 入力文字をreceiver関数に投げる
            # ※connectに直接関数を書いてもエラーを吐く
            #   無名関数lambdaとして書くと通る
            self.console.returnPressed.connect(
                lambda: self.cmdEvt.receiver(self.console.text()))
            tellMaxInput = QLabel(self.command_maxLengthTxt)
            self.fontSetter(tellMaxInput)
            tellMaxInput.setStyleSheet('font-size:16px;')
            self.myMode = QLabel()
            self.fontSetter(self.myMode)
            dollar = QLabel('$')
            self.fontSetter(dollar)
            commandBar.addWidget(self.myMode)
            commandBar.addWidget(dollar)
            commandBar.addWidget(self.console)
            commandBar.addWidget(tellMaxInput)
            
            # 応答部======================================
            responseBar = QHBoxLayout()
            responseMark = QLabel('>> ')
            responseMark.setAlignment(Qt.AlignTop)  # 上寄せ
            self.fontSetter(responseMark)
            self.responseTxt = QLabel()
            self.fontSetter(self.responseTxt)
            responseBar.addWidget(responseMark)
            responseBar.addWidget(self.responseTxt)
            responseBar.addStretch()
            
            # 表示部============================================
            resultArea = QHBoxLayout()
            self.resultTxt = QLabel()
            self.fontSetter(self.resultTxt)
            
            # DB検索結果の表
            self.resultTable = QTableWidget()
            # Tabキーでフォーカスさせない
            self.resultTable.setFocusPolicy(Qt.NoFocus)
            # 行と列は後で追加する
            self.resultTable.setColumnCount(0)
            self.resultTable.setRowCount(0)
            # 1行目headerを無効化
            hHeader = self.resultTable.horizontalHeader()
            hHeader.hide()
            # 1列目headerを無効化
            vHeader = self.resultTable.verticalHeader()
            vHeader.hide()
            
            # 表のフォントサイズと枠線色
            self.resultTable.setStyleSheet(
                'font-size:14px; gridline-color:"#555";')
            # 表のダブルクリックを無効化
            self.resultTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
            # 表の範囲選択＆選択時の色変更を無効化（選択セルのコピーは可能）
            self.resultTable.setSelectionMode(QAbstractItemView.NoSelection)
            # 表をクリックした場合の処理
            # self.resultTable.cellClicked.connect(self.myFunction)
            
            # 表の選択セルについて，文字と背景色を変更
            # tPalette = QPalette(self.resultTable.palette())
            # tPalette.setColor(QPalette.HighlightedText, QColor('#ccc'))
            # tPalette.setColor(QPalette.Highlight, QColor('#242'))
            # self.resultTable.setPalette(tPalette)  # 表に適用
            
            # resultArea.addWidget(self.resultTxt)
            resultArea.addWidget(self.resultTable)
            
            # レイアウト格納====================================
            mainLayout = QVBoxLayout()
            mainLayout.addLayout(topBar)
            mainLayout.addLayout(explainBar)
            mainLayout.addLayout(hSeparater)
            mainLayout.addLayout(historyBar)
            mainLayout.addLayout(commandBar)
            mainLayout.addLayout(responseBar)
            mainLayout.addLayout(hSeparater)
            mainLayout.addLayout(resultArea)
            # mainLayout.addStretch()  # 余白を埋める
            self.setLayout(mainLayout)
        except:
            traceback.print_exc()
