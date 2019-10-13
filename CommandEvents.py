# -*- coding: utf-8 -*-
from Database import Database
from AES_Cipher_SQLite import AES_Cipher_SQLite
import re
import os
import random
import traceback
import csv
# Keasy uses PyQt5 ver.5.9.
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import pyqtSignal, QObject


class CommandEvents(QObject):
    exitSIGNAL = pyqtSignal()  # exitコマンドのシグナル
    
    def __init__(self):
        super().__init__()
        try:
            # DBや暗号ファイルへのパス
            self.keasy_path = './keasy.db'
            self.encryptedKeasy_path = './encrypted.keasy'
            self.db = Database()  # データベース
            self.MasterPassword = ''  # DBのマスターパスワード
            # ================ モード ===============
            self.mode_none = 'none'
            self.mode_confirmMaster = 'confirmMaster'
            self.mode_auth = 'auth'
            self.mode_find = 'find'
            self.mode_add = 'add'
            self.mode_edit = 'edit'
            self.mode_delete = 'delete'
            self.mode_memorize = 'memorize'
            self.mode_csv = 'csv'
            self.mode_master = 'master'
            # add/edit/delete modeのフラグ =====================
            self.flag_none = 'none'  # 各モードに最初に入った時
            self.flag_ServiceName = 'serviceName'  # add, edit, delete
            self.flag_SearchWord = 'searchWord'  # add, edit
            self.flag_LoginURL = 'loginURL'  # add, edit
            self.flag_ID_or_Mail = 'userIDorMail'  # add, edit, delete
            self.flag_PassWord = 'passWord'  # add, edit, master
            self.flag_RandomPassWord = 'randomPassWord'  # add, edit
            self.flag_Remarks = 'remarks'  # add, edit
            self.flag_Both = 'both'  # delete
            # 既存サービスならsearchWordとログインページURLをスキップ
            self.existServiceFlag = False
            # ランダムパスワード生成のオプション
            self.randomPass_option_c = 'c'  # 大文字を含む
            self.randomPass_option_f = 'f'  # 数字を含む
            self.randomPass_option_s = 's'  # 記号(#$%&_)を含む
            
            # ================ コマンド ===============
            self.cmd_exit = 'exit'
            self.cmd_find = 'find'
            self.cmd_show = 'show'
            self.cmd_hide = 'hide'
            self.cmd_add = 'add'
            self.cmd_edit = 'edit'
            self.cmd_delete = 'delete'
            self.cmd_memorize = 'memorize'
            self.cmd_master = 'master'
            self.cmd_csv = 'csv'
            # exit以外のコマンド集合
            self.cmdSet = [
                self.cmd_find,
                self.cmd_show,
                self.cmd_hide,
                self.cmd_add,
                self.cmd_edit,
                self.cmd_delete,
                self.cmd_memorize,
                self.cmd_csv
            ]
            
            self.currentMode = self.mode_none  # 現在の状態
            self.currentFlag = self.flag_none  # 現在のモード内フラグ
            self.asteriskFlag = True  # パスワードを伏せ字にするフラグ
            # memorizeで記憶するID & pass
            self.MemorizeDict = {'user': '', 'pass': ''}
            # 片方を自動入力する場合の対象
            # 0:ユーザID/Mail 1:パスワード
            self.completeTarget = 0
            self.displayableList = []  # findで得た結果データ
            self.editableRecord = []  # editで編集するデータ行
            self.deletableServiceID = 0  # deleteで削除するデータのID
            self.deletableAccountNum = 0  # deleteで削除するデータの番号
            
            # addコマンドで追加する情報を一時的に格納====================
            self.reg_serviceID = 0
            self.reg_ServiceName = ''
            self.reg_SearchWord = ''
            self.reg_LoginURL = ''
            self.reg_ID_or_Mail = ''
            self.reg_PassWord = ''
            self.reg_Remarks = ''
        except:
            traceback.print_exc()
    
    # ウィンドウを操作するためのインスタンス保持
    def setObj(self, gui):
        """
        :type gui: PyQt5.WindowGUI.WindowGUI
        """
        try:
            self.gui = gui
        except:
            traceback.print_exc()
    
    # GUIの応答部に文章を表示
    def response(self, text: str):
        self.gui.dispResponseText(text)
    
    # 一時記憶したユーザID/Mailとパスワードを渡す
    # ['user':, 'pass':]
    def getMemorize(self) -> dict:
        return self.MemorizeDict
    
    # URLから予測できたユーザID/Mailとパスワードを一時保存
    def setMemorize(self, Service: str, ID: str, Pass: str):
        self.MemorizeDict['user'] = str(ID)
        self.MemorizeDict['pass'] = str(Pass)
        self.response(
            'URLから予測 -> '
            + Service + ' : '
            + self.MemorizeDict['user'] +
            '\nShiftキーを2回押すことで自動入力できます．'
        )
    
    # ブラウザが最前面にある時にCtrl+(Shift 2回)を押されたら，
    # URLが一致するアカウントを自動で探す
    # アカウントが1つだけ該当した場合に限りTrueを返す:
    #   ユーザID/Mailとパスワードを自動入力させる
    # それ以外ならFalseを返す:タスクトレイから自動展開する
    def autoFindByURL(self, URL: str) -> dict:
        return self.db.getIDandPassByURL(URL)
    
    # ==================================================================
    # Tabキーが押された時点の入力内容を受け取って処理
    def tabReceiver(self, text: str):
        cmdList = text.split(' ')  # コマンドをスペース毎に分割
        complementedCmd = self.complementCommand(cmdList[0])
        
        # 主コマンドのみの入力なら，主コマンドの補完
        if len(cmdList) == 1:
            self.gui.changeConsoleText(complementedCmd)
        
        # response text when create random password
        textForRandomPassWord = \
            'ランダム生成する文字数を入力してください．' \
            '1字～64字まで生成できます．\n' \
            'また，副コマンドに以下のオプションを使用できます．\n' \
            '複数のオプションを使用する場合は，' \
            '空白を開けずに続けて入力してください．\n' \
            '[c]:大文字を含む [f]:数字を含む [s]:記号#$%&_を含む'
        
        # add mode: serviceName入力時
        if self.currentMode == self.mode_add \
                and self.currentFlag == self.flag_ServiceName:
            self.tabComplement_add_serviceName(cmdList)
        # add mode: passWord入力時
        elif self.currentMode == self.mode_add \
                and self.currentFlag == self.flag_PassWord:
            self.currentFlag = self.flag_RandomPassWord
            self.response(textForRandomPassWord)
        # edit mode: password入力時
        elif self.currentMode == self.cmd_edit and \
                self.currentFlag == self.flag_PassWord:
            # ランダムパスワード生成へ移行
            self.currentFlag = self.flag_RandomPassWord
            self.response(textForRandomPassWord)
        # editが主コマンドに入力されている場合
        elif complementedCmd == self.cmd_edit:
            self.tabComplement_edit(cmdList)  # 入力文字の補完
        # deleteが主コマンドに入力されている場合
        elif complementedCmd == self.cmd_delete:
            self.tabComplement_delete(cmdList)
        # memorizeが主コマンドに入力されている場合
        elif complementedCmd == self.cmd_memorize:
            # delete用の補完処理を流用
            # ※対象が同じ[サービス名]と[ユーザID/Mail]だから
            self.tabComplement_delete(cmdList)
        else:
            pass
    
    # add modeのserviceName入力時にTabキーを押された場合の処理
    # 入力文字から始まるserviceNameを探して補完する
    def tabComplement_add_serviceName(self, cmdList: list):
        complementedList = self.complementServiceName(cmdList[0])
        if complementedList == []:
            return
        
        complementedServiceName = complementedList[1]
        # コンソールの入力文字を補完
        self.gui.changeConsoleText(complementedServiceName)
    
    # edit modeでTabキーを押された場合の処理
    # 今指定している要素について，入力文字から始まるデータを探して補完する
    def tabComplement_edit(self, cmdList: list):
        checkedList = self.checkComplementable_edit(cmdList)
        # 補完できなかったら空リストが返ってくるので補完中止
        if checkedList == []:
            return
        
        # 空リストでないなら要素が入っているため判定はしない
        # 1文字列中に主コマンド・副コマンド群の形で入れる
        for i in range(len(checkedList)):
            checkedList[i] = str(checkedList[i])
            if i == 0:
                complementedText = checkedList[i]
            else:
                complementedText = ' '.join([complementedText, checkedList[i]])
        
        # コンソールの入力文字を補完
        self.gui.changeConsoleText(complementedText)
    
    # When Tab key is pressed at delete mode
    # complement entered serviceName or userIDorMail with forward match
    # delete modeでTabキーが押されたら，
    # 入力文字から始まるサービス名・ユーザID/Mailを補完
    def tabComplement_delete(self, cmdList: list):
        # print(cmdList)
        if len(cmdList) < 2 or len(cmdList) > 3:
            return
        try:
            for i in range(len(cmdList)):
                cmdList[i] = str(cmdList[i])
            # serviceName入力時=================================
            serviceIDandName = self.complementServiceName(cmdList[1])
            if serviceIDandName == []:
                return
            
            serviceID = serviceIDandName[0]
            serviceName = serviceIDandName[1]
            # サービス名だけが入力されていた場合，
            # サービス名の削除確認
            if len(cmdList) == 2:
                cmdList[1] = str(serviceName)
                complementedText = ' '.join(cmdList)
                self.gui.changeConsoleText(complementedText)
                return
            
            # ユーザID/メールアドレス入力時=========================
            accountNums = self.db.getAccountNums_from_AccountsTable(
                serviceID, cmdList[2])
            
            if len(accountNums) != 1:
                return
            
            AccountNumber = accountNums[0]
            AccountData = self.db.getAccount_from_AccountsTable(AccountNumber)
            if len(AccountData) != 1:
                return
            
            IDorMail = AccountData[0]['userIDorMail']
            cmdList[2] = str(IDorMail)
            complementedText = ' '.join(cmdList)
            self.gui.changeConsoleText(complementedText)
        except:
            traceback.print_exc()
    
    # 引数のリスト要素数に応じて[serviceName], [ID/Mail], [変更したい情報]を
    # 補完できるか確認．補完可能なら，最後の要素を補完したリストを返す
    # ※返すリストは[0]コマンド, [1]serviceName, [2]ID/Mail, [3]変更したい情報
    # 補完できないなら空のリストを返す
    # ※serviceNameの補完時，searchWordの前方一致に引っかかっても補完されてしまう
    def checkComplementable_edit(self, cmdList: list):
        # cmdListは[コマンド], [サービス名], [ID/Mail], [変更したい情報]
        if len(cmdList) > 1:
            targetInput = cmdList[1]  # 入力したサービス名
        complementedCommands = []
        # serviceName入力時=================================
        if len(cmdList) == 2:
            ServiceID_and_ServiceName = self.complementServiceName(targetInput)
            # リストに値が入っているなら，serviceNameを補完
            if ServiceID_and_ServiceName != []:
                complementedServiceName = ServiceID_and_ServiceName[1]
                complementedCommands = [cmdList[0], complementedServiceName]
            else:
                return complementedCommands  # 空リストを返す
            
            return complementedCommands
        
        # ユーザID/メールアドレス入力時=========================
        elif len(cmdList) == 3:
            # まずserviceNameが補完できるか確認
            ServiceID_and_ServiceName = self.complementServiceName(targetInput)
            # リストに値が入っているなら，serviceIDを取得
            if ServiceID_and_ServiceName != []:
                serviceID = ServiceID_and_ServiceName[0]
            else:
                return complementedCommands  # 空リストを返す
            
            # ユーザID/メールアドレスが補完できるか確認
            IDorMail = cmdList[2]
            accountNums = self.db.getAccountNums_from_AccountsTable(
                serviceID, IDorMail)
            # 該当するユーザID/Mailが2以上または0なら補完中止，空リストを返す
            if len(accountNums) != 1:
                return complementedCommands
            
            Account = self.db.getAccount_from_AccountsTable(accountNums[0])
            
            # print(Account)
            complementedIDorMail = Account[0]['userIDorMail']
            complementedCommands = [
                cmdList[0], cmdList[1], complementedIDorMail
            ]
            
            return complementedCommands
        
        # 「どの情報を変更するか」の入力時===========================
        elif len(cmdList) == 4:
            # まずserviceNameが補完できるか確認
            ServiceID_and_ServiceName = self.complementServiceName(targetInput)
            # リストに値が入っているなら，serviceIDを取得
            if ServiceID_and_ServiceName != []:
                serviceID = ServiceID_and_ServiceName[0]
            else:
                return complementedCommands  # 空リストを返す
            
            # ユーザID/メールアドレスが補完できるか確認
            IDorMail = cmdList[2]
            accountNums = self.db.getAccountNums_from_AccountsTable(
                serviceID, IDorMail)
            # 該当するユーザID/Mailが2以上または0なら補完中止，空リストを返す
            if len(accountNums) != 1:
                return complementedCommands
            
            lastElement = cmdList[3]  # 入力中の要素
            # 変更できる情報の選択肢
            choices = [self.flag_ServiceName,
                       self.flag_SearchWord,
                       self.flag_LoginURL,
                       self.flag_ID_or_Mail,
                       self.flag_PassWord,
                       self.flag_Remarks]
            # 入力文字が正規表現でなければ補完中止
            if not self.re_check(lastElement):
                return complementedCommands
            
            # 入力中の文字から始まる選択肢が1つだけ見つかれば，
            # その選択肢に補完する（大文字小文字を問わない）
            # 2つ以上見つかったら補完中止
            foundChoice = ''
            for i in range(len(choices)):
                if re.search('^' + lastElement, choices[i], re.IGNORECASE):
                    if foundChoice != '':
                        return complementedCommands
                    else:
                        foundChoice = choices[i]
            
            # 1つも見つからなかったら補完中止
            if foundChoice == '':
                return complementedCommands
            
            # [コマンド], [ユーザ名], [ID/Mail], [変更したい情報]
            complementedCommands = [cmdList[0], cmdList[1], cmdList[2],
                                    foundChoice]
            
            return complementedCommands  # 正常に返される
        else:
            return complementedCommands  # 空リストを返す
    
    # 引数の文字列(入力文字)からserviceNameを補完できるか探す
    # 文字列から始まるserviceNameがあるかだけ探す．searchWordからは探さない
    # 1つだけ見つかれば，[0]:serviceID, [1]:serviceName のリストを返す
    # 2つ以上見つかる/無い場合は補完不可能→空リストを返す
    def complementServiceName(self, text: str):
        services = self.db.getServices_from_ServiceTable(
            text, 'forward', False)
        # 全て同じserviceNameの情報か確認(1種類に絞り込めているか)
        # 別のserviceNameの情報があれば補完中止
        serviceID_and_serviceName = []
        if len(services) == 1:
            serviceID = services[0]['serviceID']
            serviceName = services[0]['serviceName']
            serviceID_and_serviceName = [serviceID, serviceName]
        
        return serviceID_and_serviceName
    
    # 引数のserviceIDと文字列を使って，accountsテーブルから検索
    # 1つだけ見つかれば，そのユーザID/Mailを返す
    # 2つ以上見つかる/無い場合は空欄''を返す
    def complementIDorMail(self, serviceID: int, text: str):
        complementedID_or_Mail = ''
        # 入力文字が正規表現でなければ補完中止
        if not self.re_check(text):
            return complementedID_or_Mail
        
        # 該当するユーザID/メールアドレスが1つだけか確認
        # 大文字/小文字は区別しない
        accounts = self.db.getAccountNums_from_AccountsTable(serviceID, text)
        # 1つだけ見つかったら，ユーザID/Mailを補完
        if len(accounts) == 1:
            accountNum = accounts[0]
            Account = self.db.getAccount_from_AccountsTable(accountNum)
            complementedID_or_Mail = Account[0]['userIDorMail']
        
        return complementedID_or_Mail
    
    # Shift+Tabキーが押された時，そのmode内でのflag処理を1つ戻す
    def shiftTabReceiver(self):
        # add modeでのShift+Tab戻り
        if self.currentMode == self.mode_add:
            # add mode中止
            if self.currentFlag == self.flag_ServiceName:
                self.currentMode = self.mode_find
                self.currentFlag = self.flag_none
                self.response('addコマンド操作を中止しました．')
            # serviceName入力に戻る
            elif self.currentFlag == self.flag_SearchWord:
                self.currentFlag = self.flag_ServiceName
                self.reg_ServiceName = ''
                self.addFlag_none([])
            # searchWord入力に戻る
            elif self.currentFlag == self.flag_LoginURL:
                # 既存serviceNameならsearchWord入力を飛ばして戻る
                if self.existServiceFlag:
                    self.currentFlag = self.flag_ServiceName
                    self.reg_ServiceName = ''
                    self.addFlag_none([])
                # 新規serviceNameなら，searchWord入力に戻る
                else:
                    self.currentFlag = self.flag_SearchWord
                    self.reg_LoginURL = ''
                    # searchWordは要素追加方式なので最初に初期化する
                    self.reg_SearchWord = ''
                    self.addFlag_ServiceName(self.reg_ServiceName, [])
            # ログインページURL入力に戻る
            elif self.currentFlag == self.flag_ID_or_Mail:
                # 既存serviceNameならログインページURL入力を飛ばして戻る
                # searchWord入力も飛ばして戻る
                if self.existServiceFlag:
                    self.currentFlag = self.flag_ServiceName
                    self.reg_ServiceName = ''
                    self.addFlag_none([])
                # 新規serviceNameなら，ログインページURL入力に戻る
                else:
                    self.currentFlag = self.flag_LoginURL
                    self.reg_ID_or_Mail = ''
                    self.addFlag_SearchWord('', [])
            # ユーザIDorメールアドレス入力に戻る
            elif self.currentFlag == self.flag_PassWord or \
                    self.currentFlag == self.flag_RandomPassWord:
                self.currentFlag = self.flag_ID_or_Mail
                self.reg_PassWord = ''
                self.addFlag_LoginURL(self.reg_LoginURL, [])
            # パスワード入力に戻る
            elif self.currentFlag == self.flag_Remarks:
                self.currentFlag = self.flag_PassWord
                self.reg_Remarks = ''
                self.addFlag_ID_or_Mail(self.reg_ID_or_Mail, [])
            else:
                pass
        # edit modeでのShift+Tab戻り
        elif self.currentMode == self.mode_edit:
            self.currentMode = self.mode_find
            self.currentFlag = self.flag_none
            self.response(
                '編集を中止しました．'
            )
        else:
            pass
        
        # 現在のモードを表示
        self.gui.dispMyMode(self.currentMode)
    
    # =======================================================
    # コマンドを受け取って処理
    def receiver(self, receivedCmd):
        try:
            cmdList = receivedCmd.split(' ')  # コマンドをスペース毎に分割
            # コマンド数に応じて主コマンドと副コマンドに分ける
            if len(cmdList) >= 2:
                cmdMain = cmdList[0]
                del cmdList[0]
                cmdSub = cmdList
            else:
                cmdMain = cmdList[0]
                cmdSub = []
            
            # debug======================
            # print('Main: ' + cmdMain, end=' ')
            # print('Sub: ', end=' ')
            # print(cmdSub)
            # ===========================
            
            # 主コマンドや副コマンドに全角スペースがある場合
            if re.search('　', cmdMain) != None:
                self.gui.responseTxt.setText(
                    '全角文字の空白は入力できません')
                self.gui.console.clear()
                return
            elif len(cmdSub) > 0:
                for i in range(len(cmdSub)):
                    if re.search('　', cmdSub[i]) != None:
                        self.gui.responseTxt.setText(
                            '全角文字の空白は入力できません')
                        self.gui.console.clear()
                        return
            
            # exitコマンドならアプリ終了させる
            if cmdMain == self.cmd_exit:
                self.exitSIGNAL.emit()
            
            # find modeの時だけmode変更
            if self.currentMode == self.mode_find:
                # find modeでのみコマンド補完を行う
                # (他モードではそっちで決めた処理をする)
                complementedCmd = self.complementCommand(cmdMain)
                # show/hideコマンドならパスワード表示の処理へ
                if complementedCmd == self.cmd_show:
                    self.cmdAction_ShowPassword(cmdSub)
                    self.gui.console.clear()
                    self.gui.historyTxt.setText(complementedCmd)
                    return
                elif complementedCmd == self.cmd_hide:
                    self.cmdAction_HidePassword(cmdSub)
                    self.gui.console.clear()
                    self.gui.historyTxt.setText(complementedCmd)
                    return
                # 他のコマンドならモード変更
                elif complementedCmd == self.cmd_find:
                    self.currentMode = self.mode_find
                elif complementedCmd == self.cmd_add:
                    self.currentMode = self.mode_add
                elif complementedCmd == self.cmd_edit:
                    self.currentMode = self.mode_edit
                elif complementedCmd == self.cmd_delete:
                    self.currentMode = self.mode_delete
                elif complementedCmd == self.cmd_memorize:
                    self.currentMode = self.mode_memorize
                elif complementedCmd == self.cmd_csv:
                    self.currentMode = self.mode_csv
                # "master"は補完されないが全文一致することで起動
                elif complementedCmd == self.mode_master:
                    self.currentMode = self.mode_master
                # どのコマンドも違うならコマンドエラー
                else:
                    self.response(
                        'コマンドが違います：' + complementedCmd
                    )
                    # コンソール文字を除去＆コマンド履歴を表示
                    self.gui.console.clear()
                    self.gui.historyTxt.setText(complementedCmd)
                    return
            
            # modeによって処理を変える=======================
            if self.currentMode == self.mode_none:
                self.noneMode()
            elif self.currentMode == self.mode_confirmMaster:
                self.confirmMasterPassWord(cmdMain, cmdSub)
            # パスワード入力時のみ，コマンド履歴を表示しない
            elif self.currentMode == self.mode_auth:
                self.authenticationMode(cmdMain, cmdSub)
                self.gui.console.clear()
                self.gui.dispMyMode(self.currentMode)  # 現在のモードを表示
                return
            elif self.currentMode == self.mode_find:
                self.cmdAction_findMode(cmdSub)
            elif self.currentMode == self.mode_add:
                self.cmdAction_addMode(cmdMain, cmdSub)
            elif self.currentMode == self.mode_edit:
                self.cmdAction_editMode(cmdMain, cmdSub)
            elif self.currentMode == self.mode_delete:
                self.cmdAction_deleteMode(cmdMain, cmdSub)
            elif self.currentMode == self.mode_memorize:
                self.cmdAction_memorizeMode(cmdSub)
            elif self.currentMode == self.mode_csv:
                self.cmdAction_csvMode(cmdSub)
            elif self.currentMode == self.mode_master:
                self.cmdAction_masterMode()
            else:
                pass
            # コンソール文字を除去＆コマンド履歴を表示
            self.gui.console.clear()
            self.gui.historyTxt.setText(receivedCmd)
            self.gui.dispMyMode(self.currentMode)  # 現在のモードを表示
        
        except:
            traceback.print_exc()
    
    # 正規表現として正しければTrueを，誤っていればFalseを返す
    def re_check(self, string):
        try:
            re.compile(string)
            return True
        except re.error:
            pass  # 例外を出させない
        return False
    
    # コマンドが一意に予測できれば，自動補完したコマンドを返す
    # 予測できなければ，引数で受け取ったコマンドをそのまま返す
    def complementCommand(self, cmd):
        count = False
        result = str(cmd)
        # 正規表現が正しければ補完処理へ，誤っていれば補完中止
        if self.re_check(cmd):
            pass
        else:
            return result
        # 利用可能なコマンド群のうち，予測できるコマンドがあれば自動補完
        # ただし予測できるコマンドが2つ以上ある場合は補完しない
        for ableCmd in self.cmdSet:
            if re.search('^' + cmd, ableCmd) != None:
                if count:
                    return cmd
                else:
                    count = True
                    result = ableCmd
        return result
    
    # Keasyを最初に開いた場合の処理
    def noneMode(self):
        try:
            # 暗号化DBがあれば開くための認証を行う
            if os.path.exists(self.encryptedKeasy_path):
                self.response(
                    'データベースを開くためのパスワードを入力してください．'
                )
                self.currentMode = self.mode_auth
                self.gui.setConsoleMode_password()
            # 暗号化DBが無ければ，
            # 新規作成されたDBをマスターパスワードで暗号化する
            else:
                self.response(
                    'データベースを暗号化するための'
                    'マスターパスワードを入力してください．\n'
                    '半角英数字，大文字，記号を使用できます．'
                )
                self.currentMode = self.mode_confirmMaster
        except:
            traceback.print_exc()
    
    # マスターパスワードの設定
    def confirmMasterPassWord(self, cmdMain, cmdSub):
        try:
            if len(cmdSub) > 0:
                self.response(
                    'マスターパスワードにスペースは使えません．'
                )
                return
            elif len(cmdMain) > 16:
                self.response(
                    'マスターパスワードは16文字まで使用できます．'
                )
                return
            else:
                pass
            
            self.MasterPassword = cmdMain
            self.encryptDB()  # DBをマスターパスワードで暗号化
            self.currentMode = self.mode_auth
            self.gui.setConsoleMode_password()
            self.response(
                'データベースをマスターパスワードで暗号化しました．\n'
                'もう一度マスターパスワードを入力してログインしてください．'
            )
        except:
            traceback.print_exc()
    
    # DBを暗号化して暗号ファイル作成
    def encryptDB(self):
        try:
            # 送ったパスワードを暗号化・復号化に用いる
            cipherDB = AES_Cipher_SQLite(self.MasterPassword)
            
            # バイナリモードでDBファイル読み込み
            with open(self.keasy_path, "rb") as fileData:
                # DBファイルのバイナリ取得(エンコードはutf16)
                contents = fileData.read()
                # print('===binary Data===')
                # print(contents)
                pass
            
            # AES暗号化
            encrypted = cipherDB.AES_Encryption(contents)
            # print('===after Encryption===')
            # print(encrypted)
            
            # バイナリモードで暗号ファイルを作成
            with open(self.encryptedKeasy_path, "wb") as fileData:
                # 暗号化されたDBバイナリデータ(16バイト刻み)を書き込み
                fileData.write(encrypted)
        except:
            traceback.print_exc()
    
    def decryptDB(self):
        try:
            # 送ったパスワードを暗号化・復号化に用いる
            cipherDB = AES_Cipher_SQLite(self.MasterPassword)
            
            # バイナリモードで暗号ファイルを読み込み
            with open(self.encryptedKeasy_path, "rb") as fileData:
                # DBファイルのバイナリ取得(エンコードはutf16)
                cipher_data = fileData.read()
            
            # AES復号化
            decrypted = cipherDB.AES_Decryption(cipher_data)
            # print('===after Decryption===')
            # print(decrypted)
            
            # バイナリモードでDBファイル(復号化したほう)を上書き
            with open(self.keasy_path, "wb") as fileData:
                # 暗号化されたDBバイナリデータ(16バイト刻み)を書き込み
                fileData.write(decrypted)
        except:
            traceback.print_exc()
    
    # マスターパスワードの認証(DB接続確認)
    def authenticationMode(self, cmdMain: str, cmdSub: str):
        try:
            if len(cmdSub) > 0:
                self.response(
                    'マスターパスワードにスペースは使えません．'
                )
                return
            elif len(cmdMain) > 16:
                self.response(
                    'マスターパスワードは16文字まで使用できます．'
                )
                return
            else:
                pass
            
            self.MasterPassword = cmdMain
            self.decryptDB()  # DBを入力パスワードで復号化
            if not self.db.checkDB():
                self.response(
                    'マスターパスワードが違います．'
                )
                return
            
            self.response(
                'ようこそKeasyへ．コマンドを入力してください．'
            )
            self.currentMode = self.mode_find
            self.gui.setConsoleMode_raw()
        except:
            traceback.print_exc()
    
    # ========================================================
    # パスワードの表示/伏せ字
    def cmdAction_ShowPassword(self, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                'showコマンドは単体で動作します．\n'
                'スペースを入力しないでください．'
            )
        else:
            self.asteriskFlag = False
            self.response(
                'パスワードを表示します．'
                '伏せたい場合はhideコマンドを使います．'
            )
            # 応答部の表に出していたデータを再表示
            if self.displayableList:
                self.displayServices(self.displayableList)
    
    def cmdAction_HidePassword(self, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                'hideコマンドは単体で動作します．\n'
                'スペースを入力しないでください．'
            )
        else:
            self.asteriskFlag = True
            self.response(
                'パスワードを伏せます．'
                '表示したい場合はshowコマンドを使います．'
            )
            # 応答部の表に出していたデータを再表示
            if self.displayableList:
                self.displayServices(self.displayableList)
    
    # ========================================================
    # serviceNameやIDを検索
    def cmdAction_findMode(self, cmdSub: list):
        try:
            # 副コマンドが多すぎる場合
            if len(cmdSub) >= 2:
                self.response(
                    'searchWordが多すぎます．'
                    'searchWordは1語だけ入力してください．'
                )
                return
            # 副コマンド空欄の場合("find "など)
            elif len(cmdSub) == 1 and cmdSub[0] == '':
                self.response(
                    'searchWordを入力してください（例：find nihon）'
                )
                return
            # 副コマンドがない場合
            # DB内の全アカウントを表示
            elif len(cmdSub) == 0:
                self.displayableList = self.db.getAll_from_AccountsTable()
                if self.displayableList:
                    self.displayServices(self.displayableList)
                # serviceNameがいくつ見つかったか応答
                self.response(
                    '登録されているアカウント: ' +
                    str(len(self.displayableList)) + '件'
                )
                return
            else:
                pass
            # findが正しく使われたとみなし，DBを検索=====================
            self.db.getAllAccounts()  # デバッグ用
            self.displayableList = self.db.getServices_from_ServiceTable(
                cmdSub[0])
            
            # 1つだけserviceNameが見つかったら，
            # そのサービスのユーザID/Mail,パスワード，備考を表示する
            if len(self.displayableList) == 1:
                serviceName = self.displayableList[0]['serviceName']
                searchWord = self.displayableList[0]['searchWord']
                loginURL = self.displayableList[0]['LoginURL']
                # サービスに紐付けられた全アカウント取得
                accountNums = self.db.getAccounts_from_AccountsTable(
                    self.displayableList[0]['serviceID']
                )
                Accounts = []
                self.displayableList = []
                for i in range(len(accountNums)):
                    Accounts.append(
                        self.db.getAccount_from_AccountsTable(accountNums[i])
                    )
                    # アカウントごとに必要なデータを抜き出し
                    self.displayableList.append(dict(zip(
                        ['serviceName', 'searchWord', 'userIDorMail',
                         'passWord', 'remarks', 'LoginURL'],
                        [serviceName, searchWord,
                         Accounts[i][0]['userIDorMail'],
                         Accounts[i][0]['passWord'],
                         Accounts[i][0]['remarks'], loginURL]
                    )))
            
            # if self.displayableList:
            # print('displayList: ', end='')
            # print(self.displayableList)
            self.displayServices(self.displayableList)
            
            # serviceNameがいくつ見つかったか応答
            self.response(
                '検索結果: ' + str(len(self.displayableList)) + '件'
            )
        except:
            traceback.print_exc()
    
    # findコマンドの結果をGUI応答部に表示
    def displayServices(self, foundAccounts: list):
        try:
            # print('==========================')
            # print('foundAccounts: ', end='')
            # print(foundAccounts)
            self.gui.resultTable.clear()  # まず表示を全て消去
            # 1行0列からやり直す
            self.gui.resultTable.setRowCount(1)
            self.gui.resultTable.setColumnCount(0)
            # 表示すべきアカウントが無ければ中止
            if foundAccounts == []:
                return
            
            # 1行目header ============================
            # key:辞書キー名，value:キーに対応する値
            for col, (key, value) in enumerate(foundAccounts[0].items()):
                self.gui.resultTable.insertColumn(col)
                self.gui.resultTable.setItem(
                    0, col, QTableWidgetItem(key))
            
            # 2行目から検索結果 ======================
            serviceName = ''
            searchWord = ''
            loginURL = ''
            for row in range(len(foundAccounts)):
                # 結果の行数分だけ表に行を追加
                self.gui.resultTable.insertRow(row + 1)
                # 列ごとに結果を埋めていく
                # key:辞書キー名，value:キーに対応する値
                for col, (key, value) in enumerate(foundAccounts[row].items()):
                    # 同じserviceNameは連続で表示せず，
                    # 違うserviceNameに変わった時に1度だけ表示させる
                    value = str(value)
                    if key == 'serviceName':
                        if value == serviceName:
                            pass
                        else:
                            serviceName = value
                            self.gui.resultTable.setItem(
                                row + 1, col, QTableWidgetItem(value)
                            )
                    # 同じsearchWordは連続で表示せず，
                    # 違うsearchWordに変わった時に1度だけ表示させる
                    elif key == 'searchWord':
                        if value == searchWord:
                            pass
                        else:
                            searchWord = str(value)
                            self.gui.resultTable.setItem(
                                row + 1, col, QTableWidgetItem(value)
                            )
                    # 同じログインページURLは連続で表示せず，
                    # 違うログインページURLに変わった時に1度だけ表示させる
                    elif key == 'LoginURL':
                        if value == loginURL:
                            pass
                        else:
                            loginURL = str(value)
                            self.gui.resultTable.setItem(
                                row + 1, col, QTableWidgetItem(value)
                            )
                    # asteriskFlag=Trueならパスワードを伏せ字(*)で表示する
                    elif key == 'passWord' and self.asteriskFlag:
                        self.gui.resultTable.setItem(
                            row + 1, col, QTableWidgetItem(
                                self.changeAsterisks(str(value))
                            )
                        )
                    # other case, display value
                    # translate value to str because
                    # QTableWidgetItem doesn't display int values
                    else:
                        self.gui.resultTable.setItem(
                            row + 1, col, QTableWidgetItem(str(value))
                        )
            # セル内の文字数に合わせてセル幅を変更
            self.gui.resultTable.resizeColumnsToContents()
        except:
            traceback.print_exc()
    
    # パスワード文字列を，同じ文字数の伏せ字(*)に変えて返す
    def changeAsterisks(self, password: str):
        result = ""
        # chars = list(password)
        for i in range(len(password)):
            result += '*'
        return result
    
    # ランダムパスワードを生成
    # return: str / exception -> return: str ''
    def createRandomPassWord(self, cmdMain: str, cmdSub: list):
        result = ''
        try:
            Case_option = False
            Figure_option = False
            Symbol_option = False
            
            wordCount = int(cmdMain)  # intでなかったらValueErrorを取得
            
            # 空欄でEnterキーを押された場合
            if cmdMain == '':
                return result
            # 副コマンドが2個以上の場合
            elif len(cmdSub) > 1:
                return result
            elif len(cmdSub) == 1:
                chars = list(cmdSub[0])
                
                # オプションに対応する字か判定
                # 対応するオプションをTrueにする
                # 同じ字が2つ以上ある/対応の無い字があればランダム生成中止
                for i in range(len(chars)):
                    if chars[i] == self.randomPass_option_c:
                        if Case_option:
                            return result
                        else:
                            Case_option = True
                    elif chars[i] == self.randomPass_option_f:
                        if Figure_option:
                            return result
                        else:
                            Figure_option = True
                    elif chars[i] == self.randomPass_option_s:
                        if Symbol_option:
                            return result
                        else:
                            Symbol_option = True
                    else:
                        return result
            else:
                pass
            
            # ランダム生成処理
            letter = 'abcdefghijklmnopqrstuvwxyz'
            if Case_option:
                letter = letter + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if Figure_option:
                letter = letter + '0123456789'
            if Symbol_option:
                letter = letter + '#$%&_'
            randomList = random.choices(letter, k=wordCount)
            randomizedLetter = ''.join(randomList)
            result = randomizedLetter
        
        except ValueError as e:
            # this means that entered wordcount includes other than figure
            traceback.print_exc()
        except:
            traceback.print_exc()
        return result
    
    # ========================================================
    # 新たにアカウントを登録
    def cmdAction_addMode(self, cmdMain: str, cmdSub: list):
        try:
            # flagによって処理を変える
            if self.currentFlag == self.flag_none:
                self.addFlag_none(cmdSub)
            elif self.currentFlag == self.flag_ServiceName:
                self.addFlag_ServiceName(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_SearchWord:
                self.addFlag_SearchWord(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_LoginURL:
                self.addFlag_LoginURL(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_ID_or_Mail:
                self.addFlag_ID_or_Mail(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_PassWord:
                self.addFlag_PassWord(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_RandomPassWord:
                self.addFlag_randomPassWord(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_Remarks:
                self.addFlag_Remarks(cmdMain, cmdSub)
            pass
        except:
            traceback.print_exc()
    
    # add mode最初の処理
    def addFlag_none(self, cmdSub: list):
        try:
            # 副コマンドがある場合
            if len(cmdSub) > 0:
                self.response(
                    'addコマンドに副コマンドは不要です．'
                    'addのみ入力してください．'
                )
                return
            else:
                pass
            
            # 既存serviceNameかどうかの判定をリセット
            # Shift+Tabで戻ってきた時も，ここでリセットされる
            self.existServiceFlag = False
            
            # serviceName入力へ==============================
            self.currentFlag = self.flag_ServiceName
            self.response(
                'アカウントを登録します．serviceNameを入力してください．\n'
                '既存のserviceNameを入力すると，'
                'そのserviceNameに対するアカウント情報を追加できます．'
            )
        except:
            traceback.print_exc()
    
    # serviceNameの登録
    def addFlag_ServiceName(self, cmdMain: str, cmdSub: list):
        try:
            # 空欄でEnterキーを押された場合
            if cmdMain == '':
                self.response('serviceNameを空欄にはできません．')
                return
            # 副コマンドがある場合
            elif len(cmdSub) >= 1:
                self.response('serviceNameに空白は使用できません．')
                return
            else:
                pass
            
            # 既にDBにあるserviceNameか確認
            # 既存のserviceNameならそのid(int)が，無ければ0が返る
            serviceID = self.db.getServiceID_from_ServiceTable(cmdMain)
            
            # 既存のserviceNameなら，existServiceFlag=True
            # TrueならsearchWordとログインページURLの入力はスキップする
            if serviceID > 0:
                self.reg_serviceID = serviceID  # serviceIDを保持
                self.reg_ServiceName = cmdMain  # serviceNameを保持
                self.existServiceFlag = True
                self.addFlag_LoginURL('', [])
            else:
                self.reg_ServiceName = cmdMain  # serviceNameを保持
                self.currentFlag = self.flag_SearchWord
                self.response(
                    'このserviceNameを探すためのsearchWordを入力してください．\n'
                    'searchWordを登録しない場合は，'
                    '空欄のままEnterキーを押してください．'
                )
        except:
            traceback.print_exc()
    
    # serviceNameを検索するために使うsearchWordを登録
    def addFlag_SearchWord(self, cmdMain: str, cmdSub: list):
        try:
            # 副コマンドがある場合
            if len(cmdSub) > 0:
                self.response('searchWordに空白は使えません．')
                return
            else:
                self.reg_SearchWord = cmdMain  # searchWordを保持(空欄でも良い)
            self.currentFlag = self.flag_LoginURL
            self.response(
                'このサービスのログインページURLを入力してください．\n'
                '登録しない場合は，空欄のままEnterキーを押してください．'
            )
        except:
            traceback.print_exc()
    
    # サービスのURLを登録
    def addFlag_LoginURL(self, cmdMain: str, cmdSub: list):
        try:
            # 副コマンドがある場合
            if len(cmdSub) > 0:
                self.response('URLに空白は使用できません')
                return
            
            self.reg_LoginURL = cmdMain  # URLを保持
            self.currentFlag = self.flag_ID_or_Mail
            self.response(
                'ログインに必要なユーザIDまたは'
                'メールアドレスを入力してください．'
            )
        except:
            traceback.print_exc()
    
    # ユーザIDまたはメールアドレスを登録
    def addFlag_ID_or_Mail(self, cmdMain: str, cmdSub: list):
        try:
            # 空欄でEnterキーを押された場合
            if cmdMain == '':
                self.response(
                    'ユーザID/Mailを空欄にはできません．'
                )
                return
            # 副コマンドがある場合
            elif len(cmdSub) > 0:
                self.response(
                    'ユーザID/Mailにスペースは使用できません．'
                )
                return
            else:
                pass
            
            # 対象サービス名に同名のユーザID/Mailがあれば拒否
            accounts = self.db.getAccountNums_from_AccountsTable(
                self.reg_serviceID, cmdMain
            )
            if len(accounts) > 0:
                self.response(
                    '1つのサービス名に同名のユーザID/Mailを'
                    '紐付けることはできません．'
                )
                return
            
            self.reg_ID_or_Mail = cmdMain  # ID/Mailを保持
            self.currentFlag = self.flag_PassWord
            self.response(
                'ログインに必要なパスワードを入力してください．\n'
                '半角英数字，大文字，記号#$%&_を使用できます．\n'
                'ランダム生成機能を利用する場合はTabキーを押してください．'
            )
        except:
            traceback.print_exc()
    
    # パスワードを登録
    def addFlag_PassWord(self, cmdMain: str, cmdSub: list):
        try:
            text = 'ログインに必要なパスワードを入力してください．\n' \
                   '半角英数字，大文字，記号#$%&_を使用できます．\n' \
                   'ランダム生成機能を利用する場合は' \
                   'Tabキーを押してください．'
            
            # 空欄でEnterキーを押された場合
            if cmdMain == '':
                self.response(
                    'パスワードを空欄にはできません．\n' + text
                )
                return
            # 副コマンドがある場合
            elif len(cmdSub) > 0:
                self.response(
                    'パスワードにスペースは使用できません\n' + text
                )
                return
            else:
                pass
            self.reg_PassWord = cmdMain  # Passを保持
            self.currentFlag = self.flag_Remarks
            self.response(
                '備考があれば入力してください．\n'
                '備考がない場合は，空欄のままEnterキーを押してください．'
            )
        except:
            traceback.print_exc()
    
    # ランダムパスワードを登録
    def addFlag_randomPassWord(self, cmdMain: str, cmdSub: list):
        try:
            randomizedLetter = self.createRandomPassWord(cmdMain, cmdSub)
            # if didn't create random password, stop this method
            if randomizedLetter == '':
                return
            self.reg_PassWord = randomizedLetter  # save random password
            self.currentFlag = self.flag_Remarks
            self.response(
                '備考があれば入力してください．\n'
                '備考がない場合は，空欄のままEnterキーを押してください．'
            )
        except:
            traceback.print_exc()
    
    # 備考を登録・これまでの入力内容をDBに登録
    def addFlag_Remarks(self, cmdMain: str, cmdSub: list):
        try:
            # 副コマンドがある場合
            if len(cmdSub) > 0:
                self.response(
                    '備考に空白は使用できません．'
                )
                return
            
            # 空欄でEnterキーを押された場合でも登録処理をする
            self.reg_Remarks = cmdMain  # 備考を保持
            self.currentFlag = self.flag_none
            self.currentMode = self.mode_find
            
            # DBにアカウント登録
            # 既存serviceNameへの追加登録
            if self.existServiceFlag:
                successRegister = self.db.addAccount_into_existServiceName(
                    self.reg_serviceID, self.reg_ID_or_Mail,
                    self.reg_PassWord, self.reg_Remarks
                )
            # 新たなserviceNameでの登録
            else:
                successRegister = self.db.addAccount_newServiceName(
                    self.reg_ServiceName,
                    self.reg_SearchWord,
                    self.reg_LoginURL,
                    self.reg_ID_or_Mail,
                    self.reg_PassWord,
                    self.reg_Remarks
                )
            # 登録に成功したら登録完了の通知を表示
            if successRegister:
                self.response(
                    '以下の内容が登録されました．'
                    '編集したい場合はEditコマンドを使用できます．\n'
                    '-----------------------------\n'
                    'serviceName：' + self.reg_ServiceName + '\n' +
                    'searchWord：' + self.reg_SearchWord + '\n' +
                    'ログインページURL：' + self.reg_LoginURL + '\n' +
                    'ユーザID/メールアドレス：' + self.reg_ID_or_Mail + '\n' +
                    'パスワード：' + self.reg_PassWord + '\n' +
                    '備考：' + self.reg_Remarks)
                self.encryptDB()  # DB暗号化
            # 登録に失敗したらエラー通知を表示
            else:
                self.response(
                    '登録できませんでした（エラー発生）'
                    '内容を確認し，もう一度登録してください．'
                )
            
            self.deleteRegs()  # 一時的な記憶や判定を削除
        except:
            traceback.print_exc()
    
    # サービス追加時の一時的な記憶を削除
    def deleteRegs(self):
        self.existServiceFlag = False  # 既存serviceNameかどうかの判定をリセット
        self.reg_serviceID = 0
        self.reg_ServiceName = ''
        self.reg_SearchWord = ''
        self.reg_LoginURL = ''
        self.reg_ID_or_Mail = ''
        self.reg_PassWord = ''
        self.reg_Remarks = ''
    
    # ========================================================
    # 既存のserviceName，searchWord，ID, パスワード，備考を編集
    def cmdAction_editMode(self, cmdMain: str, cmdSub: list):
        try:
            if self.currentFlag == self.flag_none:
                self.editFlag_none(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_ServiceName:
                self.editFlag_ServiceName(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_SearchWord:
                self.editFlag_SearchWord(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_LoginURL:
                self.editFlag_LoginURL(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_ID_or_Mail:
                self.editFlag_ID_or_Mail(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_PassWord:
                self.editFlag_PassWord(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_RandomPassWord:
                self.editFlag_RandomPassWord(cmdMain, cmdSub)
            elif self.currentFlag == self.flag_Remarks:
                self.editFlag_Remarks(cmdMain, cmdSub)
            else:
                pass
        
        except:
            traceback.print_exc()
    
    # edit mode 最初の処理
    def editFlag_none(self, cmdMain: str, cmdSub: list):
        self.editableRecord = []  # 編集対象データをリセット
        # edit [serviceName] [ユーザID] [変更したい情報の種類]となってるか確認
        # 副コマンドが3つでなかった場合
        if len(cmdSub) != 3:
            self.response(
                'editコマンドには3種類の指示が必要です．'
                '以下のように使用してください．\n'
                'edit [serviceName] [ユーザID/メールアドレス] [変更したい情報]\n'
                '例：edit gmail user1@gmail.com password'
            )
            return
        
        cmdList = [cmdMain]
        for i in range(len(cmdSub)):
            cmdList.append(cmdSub[i])
        # print('cmdList: ', end='')
        # print(cmdList)
        
        # serviceNameやID/Mailが存在するのか確認
        complementedCmdList = self.checkComplementable_edit(cmdList)
        # 補完できなければ空リストが返ってくるので処理中止
        if complementedCmdList == []:
            self.response(
                'serviceName，ユーザID/メールアドレス，変更したい情報の'
                'いずれかが存在しません．\n'
                '正しく入力してください'
            )
            return
        # print('complementedCmdList:', end='')
        # print(complementedCmdList)
        
        # serviceName，ユーザID/Mailを補完
        serviceIDandName = self.complementServiceName(
            complementedCmdList[1])
        ServiceID = serviceIDandName[0]
        ServiceName = serviceIDandName[1]
        Accounts = self.db.getAccounts_from_ServiceTable(ServiceID)
        SearchWord = Accounts['searchWord']
        LoginURL = Accounts['LoginURL']
        
        # textから始まるアカウントの番号を探してから，紐づく情報を取得
        accountNums = self.db.getAccountNums_from_AccountsTable(
            ServiceID, complementedCmdList[2]
        )
        AccountNum = accountNums[0]
        AccountList = self.db.getAccount_from_AccountsTable(AccountNum)
        IDorMail = AccountList[0]['userIDorMail']
        PassWord = AccountList[0]['passWord']
        Remarks = AccountList[0]['remarks']
        
        # 編集対象データとして一時的に記憶しておく
        self.editableRecord = dict(zip(
            ['serviceID', 'serviceName', 'searchWord', 'LoginURL',
             'accountID', 'userIDorMail', 'passWord', 'remarks'],
            [ServiceID, str(ServiceName), str(SearchWord), str(LoginURL),
             AccountNum, str(IDorMail), str(PassWord), str(Remarks)]
        ))
        # print('editableRecord: ', end='')
        # print(self.editableRecord)
        
        # リストが空かどうかは判定しない
        # checkComplementable_edit関数でレコードの存在は確認済み
        self.currentFlag = complementedCmdList[3]
        
        # GUIに入力を促すメッセージ表示
        if self.currentFlag == self.flag_ServiceName:
            self.response(
                '現在のserviceName: \n"' +
                self.editableRecord['serviceName'] + '"\n' +
                '新たなserviceNameを入力してください．'
            )
        elif self.currentFlag == self.flag_SearchWord:
            self.response(
                '現在のsearchWord: \n"' +
                self.editableRecord['searchWord'] + '"\n' +
                '新たなsearchWordを入力してください．'
            )
        elif self.currentFlag == self.flag_LoginURL:
            self.response(
                '現在のログインページURL: \n"' +
                self.editableRecord['LoginURL'] + '"\n' +
                '新たなログインページURLを入力してください．\n'
                '例：https://keasy.com/login'
            )
        elif self.currentFlag == self.flag_ID_or_Mail:
            self.response(
                '現在のユーザID/メールアドレス: \n"' +
                self.editableRecord['userIDorMail'] + '"\n' +
                '新たなユーザIDまたはメールアドレスを入力してください．'
            )
        elif self.currentFlag == self.flag_PassWord:
            self.response(
                '現在のpassWord: \n"' +
                self.editableRecord['passWord'] + '"\n' +
                '新たなパスワードを入力してください．\n'
                '半角英数字，大文字，記号#$%&_を使用できます．\n'
                'パスワードをランダム生成するにはTabキーを押してください．'
            )
        elif self.currentFlag == self.flag_Remarks:
            self.response(
                '現在の備考: \n"' + self.editableRecord['remarks'] + '"\n' +
                '新たな備考を入力してください．'
                '空欄にすることもできます．'
            )
        else:
            pass
    
    # サービス名を変更
    def editFlag_ServiceName(self, cmdMain: str, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                'serviceNameにスペースは使えません．'
                'もう1度入力してください．'
            )
            return
        elif cmdMain == "":
            self.response(
                'serviceNameを空欄にはできません．'
                'もう1度入力してください．'
            )
            return
        else:
            pass
        
        ServiceID = self.editableRecord['serviceID']
        newServiceName = cmdMain
        # idからserviceNameを特定して変更
        self.db.editServiceName(ServiceID, newServiceName)
        self.encryptDB()  # DB暗号化
        
        # edit mode修了
        self.currentMode = self.mode_find
        self.currentFlag = self.flag_none
        
        self.response(
            'serviceNameを変更しました: ' + cmdMain
        )
    
    # 検索ワードを変更
    def editFlag_SearchWord(self, cmdMain: str, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                'searchWordにスペースは使えません．'
                'もう1度入力してください．'
            )
            return
        else:
            pass
        
        ServiceID = self.editableRecord['serviceID']
        newSearchWord = cmdMain
        # idからsearchWordを特定して変更
        self.db.editSearchWord(ServiceID, newSearchWord)
        self.encryptDB()  # DB暗号化
        
        # edit mode修了
        self.currentMode = self.mode_find
        self.currentFlag = self.flag_none
        
        self.response(
            'searchWordを変更しました: ' + cmdMain
        )
    
    # ログインURLを変更
    def editFlag_LoginURL(self, cmdMain: str, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                'ログインページURLにスペースは使えません．'
                'もう1度入力してください．'
            )
            return
        
        ServiceID = self.editableRecord['serviceID']
        newLoginURL = cmdMain
        # idからURLを特定して変更
        self.db.editLoginURL(ServiceID, newLoginURL)
        self.encryptDB()  # DB暗号化
        
        # edit mode修了
        self.currentMode = self.mode_find
        self.currentFlag = self.flag_none
        
        self.response(
            'ログインページURLを変更しました: ' + cmdMain
        )
    
    # ユーザID/Mailを変更
    def editFlag_ID_or_Mail(self, cmdMain: str, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                'ユーザID/メールアドレスにスペースは使えません．'
                'もう1度入力してください．'
            )
            return
        elif cmdMain == "":
            self.response(
                'ユーザID/メールアドレスを空欄にはできません．'
                'もう1度入力してください．'
            )
            return
        else:
            pass
        
        AccountNum = self.editableRecord['accountID']
        newIDorMail = cmdMain
        serviceID = self.db.getServiceID_from_AccountsTable(AccountNum)
        
        # 対象サービス名に同名のユーザID/Mailがあれば拒否
        accounts = self.db.getAccountNums_from_AccountsTable(
            serviceID, cmdMain
        )
        if len(accounts) > 0:
            self.response(
                '1つのサービス名に同名のユーザID/Mailを'
                '紐付けることはできません．'
            )
            return
        
        # アカウント番号からsearchWordを特定して変更
        self.db.editIDorMail(AccountNum, newIDorMail)
        self.encryptDB()  # DB暗号化
        
        # edit mode修了
        self.currentMode = self.mode_find
        self.currentFlag = self.flag_none
        
        self.response(
            'ユーザID/メールアドレスを変更しました: ' + cmdMain
        )
    
    # パスワードを変更
    def editFlag_PassWord(self, cmdMain: str, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                'パスワードにスペースは使えません．'
                'もう1度入力してください．\n'
                'パスワードをランダム生成するにはTabキーを押してください．'
            )
            return
        elif cmdMain == "":
            self.response(
                'パスワードを空欄にはできません．'
                'もう1度入力してください．\n'
                'パスワードをランダム生成するにはTabキーを押してください．'
            )
            return
        else:
            pass
        
        AccountNum = self.editableRecord['accountID']
        newPassWord = cmdMain
        # アカウント番号からsearchWordを特定して変更
        self.db.editPassWord(AccountNum, newPassWord)
        self.encryptDB()  # DB暗号化
        
        # edit mode修了
        self.currentMode = self.mode_find
        self.currentFlag = self.flag_none
        
        self.response(
            'パスワードを変更しました: ' + cmdMain
        )
    
    # ランダムパスワードに変更
    def editFlag_RandomPassWord(self, cmdMain: str, cmdSub: list):
        try:
            randomizedLetter = self.createRandomPassWord(cmdMain, cmdSub)
            # if didn't create random password, stop this method
            if randomizedLetter == '':
                return
            
            AccountNum = self.editableRecord['accountID']
            newPassWord = randomizedLetter
            # アカウント番号からsearchWordを特定して変更
            self.db.editPassWord(AccountNum, newPassWord)
            self.encryptDB()  # DB暗号化
            
            # edit mode修了
            self.currentMode = self.mode_find
            self.currentFlag = self.flag_none
            self.response(
                'パスワードを変更しました: ' + randomizedLetter
            )
        except:
            traceback.print_exc()
    
    # 備考を変更
    def editFlag_Remarks(self, cmdMain: str, cmdSub: list):
        if len(cmdSub) > 0:
            self.response(
                '備考にスペースは使えません．'
                'もう1度入力してください．'
            )
            return
        
        AccountNum = self.editableRecord['accountID']
        newRemarks = cmdMain
        # アカウント番号からsearchWordを特定して変更
        self.db.editRemarks(AccountNum, newRemarks)
        self.encryptDB()  # DB暗号化
        
        # edit mode修了
        self.currentMode = self.mode_find
        self.currentFlag = self.flag_none
        
        self.response(
            '備考を変更しました: ' + cmdMain
        )
    
    # ========================================================
    # preparation of delete serviceName or userIDorMail from DB
    def cmdAction_deleteMode(self, cmdMain: str, cmdSub: list):
        try:
            didText = '削除しました．'
            do_notText = '削除を中止しました．'
            if self.currentFlag == self.flag_ServiceName:
                result = self.deleteFlag_ServiceName(cmdMain, cmdSub)
                # True/None/False
                if result:
                    self.response(didText)
                elif result == None:
                    pass
                else:
                    self.response(do_notText)
            elif self.currentFlag == self.flag_ID_or_Mail:
                result = self.deleteFlag_Account(cmdMain, cmdSub)
                # True/None/False
                if result:
                    self.response(didText)
                elif result == None:
                    pass
                else:
                    self.response(do_notText)
            elif self.currentFlag == self.flag_Both:
                result = self.deleteFlag_Account(cmdMain, cmdSub)
                # True/None/False
                if result:
                    self.deleteFlag_ServiceName(cmdMain, cmdSub)
                    self.response(didText)
                elif result == None:
                    pass
                else:
                    self.response(do_notText)
            else:
                pass
            
            # cmdSubは[サービス名], [ID/Mail]
            # cmdSubが無い/3つ以上ある場合は補完中止
            if len(cmdSub) < 1 or len(cmdSub) > 2:
                return
            
            targetInput = cmdSub[0]  # 入力したサービス名
            
            # serviceName入力時=================================
            serviceIDandName = self.complementServiceName(targetInput)
            if serviceIDandName == []:
                self.response(
                    '該当するサービス名がありません．'
                )
                return
            
            serviceID = serviceIDandName[0]
            serviceName = str(serviceIDandName[1])
            # サービス名だけが入力されていた場合，
            # サービス名の削除確認
            if len(cmdSub) == 1:
                self.deletableServiceID = serviceID
                self.currentFlag = self.flag_ServiceName
                self.response(
                    'サービス"' + serviceName + '"を削除します．\n'
                                            '実行する場合は"yes"，'
                                            '中止する場合は"no"を入力してください．'
                )
                return
            
            # ユーザID/メールアドレス入力時=========================
            targetInput = cmdSub[1]
            # サービスIDと入力文字からアカウント番号を検索
            accountNums = self.db.getAccountNums_from_AccountsTable(
                serviceID, targetInput)
            if len(accountNums) != 1:
                return
            
            AccountNumber = accountNums[0]
            AccountData = self.db.getAccount_from_AccountsTable(AccountNumber)
            # 該当アカウントが無い場合(リストが空)
            # idからの検索なので，リストの数が1を超えることは無いはず？
            if len(AccountData) != 1:
                self.response(
                    '該当するユーザID/メールアドレスがありません．'
                )
                return
            
            IDorMail = str(AccountData[0]['userIDorMail'])
            # 削除するデータの場所(int)を一次記憶
            self.deletableAccountNum = AccountNumber
            self.currentFlag = self.flag_ID_or_Mail
            self.response(
                'ユーザID/Mail "' + IDorMail +
                '"のアカウントを削除します．\n'
                '実行する場合は"yes"，中止する場合は"no"を入力してください．'
            )
            
            # そのサービス名に紐付いたアカウント数が1つだけだったら，
            # サービス名も削除対象に含める
            accounts = self.db.getAccounts_from_AccountsTable(serviceID)
            if len(accounts) == 1:
                self.deletableServiceID = serviceID
                self.currentFlag = self.flag_Both
        except:
            traceback.print_exc()
    
    # confirm and delete serviceName from DB
    # return:
    #   True: do delete
    #   None: reconfirm
    #   False: do not delete
    def deleteFlag_ServiceName(self, cmdMain: str, cmdSub: list):
        try:
            result = None
            if len(cmdSub) > 0:
                return result
            if cmdMain == 'yes':
                # 該当するサービス名を削除
                self.db.deleteServiceName(self.deletableServiceID)
                # サービスに紐付けられた全アカウントを探して削除
                accountNums = self.db.getAccounts_from_AccountsTable(
                    self.deletableServiceID
                )
                for i in range(len(accountNums)):
                    self.db.deleteAccount(accountNums[i])
                self.encryptDB()  # DB暗号化
                result = True
            elif cmdMain == 'no':
                result = False
            else:
                return result
            
            self.deletableServiceID = 0
            self.currentMode = self.mode_find
            self.currentFlag = self.flag_none
        except:
            traceback.print_exc()
        return result
    
    # confirm and delete Account from DB
    # return:
    #   True: do delete
    #   None: reconfirm
    #   False: do not delete
    def deleteFlag_Account(self, cmdMain: str, cmdSub: list):
        try:
            result = None
            if len(cmdSub) > 0:
                return result
            if cmdMain == 'yes':
                # 該当するアカウントを削除
                self.db.deleteAccount(self.deletableAccountNum)
                self.encryptDB()  # DB暗号化
                result = True
            elif cmdMain == 'no':
                result = False
            else:
                return result
            
            self.deletableAccountNum = 0
            self.currentMode = self.mode_find
            self.currentFlag = self.flag_none
        except:
            traceback.print_exc()
        return result
    
    # ========================================================
    # findコマンドで表示されたIDとパスワードを記憶
    # 記憶された組は自動入力に使う
    def cmdAction_memorizeMode(self, cmdSub: list):
        try:
            # cmdSubは[サービス名], [ID/Mail]
            # cmdSubが2つでない場合は補完中止
            if len(cmdSub) != 2:
                self.response(
                    '記憶するためのサービス名と'
                    'ユーザID/Mailを入力してください．'
                )
                self.currentMode = self.mode_find
                return
            
            targetInput = cmdSub[0]  # 入力したサービス名
            
            # serviceName入力時=================================
            serviceIDandName = self.complementServiceName(targetInput)
            # 該当サービス名が無い場合(リストが空)
            if serviceIDandName == []:
                self.response(
                    '該当するサービス名がありません．'
                )
                self.currentMode = self.mode_find
                return
            serviceID = serviceIDandName[0]
            
            # ユーザID/メールアドレス入力時=========================
            targetInput = cmdSub[1]
            accountNums = self.db.getAccountNums_from_AccountsTable(
                serviceID, targetInput)
            if len(accountNums) != 1:
                self.response(
                    '致命的なエラー：アカウントが見つかりませんでした．'
                )
                self.currentMode = self.mode_find
                return
            
            AccountNumber = accountNums[0]
            AccountData = self.db.getAccount_from_AccountsTable(AccountNumber)
            # 該当アカウントが無い場合(リストが空)
            # idからの検索なので，リストの数が1を超えることは無いはず？
            if len(AccountData) != 1:
                self.response(
                    '該当するユーザID/メールアドレスがありません．'
                )
                self.currentMode = self.mode_find
                return
            
            IDorMail = str(AccountData[0]['userIDorMail'])
            passWord = str(AccountData[0]['passWord'])
            # ユーザID/Mailとパスワードを一時記憶
            self.MemorizeDict['user'] = IDorMail
            self.MemorizeDict['pass'] = passWord
            self.response(
                'ユーザ"' + IDorMail + '"のID/Mailとパスワードを記憶しました．'
            )
            self.currentMode = self.mode_find
        except:
            traceback.print_exc()
    
    # csv出力
    def cmdAction_csvMode(self, cmdSub: list):
        dataList: list = self.db.getAllDataForCSV()
        try:
            with open('keasy_data.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(dataList)
            self.response('CSV出力しました。')
            self.currentMode = self.mode_find
        except:
            traceback.print_exc()
    
    # マスターパスワードの変更
    def cmdAction_masterMode(self):
        self.response(
            '新しいマスターパスワードを入力してください．\n'
            '半角英数字，大文字，記号を使用できます．'
        )
        self.currentMode = self.mode_confirmMaster
