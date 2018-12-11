# -*- coding: utf-8 -*-
from CommandEvents import CommandEvents
import sys
from os import path as os_path, remove as os_remove
import traceback
# Keasy uses PyQT5 ver.5.9.
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QSystemTrayIcon, QLabel, QFrame, QTableWidget, QAbstractItemView
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt


class WindowGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.appTitle = 'Keasy'
        self.version = '2.0'
        self.icon_path = 'icon.png'
        self.icon = QIcon(self.resource_path(self.icon_path))
        self.icon2_path = 'icon2.png'
        self.icon2 = QIcon(self.resource_path(self.icon2_path))
        self.command_maxLengthTxt = '60字まで'
        self.tray_toolchipTxt = 'Ctrlキーを2回押すことで展開します'
        self.history = ['']  # コマンド履歴用
        self.setWindowTitle(self.appTitle)
        self.setWindowFlags(Qt.CustomizeWindowHint)  # タイトルバーを消す
        self.setMinimumSize(600, 500)
        self.setMaximumSize(1200, 800)
        self.savedMyGeometry = None  # タスクトレイ格納時のウィンドウサイズ
        self.setStyleSheet(
            'color:rgb(200,200,200);'
            'background:rgb(50,50,50);')
        # コマンド処理のインスタンス
        self.cmdEvt = CommandEvents()
        self.cmdEvt.setObj(self)
        self.cmdEvt.exitSIGNAL.connect(self.exitKeasy)
        # OSによって適用フォントを変える
        import platform
        MyOS = platform.system()
        if MyOS == 'Windows':
            MainFont = 'font-family:MS Gothic;font-size:14px;'
            ConsoleFont = 'font-family:MS Gothic;font-size:18px;'
        elif MyOS == 'Darwin':
            MainFont = 'font-family:Monospace;font-size:13px;'
            ConsoleFont = 'font-family:Monospace;font-size:16px;'
        else:
            MainFont = 'font-family:Monospace;font-size:14px;'
            ConsoleFont = 'font-family:Monospace;font-size:18px;'
        self.tray = QSystemTrayIcon()  # トレイアイコン（通知領域）
        self.initSystemTray(self.tray)  # トレイ設定
        self.initUI(MainFont, ConsoleFont)  # アプリの外観
        self.show()  # ウィンドウ表示
        # OSによってウィンドウ操作プログラムを変える
        import WindowController
        WindowController.controlWindow(self)
        self.cmdEvt.receiver('')  # 最初にパスワード認証させる

    # pyinstallerでexe/app化した後でも画像を使えるように絶対パスへ変更
    # Win/Macどちらも，この処理をしないと画像・アイコンが表示されない
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

    # autoComplete_singleで自動入力する対象を切り替える
    def switchMemorize(self):
        try:
            # completeTarget=
            # 0: ユーザID/Mail
            # 1:パスワード
            if self.cmdEvt.completeTarget == 0:
                self.cmdEvt.completeTarget = 1
                self.tray.setIcon(self.icon2)
            else:
                self.cmdEvt.completeTarget = 0
                self.tray.setIcon(self.icon)
            print(self.cmdEvt.completeTarget)
        except:
            traceback.print_exc()

    # 現在のmodeにおけるflag処理を1つ戻す
    def rollBack_at_flag(self):
        self.cmdEvt.shiftTabReceiver()

    # システムトレイ（通知領域）の設置
    def initSystemTray(self, tray):
        try:
            tray.setIcon(
                QIcon(self.resource_path(self.icon_path))
            )
            tray.setToolTip(self.tray_toolchipTxt)
            tray.show()
        except:
            traceback.print_exc()

    # コンソールに1文字入力される度に，その文字が使用可能か確認・修正する
    def checkConsoleText(self, text: str):
        if text == '':
            return
        txtList = list(text)
        newChar = txtList[-1]  # 最後の文字
        # パスワード入力かどうかで確認方法を変える
        if self.cmdEvt.currentFlag == self.cmdEvt.flag_PassWord:
            checked = self.passwordCheck(newChar)
        else:
            checked = self.newtralCheck(newChar)

        # 使用可能な文字だったら合格(何もしない)
        if checked:
            return

        # 使用不可能な文字なら消す
        del txtList[-1]
        fixedTxt = ''.join(txtList)
        self.changeConsoleText(fixedTxt)

    # 入力された文字がパスワードに使用可能か確認
    # True:使用可能
    # False:使用不可能
    def passwordCheck(self, newChar: str):
        checkTxt = 'abcdefghijklmnopqrstuvwxyz' \
                   'ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
                   '1234567890#$%&_'
        checkList = list(checkTxt)
        # 使用可能な文字のどれかに当てはまれば合格
        for char in checkList:
            if char == newChar:
                return True
        return False

    # 入力された文字がサービス名などに使用可能か確認
    # True:使用可能
    # False:使用不可能
    # 今の所は何を入力してもOK
    def newtralCheck(self, text: str):
        return True

    # コンソールの入力内容を変更
    def changeConsoleText(self, text: str):
        self.console.setText(text)

    # コマンドによる処理結果を表示
    def dispResponseText(self, txt: str):
        try:
            self.responseTxt.setText(txt)
        except:
            traceback.print_exc()

    # コマンドを送る度に，現在のモードを表示
    def dispMyMode(self, mode: str):
        self.myMode.setText(mode)

    # アプリ終了処理
    def exitKeasy(self):
        self.tray.hide()  # 通知領域にアイコンだけ残らないようにする
        # 復号化された状態のDBを削除
        if os_path.exists(self.cmdEvt.keasy_path):
            os_remove(self.cmdEvt.keasy_path)
        sys.exit()

    # コンソールの入力文字を伏せる
    def setConsoleMode_password(self):
        self.console.setEchoMode(QLineEdit.Password)

    # コンソールの入力文字を表示する
    def setConsoleMode_raw(self):
        self.console.setEchoMode(QLineEdit.Normal)

    # アプリUI設定
    def initUI(self, MainFont: str, ConsoleFont: str):
        try:
            hline = QFrame()
            hline.setFrameShape(QFrame.HLine)
            vline = QFrame()
            vline.setFrameShape(QFrame.VLine)
            vline.setStyleSheet('color:rgb(0,200,0);')
            vline.setLineWidth(3)
            # 最上部========================================
            topBar = QHBoxLayout()
            icon = QPixmap(
                self.resource_path(self.icon_path)).scaled(30, 30)
            self.icon_area = QLabel()
            self.icon_area.setPixmap(icon)
            title = QLabel(self.appTitle + self.version)
            title.setStyleSheet('font-size:28px;')
            topBar.addWidget(self.icon_area)
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
            explainTxt.setStyleSheet(MainFont)
            explainBar.addWidget(explainTxt)

            # 区切り========================================
            hSeparater = QHBoxLayout()
            hSeparater.addWidget(hline)
            vSeparater = QHBoxLayout()
            vSeparater.addWidget(vline)

            # コマンド履歴部======================================
            historyBar = QHBoxLayout()
            historyMark = QLabel('$ ')
            historyMark.setStyleSheet(MainFont)
            self.historyTxt = QLabel('aaa')
            self.historyTxt.setStyleSheet(MainFont)
            historyBar.addWidget(historyMark)
            historyBar.addWidget(self.historyTxt)
            historyBar.addStretch()

            # コンソール部======================================
            commandBar = QHBoxLayout()
            self.console = QLineEdit()
            self.console.setMaxLength(60)
            self.console.setStyleSheet(
                ConsoleFont +
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
            self.console.textChanged.connect(
                lambda: self.checkConsoleText(self.console.text()))
            tellMaxInput = QLabel(self.command_maxLengthTxt)
            tellMaxInput.setStyleSheet(MainFont)
            tellMaxInput.setStyleSheet('font-size:16px;')
            self.myMode = QLabel()
            self.myMode.setStyleSheet(MainFont)
            dollar = QLabel('$')
            dollar.setStyleSheet(MainFont)
            commandBar.addWidget(self.myMode)
            commandBar.addWidget(dollar)
            commandBar.addWidget(self.console)
            commandBar.addWidget(tellMaxInput)

            # 応答部======================================
            responseBar = QHBoxLayout()
            responseMark = QLabel('>> ')
            responseMark.setAlignment(Qt.AlignTop)  # 上寄せ
            responseMark.setStyleSheet(MainFont)
            self.responseTxt = QLabel()
            self.responseTxt.setStyleSheet(MainFont)
            responseBar.addWidget(responseMark)
            responseBar.addWidget(self.responseTxt)
            responseBar.addStretch()

            # 表示部============================================
            resultArea = QHBoxLayout()
            self.resultTxt = QLabel()
            self.resultTxt.setStyleSheet(MainFont)

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
