# -*- coding: utf-8 -*-
import sqlite3
import traceback


# [Eng] dict key is...
# [日] 辞書型のキーは以下
# serviceID, serviceName, searchWord, LoginURL,
# accountID, userIDorMail, passWord, remarks

class Database:
    def __init__(self):
        self.dbName = 'keasy.db'
        self.services_table = 'Services'
        self.accounts_table = 'Accounts'
        
        try:
            con = sqlite3.connect(self.dbName)
            # もしテーブルが無ければ作る
            # integerはprimary keyにすると自動でauto incrementになっている
            # サービステーブル=====================================
            con.execute("create table if not exists %s("
                        "id integer primary key,"  # 連番(主キー)
                        "service string,"  # サービス名(主キー)
                        "search string,"  # searchWord
                        "url string)"  # ログインページのURL
                        % (self.services_table))
            # アカウントテーブル=====================================
            con.execute("create table if not exists %s("
                        "id integer primary key,"  # 連番(主キー)
                        "service int not null,"  # サービスのID
                        "user string not null,"  # ID/メールアドレス
                        "password string not null,"  # パスワード
                        "remarks string)"  # 備考
                        % (self.accounts_table))
            
            con.commit()  # SQLを確定
            con.close()
        except:
            traceback.print_exc()
    
    # DBが正しく復号化されていればTrueを返す
    # 復号化が誤っていればFalseを返す
    def checkDB(self):
        try:
            with open("keasy.db", "rb") as fileData:
                # DBファイルのバイナリ取得(エンコードはutf16)
                contents = fileData.read()
            # ファイル先頭6字がバイナリで'SQLite'でない場合はFalseを返す
            # 正しく復号化されていれば'SQLite'となる
            if contents[0:6] != b'SQLite':
                return False
            return True
        except:
            traceback.print_exc()
            return False
    
    # デバッグ用：全データ表示
    # [Eng] For Debug: display all DB data
    def getAllAccounts(self):
        # print('reading all data from database...')
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            cur.execute("select name from sqlite_master where type='table'")
            # print('============Tables ============')
            # for row in cur:
            #     print(row[0])
            
            cur.execute("select * from %s" % (self.services_table))
            # print('============Values in Services Table ============')
            # for row in cur:
            #     print(row)
            
            cur.execute("select * from %s" % (self.accounts_table))
            # print('============Values in Accounts Table ============')
            # for row in cur:
            #     print(row)
            
            con.close()
        except:
            traceback.print_exc()
    
    # デバッグ用：データ挿入
    # [Eng] For Debug: insert data
    def insertTest(self):
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "insert into %s(service,search,url)"
                "values('gmail','google','')"
                % (self.services_table))
            con.execute(
                "insert into %s(service,user,password,remarks) values("
                "1,"
                "'myUserFirst@gmail.com',"
                "'thispasswordslongis31characters',"
                "'thats_remarks'"
                ")" % (self.accounts_table))
            # =======================
            con.execute(
                "insert into %s(service,user,password,remarks) values("
                "1,"
                "'testAdmin@gmail.com',"
                "'40charsAAABBBBBBBBBBCCCCCCCCCCDDDDDDDDDD',"
                "''"
                ")" % (self.accounts_table))
            # =======================
            con.execute(
                "insert into %s(service,search,url)"
                "values('GitHub','','https://github.com')"
                % (self.services_table))
            con.execute(
                "insert into %s(service,user,password,remarks) values("
                "2,"
                "'testAdmin@gmail.com',"
                "'40charsAAABBBBBBBBBBCCCCCCCCCCDDDDDDDDDD',"
                "''"
                ")" % (self.accounts_table))
            
            con.commit()
            con.close()
        except:
            traceback.print_exc()
    
    # serviceテーブルから，引数と全く同じ文字のサービス名があるか検索
    # 見つかったら該当サービス名のid(int)を返す
    # 見つからなかったら0を返す
    def getServiceID_from_ServiceTable(self, serviceName: str) -> int:
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            # 大文字小文字を区別せずに探す
            # 両方とも全て大文字に変換することで合わせている
            cur.execute(
                "select id from '%s' where upper(service) = upper('%s')"
                % (self.services_table, serviceName)
            )
            result = cur.fetchone()
            
            # debug ==========
            # print('=====getServiceName_from_ServiceTable=====')
            # print('result: ', end='')
            # print(result)
            # debug ==========
            
            con.close()
            if result == None:
                return 0
            serviceID = result[0]  # 該当サービス名のID
            return serviceID
        except:
            traceback.print_exc()
            return 0
    
    # 引数の文字列を使って，serviceテーブルからサービス名の検索
    # condition=
    #   include: search serviceName includes arg-searchWord
    #   forward: search serviceName starts with arg-searchWord
    # useSearchWord=
    #   True: search also using searchWord
    #   False: search without searchWord
    # 指定条件でDB内に見つかれば，辞書型で
    # ['serviceID', 'serviceName', 'searchWord', 'URL']を返す
    # 無ければ空リストを返す
    def getServices_from_ServiceTable(
            self, searchWord: str,
            condition='include', useSearchWord=True) -> list:
        Accounts = []
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            # serviceNameを検索
            # searchWordを含むserviceNameを探す
            if condition == 'include' and useSearchWord:
                cur.execute(
                    "select * from '%s' where service like '%s' "
                    "or search like '%s'"
                    % (self.services_table,
                       "%" + searchWord + "%", "%" + searchWord + "%")
                )
            elif condition == 'include' and not useSearchWord:
                cur.execute(
                    "select * from '%s' where service like '%s'"
                    % (self.services_table, "%" + searchWord + "%",)
                )
            # searchWordから始まるserviceNameを探す
            elif condition == 'forward' and useSearchWord:
                cur.execute(
                    "select * from '%s' where service like '%s' "
                    "or search like '%s'"
                    % (self.services_table, searchWord + "%", searchWord + "%")
                )
            elif condition == 'forward' and not useSearchWord:
                cur.execute(
                    "select * from '%s' where service like '%s'"
                    % (self.services_table, searchWord + "%")
                )
            else:
                # 検索条件はinclude/forwardを使うべき
                # この分岐に入ってはいけない
                raise ValueError("Argment 'condition' is bad value! "
                                 "You must use 'include' or 'forward'.")
            result = cur.fetchall()
            # debug==========
            # print('===== getServices_from_ServiceTable =====')
            # print('Accounts result: ', end='')
            # print(result)
            # debug==========
            
            # サービスが見つからなければ空リストを返す
            if len(result) < 1:
                return Accounts
            
            for i in range(len(result)):
                # 入力文字と一致するサービス名の場合，
                # そのデータだけを辞書型に変換
                if searchWord == result[i][1]:
                    Accounts = []
                    Accounts.append(dict(zip(
                        ['serviceID', 'serviceName', 'searchWord', 'LoginURL'],
                        [result[i][0], result[i][1], result[i][2], result[i][3]]
                    )))
                    break
                # 一致しない限りは，辞書型に変換して追加
                Accounts.append(dict(zip(
                    ['serviceID', 'serviceName', 'searchWord', 'LoginURL'],
                    [result[i][0], result[i][1], result[i][2], result[i][3]]
                )))
            
            con.close()
        except:
            traceback.print_exc()
        return Accounts
    
    # 引数のserviceIDを使って，serviceテーブルからサービス情報を取得
    # 見つかれば辞書型で
    # ['serviceName', 'searchWord', 'ログインURL']を返す
    # 無ければ空リストを返す
    def getAccounts_from_ServiceTable(self, serviceID: int) -> list:
        Accounts = []
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            cur.execute(
                "select * from '%s' where id = %s"
                % (self.services_table, serviceID)
            )
            result = cur.fetchall()
            # debug==========
            # print('===== getServices_from_ServiceTable =====')
            # print('Accounts result: ', end='')
            # print(result)
            # debug==========
            # 結果が1つでないなら空リストを返す
            # serviceIDは主キーだから，見つからなかった場合だけ？
            if len(result) != 1:
                return Accounts
            # 辞書型に変換
            Accounts = dict(zip(
                ['serviceName', 'searchWord', 'LoginURL'],
                [result[0][1], result[0][2], result[0][3]]
            ))
            con.close()
        except:
            traceback.print_exc()
        return Accounts
    
    # accountsテーブルから全データをserviceID順に取得
    # 辞書型で[num]['serviceName', 'searchWord', 'URL',
    #               'ユーザID/Mail', 'パスワード', '備考'] を返す
    # 無ければ空リストを返す
    def getAll_from_AccountsTable(self) -> list:
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            cur.execute("select * from %s order by service"
                        % (self.accounts_table))
            Account = []
            
            for row in cur:
                serviceData = self.getAccounts_from_ServiceTable(row[1])
                serviceName = serviceData['serviceName']
                searchWord = serviceData['searchWord']
                loginURL = serviceData['LoginURL']
                # 辞書型に変換
                Account.append(dict(zip(
                    ['serviceName', 'searchWord',
                     'userIDorMail', 'passWord', 'remarks', 'LoginURL'],
                    [serviceName, searchWord,
                     row[2], row[3], row[4], loginURL]
                )))
            con.commit()
            con.close()
            # debug==========
            # print('============Values in Accounts Table ============')
            # print('Account: ', end='')
            # print(Account)
        except:
            traceback.print_exc()
        return Account
    
    # Accountsテーブルから，引数のアカウント番号が紐付くServiceIDを探す
    # 見つかればServiceIDを，見つからなければ0を返す
    def getServiceID_from_AccountsTable(self, accountNum: int) -> int:
        ServiceID = 0
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            cur.execute(
                "select service from %s where id = %s"
                % (self.accounts_table, accountNum)
            )
            for row in cur:
                ServiceID = row[0]
            con.commit()
            con.close()
            # debug==========
            # print('=======getAccount_from_AccountsTable=====')
            # print('Account: ', end='')
            # print(Account)
        except:
            traceback.print_exc()
        return ServiceID
    
    # 引数のアカウント番号を使って，accountsテーブルからアカウント取得
    # 見つかれば辞書型で
    # [0]['accountID', 'userIDorMail', 'passWord', 'remarks']を返す
    # 無ければ空リストを返す
    def getAccount_from_AccountsTable(self, accountNum: int) -> list:
        Account = []
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            cur.execute(
                "select * from %s where id = %s"
                % (self.accounts_table, accountNum)
            )
            for row in cur:
                # 辞書型に変換
                Account.append(dict(zip(
                    ['accountID', 'userIDorMail', 'passWord', 'remarks'],
                    [accountNum, row[2], row[3], row[4]]
                )))
            con.commit()
            con.close()
            # debug==========
            # print('=======getAccount_from_AccountsTable=====')
            # print('Account: ', end='')
            # print(Account)
        except:
            traceback.print_exc()
        return Account
    
    # 引数のserviceIDを使って，accountsテーブルからアカウント番号一覧を取得
    # 見つかればアカウント番号のリストを返す
    # 無ければ空リストを返す
    def getAccounts_from_AccountsTable(self, serviceID: int) -> list:
        Accounts = []
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            cur.execute(
                "select id from %s where service = %s"
                % (self.accounts_table, serviceID)
            )
            for row in cur:
                # debug
                # print('row::' + str(row))
                Accounts.append(row[0])
            con.commit()
            con.close()
        except:
            traceback.print_exc()
        return Accounts
    
    # 引数のURLを使って，serviceテーブルからアカウント取得
    # 見つかったアカウントが1つだけだった場合のみ，
    # accountsテーブルからユーザID/Mailとパスワードを取得して
    # 辞書型で['Service','ID','Pass']を返す
    # アカウントが0か2以上なら空の辞書を返す
    def getIDandPassByURL(self, URL: str) -> dict:
        IDAndPass = {}
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            # URLからサービスIDを取得
            cur.execute(
                "select id from %s where url like '%s'"
                % (self.services_table, URL + "%")
            )
            serviceID_list = []
            for row in cur:
                serviceID_list.append(row[0])
            con.commit()
            # サービス名が1つだけ見つかったら，
            # サービスIDからサービス名, ユーザID/Mail, パスワードを取得
            if len(serviceID_list) == 1:
                accountData = []
                cur.execute(
                    "select service from %s where id = %s"
                    % (self.services_table, serviceID_list[0])
                )
                for row in cur:
                    serviceName = row[0]
                cur.execute(
                    "select user,password from %s where service = %s"
                    % (self.accounts_table, serviceID_list[0])
                )
                for row in cur:
                    # 辞書型に変換
                    accountData.append(dict(zip(
                        ['serviceName', 'userIDorMail', 'passWord'],
                        [serviceName, row[0], row[1]]
                    )))
                # アカウントが1つだけ見つかったら，
                # ユーザID/Mailとパスワードを返り値にする
                if len(accountData) == 1:
                    IDAndPass = {
                        'Service': accountData[0]['serviceName'],
                        'ID': accountData[0]['userIDorMail'],
                        'Pass': accountData[0]['passWord']
                    }
            con.close()
        except:
            traceback.print_exc()
        return IDAndPass
    
    # 引数のserviceIDと文字列を使って，
    # accountsテーブルから該当するユーザID/Mailのアカウント番号を検索
    # 見つかったアカウント番号をリストで返す．
    # 見つからなければ空リストを返す
    def getAccountNums_from_AccountsTable(
            self, serviceID: int, IDorMail: str) -> list:
        AccountNums = []
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            cur.execute(
                "select * from %s where service = %s and user like '%s'"
                % (self.accounts_table, serviceID, IDorMail + '%')
            )
            result = cur.fetchall()
            for row in range(len(result)):
                # 入力文字と一致するユーザID/Mailがあれば，
                # そのアカウントのアカウント番号だけを追加
                if IDorMail == result[row][2]:
                    AccountNums = []
                    AccountNums.append(result[row][0])
                    break
                AccountNums.append(result[row][0])
            con.commit()
            con.close()
        except:
            traceback.print_exc()
        return AccountNums
    
    # accountsテーブルからアカウント検索
    # ServiceNameから始まるserviceNameのうち，
    # IDorMailから始まるユーザID/Mailに関するレコードを取得(7項目)
    # [アカウントと対応するserviceNameID], [serviceName], [searchWord], [URL],
    # [アカウント番号], [ユーザID/Mail], [パスワード], [備考]
    # 取得できればレコード入りリストを，取得できなければ空リストを返す
    def getEditableAccount(self, ServiceID: int, IDorMail: str) -> list:
        resultList = []
        try:
            con = sqlite3.connect(self.dbName)
            cur = con.cursor()
            
            cur.execute(
                "select * from '%s' where id = '%s'"
                % (self.services_table, ServiceID)
            )
            resultService = cur.fetchall()
            
            cur.execute(
                "select * from '%s' where service = '%s' and user like '%s'"
                % (self.accounts_table, ServiceID, IDorMail + "%")
            )
            resultAccounts = cur.fetchall()
            # debug==========
            # print('======Editable Accounts=======')
            # print('resultService: ', end='')
            # print(resultService)
            # print('resultAccounts: ', end='')
            # print(resultAccounts)
            # debug==========
            # 最初のレコードを保持
            # レコードの有無は判定しない(この関数が走る前に存在を確認済み)
            # 辞書型に変換
            resultList = (dict(zip(
                ['serviceID', 'serviceName',
                 'searchWord', 'LoginURL',
                 'accountID', 'userIDorMail',
                 'passWord', 'remarks'],
                [resultAccounts[0][1], resultService[0][1],
                 resultService[0][2], resultService[0][3],
                 resultAccounts[0][0], resultAccounts[0][2],
                 resultAccounts[0][3], resultAccounts[0][4]]
            )))
            con.commit()
            con.close()
        except:
            traceback.print_exc()
        return resultList
    
    # DBの既存serviceNameにアカウント追加
    # accountsテーブルのみ
    # 成功ならTrue,例外が起きたらFalseを返す
    def addAccount_into_existServiceName(
            self, ServiceID: int, IDorMail: str,
            PassWord: str, Remarks: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "insert into %s(service,user,password,remarks) "
                "values('%s','%s','%s','%s')"
                % (self.accounts_table, ServiceID, IDorMail, PassWord, Remarks)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # DBに新たなserviceNameでアカウント追加
    # serviceテーブルとaccountsテーブル両方
    # 成功ならTrue,例外が起きたらFalseを返す
    def addAccount_newServiceName(
            self, ServiceName: str, SearchWord: str, LoginURL: str,
            IDorMail: str, PassWord: str, Remarks: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "insert into %s(service,search,url)"
                "values('%s','%s','%s')"
                % (self.services_table, ServiceName, SearchWord, LoginURL))
            con.commit()
            
            ServiceID = self.getServiceID_from_ServiceTable(ServiceName)
            con.execute(
                "insert into %s(service,user,password,remarks) "
                "values(%s,'%s','%s','%s')"
                % (self.accounts_table, ServiceID,
                   IDorMail, PassWord, Remarks))
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # serviceNameを変更
    def editServiceName(self, ServiceID: int, newServiceName: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "update %s set service = '%s' where id = %s"
                % (self.services_table, newServiceName, ServiceID)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # searchWordを変更
    def editSearchWord(self, ServiceID: int, newSearchWord: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "update %s set search = '%s' where id = %s"
                % (self.services_table, newSearchWord, ServiceID)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # URLを変更
    def editLoginURL(self, ServiceID: int, newLoginURL: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "update %s set url = '%s' where id = %s"
                % (self.services_table, newLoginURL, ServiceID)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # ユーザID/Mailを変更
    def editIDorMail(self, AccountNum: int, newIDorMail: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "update %s set user = '%s' where id = %s"
                % (self.accounts_table, newIDorMail, AccountNum)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # パスワードを変更
    def editPassWord(self, AccountNum: int, newPassWord: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "update %s set password = '%s' where id = %s"
                % (self.accounts_table, newPassWord, AccountNum)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # 備考を変更
    def editRemarks(self, AccountNum: int, newRemarks: str) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "update %s set remarks = '%s' where id = %s"
                % (self.accounts_table, newRemarks, AccountNum)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # [Eng] delete serviceName using serviceID from service-table
    # [日]サービスIDを使ってサービス名を削除
    def deleteServiceName(self, serviceID: int) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "delete from %s where id = %s"
                % (self.services_table, serviceID)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
    
    # [Eng] delete account using accountNum from accounts-table
    # [日]アカウント番号を使ってアカウントを削除
    def deleteAccount(self, accountNum: int) -> bool:
        try:
            con = sqlite3.connect(self.dbName)
            con.execute(
                "delete from %s where id = %s"
                % (self.accounts_table, accountNum)
            )
            con.commit()
            con.close()
            return True
        except:
            traceback.print_exc()
            return False
