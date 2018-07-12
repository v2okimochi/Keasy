# Keasy
Keasy is open source GUI password manager. You can use it only by command which CLI-like.

Almost functions work only on Windows now yet.

* What is convenience of Keasy?
* [Structure](#Structure)
* [Run](#Run)
* [Usage](#Usage)
* [Contribution](#Contribution)


# What is convenience of Keasy?
Keasy can realize CLI-like operation speed on GUI application. 

Even if you are using Windows, you don't have to use mouse when operate password manager.

For example, if you want to login to website, first focused at your password manager by mouse, then copied our username and password from your password manager,  then focused website by mouse, finally pasted these on website.

But Keasy can operated by only keyboard.

First you hide Keasy into task tray by Ctrl+Ctrl, and open website. Then open Keasy by Ctrl+Ctrl and find account. hide Keasy to focus website, finally paste username and password by Shift+Shift.

You only use mouse when open website or focus input-form.

# Structure
GUI: PyQt5  
Database: SQLite3  

Keasy uses 6 data at Database. For example case of GitHub account...
* service-name: GitHub
* search-word: microsoft
* login-url: https://github.com  
* user-name: sh141
* password: my-password
* remarks: this is GitHub account.

Keasy encrypts DB file(keasy.db) of SQLite3 to "encrypted.keasy" with AES password.

Keasy use DB after decrypt "encrypted.keasy" and save to same file.   
And Keasy delete "keasy.db" before quit itself.

"encrypted.keasy" is only open by your master password.

# Run
## Use with Python3
You should run Keasy.py to use Keasy application.  
For example if you use python3.6...
```console
# python3.6 Keasy.py
```

You have to install libraries (PyQt5.9, keyboard0.11.0, and also) used by Keasy into your python3.


## Use with exe file on Windows
Download .exe file from following link.  
I checked the operation only on Windows10 x86-64.

* [Keasy version1.0](https://drive.google.com/file/d/1KXHCws-_XuXJoT1U_JjpvC_yEFEvdtGI/view?usp=sharing) ( 36MB )


## Build Keasy yourself for Windows
You can build Keasy to .exe file yourself with PyInstaller. Keasy.exe of Above link is also built by PyInstaller.  

If you will build it at your working directory "Keasy", you should use this command on your PowerShell using PyInstaller.

```console
PS [your working directory]\Keasy> pyinstaller --onefile --noconsole --icon icon.ico --hidden-import comtypes.gen._944DE083_8FB8_45CF_BCB7_C477ACB2F897_0_1_0 --hidden-import comtypes.gen.UIAutomationClient --path C:\Windows\WinSxS\amd64_avg.vc140.crt_f92d94485545da78_14.0.24210.0_none_69fa0197d9b096ae\ .\Keasy.py
```

Path which specified by --path may be different on your Windows.

I did the optional to avoid warning that "lib not found: api-ms-win-crt-stdio-l1-1-0.dll" with building.

***

You should add icon's path(icon name, absolute path to icon) to "Keasy.spec" in order to displayable icon at application and task bar.
```console
a.datas += [('icon.ico', '[absolute directory path to icon.ico]\icon.ico', 'DATA')]
```

For example following.  
Please change path according to your working directory.

```python:Keasy.spec
# -*- mode: python -*-

block_cipher = None


a = Analysis(['Keasy.py'],
             pathex=['C:\\Windows\\WinSxS\\amd64_avg.vc140.crt_f92d94485545da78_14.0.24210.0_none_69fa0197d9b096ae\\', 'D:\\[your working directory]]\\Keasy'],
             binaries=[],
             datas=[],
             hiddenimports=['comtypes.gen._944DE083_8FB8_45CF_BCB7_C477ACB2F897_0_1_0', 'comtypes.gen.UIAutomationClient'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
a.datas += [('icon.ico', '[absolute directory path to icon.ico]\icon.ico', 'DATA')]
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Keasy',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False , icon='icon.ico')
```

If you made "Keasy.spec" as above, you should not use above long pyinstaller command, but should use this command to build Keasy with your spec file.
```console
pyinstaller .\Keasy.spec
```


# Usage
## Console-commands
* [exit](#exit)
* [find](#find)
* [memorize](#memorize)
* [show](#show)
* [hide](#hide)
* [add](#add)
* [edit](#edit)
* [delete](#delete)
* [master](#master)

### exit  
Quit Keasy.


### find [input-text]  
Search service-name by input-text and display their. <br><br> 
If you have registered search-word, and it includes input-text, Keasy bring service-name which has this search-word.  <br><br>
At this time, If Keasy brought up only one service-name, Keasy show you account(user-ID/Mail, password, remarks) service-name has.
For example...
```console
$ find git
```


### memorize [service-name] [user-ID/Mail]  
Choose one account, then remember user-name and password temporary. <br> 
You can paste remembered datas by Shift -> Shift. Keasy do that "paste user-name"->"press tab key"->"paste password".


### show  
Keasy shows raw passwords which displayed.


### hide  
Keasy hides passwords which displayed. Passwords are changed to "*".


### add  
Add account.  
You should enter "service-name", "search-word", "login-url", "user-name", "password", "remarks". But search-word, login-url and remarks are optional.  <br><br>
For example...  
service-name: GitHub  
search-word:  
login-url: https://github.com  
user-name: sh141  
password: my-password  
remarks:  


### edit [service-name] [user-ID/Mail] [choose-infomation]  
Edit account information.  
You can select "choose-information" from the following:<br><br>
ServiceName  
SearchWord  
LoginURL  
ID_or_Mail  
PassWord  
Remarks  
<br>
For example...
```console
$ edit GitHub sh141 PassWord
```


### delete [service-name] (user-ID/Mail)  
Delete service or account.  
If you delete service, Keasy delete also accounts which this service has.  
If you delete account which service-name has only one, Keasy delete also this service.
<br>
For 2 example...  
```console
$ delete GitHub
```
```console
$ delete GitHub sh141
```

### master  
change master-password.


## Keyboard-shortcuts
* [tab](#tab)
* [shift+tab](#shift+tab)
* [ctrl->ctrl](#ctrl->ctrl)
* [shift->shift](#shift->shift)
* [ctrl+shift->ctrl+shift](#ctrl+shift->ctrl+shift)
* [ctrl+space](#ctrl+space)


### tab
Complement your command if input which like exist command on Keasy.

If database has some service-name or user-ID/Mail like your input, Keasy also complement these.

Keasy does not complement "exit" and "master" so you should input these fully.


### shift+tab
Rollback state at current mode.  
You can use it at add mode and edit mode.


### ctrl->ctrl
Hide Keasy into task tray, or open Keasy from task tray.
You can always call Keasy because Keasy is monitoring your keyboard.

If you call Keasy when you are looking website, Keasy is getting URL of current webpage to search for user-name and password, then memorize these automatically(auto-memorize).

The auto-memorize works at Mozilla Firefox and Google Chrome now.


### shift->shift
Input user-name and password to website automatically.

Actually, Keasy do "ctrl+l (focus to address bar)"->"ctrl+c (copy URL)" using your keyboard.


### ctrl+shift->ctrl+shift
You can also use it by ctrl+(shift->shift).

Input user-name or password to website automatically.  
The difference from "shift -> shift" is that only input one data.

To switch data, you should use "ctrl+space".


### ctrl+space
Switch data for input.

At first you can input user-name automatically.  
If you want to input password, press "ctrl+shift -> ctrl+shift" then switch data for input from user-name to password.

It switches data to user-name or password every time press this hotkey.


# Contribution
Pull requests and issues are very welcome.

I would like to make Keasy a convenience GUI password manager which able to run on multi platform with command line base.