# -*- coding: utf-8 -*-
# Keasy uses pycryptodome as pycrypto.
from Cryptodome.Cipher import AES


class AES_Cipher_SQLite:
    def __init__(self, keyPhrase: str):
        # AES暗号化に使うパスワード
        keyPhrase_shortageChars = self.getShortageChars(keyPhrase)
        self.PassWord = self.get16ByteIncrementsData(
            keyPhrase, keyPhrase_shortageChars
        ).encode('utf8')
        
        # AES暗号化に使うIV
        ivPhrase = 'iv'
        ivPhrase_shortageChars = self.getShortageChars(ivPhrase)
        self.iv = self.get16ByteIncrementsData(
            ivPhrase, ivPhrase_shortageChars
        ).encode('utf8')
    
    # 16バイト刻みの文字数となるために何文字不足しているかを返す
    def getShortageChars(self, text: str) -> int:
        # 文字数0なら不足数は16
        if len(text) == 0:
            nearChars = 16
        # 16バイト刻みなら不足数は0
        elif (len(text) % 16) == 0:
            nearChars = len(text)
        else:
            nearChars = len(text) + (16 - (len(text) % 16))
        
        return nearChars - len(text)
    
    # 不足分したバイト数をstring文字で補い，16バイト刻みにして返す
    def get16ByteIncrementsData(self, text: str, shortage: int) -> str:
        return text + '_' * shortage
    
    # AESでDBバイナリデータ(16バイト刻み)を暗号化
    def AES_Encryption(self, targetData: bytes) -> bytes:
        obj = AES.new(self.PassWord, AES.MODE_CBC, self.iv)
        encryptedData = obj.encrypt(targetData)
        return encryptedData
    
    # AESでDBバイナリデータ(16バイト刻み)を復号化
    def AES_Decryption(self, targetData: bytes) -> bytes:
        obj = AES.new(self.PassWord, AES.MODE_CBC, self.iv)
        decrypted = obj.decrypt(targetData)
        return decrypted
