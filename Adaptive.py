import sys
from os import system
from utilities import GITHUBURL, fetchConfig, editConfig, getLeaguePath, checkLeaguePath, resourcePath, APPID, checkAutostart, toggleAutostart, VERSION, addCurrentProfile, profileList, removeProfile, renameProfile, editModeConfig, fetchModeConfig, replaceConfig, ISSUESURL, isOutdated, RELEASEURL
from lcu_driver import Connector
from ctypes import windll
from gui import Ui_MainWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QMessageBox, QInputDialog, QSystemTrayIcon, QMenu
from PyQt5.QtCore import QObject, QThread, pyqtSignal as Sig, pyqtSlot as Slot
from PyQt5.QtGui import QIcon, QPixmap

class Window(QMainWindow, Ui_MainWindow):
    startLCUrequested = Sig()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.iconPixmap = QPixmap(resourcePath("asset/icon.png"))
        self.WIcon = QIcon(resourcePath("asset/icon.png"))
        self.setWindowIcon(self.WIcon)

        self.checkUpdatesStartup()

        self.icon.setPixmap(self.iconPixmap)
        self.statusBar().showMessage("Waiting for League ...")
        self.configList.addItems(profileList())
        self.creds.setText(f"<html><head/><body><p><span style=\" font-size:20pt; font-weight:600;\">Adaptive {VERSION}</span></p><p><span style=\" font-size:10pt;\">by Ria</span></p></body></html>")
        self.windowOnStartup.setChecked(fetchConfig("showWindowOnStartup"))
        self.startWithWin.setChecked(checkAutostart())
        self.updateOnStartup.setChecked(fetchConfig("updateOnStartup"))
        self.updateLeaguePath()
        self.createSystemTray()
        self.connectSignalSlots()
        self.hide()

        self.lcuWorker = LCUWorker()
        self.lcuThread = QThread()
        self.lcuWorker.modes.connect(self.fetchedModes)
        self.startLCUrequested.connect(self.lcuWorker.startLCU)
        self.lcuWorker.moveToThread(self.lcuThread)
        self.lcuThread.start()
        self.startLCUrequested.emit()

    def changeEvent(self, event):
        event.accept()
        if event.type() == 105:
            self.hide()

    def createSystemTray(self):
        self.sysTray = QSystemTrayIcon(self)
        self.sysTray.setIcon(self.WIcon)
        self.sysTray.setVisible(True)
        self.sysTray.setToolTip("Adaptive")
        self.sysTray.activated.connect(self.sysTrayActivated)

        self.sysTrayMenu = QMenu(self)
        creds = self.sysTrayMenu.addAction(f"Adaptive {VERSION} - by Ria")
        creds.setDisabled(True)
        creds.setIcon(self.WIcon)
        self.sysTrayMenu.addSeparator()
        settingsAct = self.sysTrayMenu.addAction("Settings")
        settingsAct.triggered.connect(self.showNormal)
        exitAct = self.sysTrayMenu.addAction("Exit")
        exitAct.triggered.connect(self.close)

        self.sysTray.setContextMenu(self.sysTrayMenu)

    def sysTrayActivated(self, reason):
        if reason == 3:
            self.showNormal()

    def fetchedModes(self, modes: dict):
        self.modeNameId = modes
        self.statusBar().clearMessage()
        
        self.chooseMode.addItems(list(modes.keys()))
        self.updateConfigList()

        if fetchConfig("leaguePath") == "":
            editConfig("leaguePath", getLeaguePath())
            self.updateLeaguePath()
    
    def connectSignalSlots(self):
        self.sourceCode.clicked.connect(self.showSourceCode)
        self.chooseMode.activated[str].connect(self.modeChanged)
        self.chooseConfig.activated[str].connect(self.configChanged)
        self.pathBrowse.clicked.connect(self.selectLeaguePath)
        self.startWithWin.toggled.connect(toggleAutostart)
        self.addCurrent.clicked.connect(self.addProfile)
        self.removeConfig.clicked.connect(self.remProfile)
        self.renameConfig.clicked.connect(self.renProfile)
        self.windowOnStartup.toggled.connect(self.toggleWindowOnStartup)
        self.reportBug.clicked.connect(self.showReportBug)
        self.updateOnStartup.toggled.connect(self.toggleUpdateOnStartup)
        self.checkUpdates.clicked.connect(self.checkForUpdates)

    def checkUpdatesStartup(self):
        if fetchConfig("updateOnStartup"):
            outdated = isOutdated()
            if outdated:
                choice = QMessageBox.question(self, "Update available", f"A newer version of Adaptive detected ({outdated}). Do you want to visit the download site?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if choice == QMessageBox.Yes:
                    system(f"start \"\" {RELEASEURL}")

    def checkForUpdates(self):
        outdated = isOutdated()
        if outdated:
            choice = QMessageBox.question(self, "Update available", f"A newer version of Adaptive detected ({outdated}). Do you want to visit the download site?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if choice == QMessageBox.Yes:
                system(f"start \"\" {RELEASEURL}")
        else:
            QMessageBox.information(self, "No updates available", "You are already on the latest version.", QMessageBox.Ok)

    def toggleWindowOnStartup(self):
        editConfig("showWindowOnStartup", self.windowOnStartup.isChecked())

    def toggleUpdateOnStartup(self):
        editConfig("updateOnStartup", self.updateOnStartup.isChecked())
        
    def modeChanged(self, mode):
        self.updateConfigList()

    def configChanged(self, config):
        if config == "No changes": config = -1
        editModeConfig(self.modeNameId[self.chooseMode.currentText()], config)

    def updateConfigList(self):
        self.chooseConfig.clear()
        self.chooseConfig.addItem("No changes")
        self.chooseConfig.addItems(profileList())

        try:
            selected = fetchModeConfig(self.modeNameId[self.chooseMode.currentText()])
            if selected != -1:
                self.chooseConfig.setCurrentIndex(self.chooseConfig.findText(selected))
        except AttributeError: pass

    def updateLeaguePath(self):
        self.pathText.setText(fetchConfig('leaguePath'))

    def showSourceCode(self):
        system(f"start \"\" {GITHUBURL}")

    def showReportBug(self):
        system(f"start \"\" {ISSUESURL}")

    def selectLeaguePath(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        errorDialog = QMessageBox()
        errorDialog.setIcon(QMessageBox.Critical)
        errorDialog.setWindowIcon(self.WIcon)
        errorDialog.setText('Folder must contain the game League of Legends\nTypically "C:\\Riot Games\\League of Legends"')
        errorDialog.setWindowTitle("Invalid path")

        while True:
            if dialog.exec() == QDialog.Accepted:
                path = dialog.selectedFiles()[0].replace("/", "\\", -1)
                if checkLeaguePath(path):
                    editConfig("leaguePath", path)
                    self.updateLeaguePath()
                    break
                errorDialog.exec()
                continue
            break

    def addProfile(self):
        name, ok = QInputDialog.getText(self, "Enter a name for this Config", "Name:" + " " * 75)
        if name and ok:
            errorDialog = QMessageBox()
            errorDialog.setIcon(QMessageBox.Critical)
            errorDialog.setWindowTitle("An Error occured")
            errorDialog.setWindowIcon(self.WIcon)
            res = addCurrentProfile(name)
            if res == -1:
                errorDialog.setText('Name already existed.')
            elif res == -2:
                errorDialog.setText("Please set your League's path in the Settings tab.")
            elif res == -4:
                errorDialog.setText('Names cannot contain \\ / : * ? " < > |')
            elif res in (-3, 0):
                self.configList.addItem(name)
                self.updateConfigList()
                return
            errorDialog.exec()
    
    def remProfile(self):
        current = self.configList.currentItem()
        if current is None: return
        removeProfile(current.text())
        self.configList.takeItem(self.configList.currentRow())
        self.updateConfigList()
    
    def renProfile(self):
        current = self.configList.currentItem()
        if current is None: return

        name, ok = QInputDialog.getText(self, "Enter another name for this Config", "Name:" + " " * 85)
        if name and ok:
            errorDialog = QMessageBox()
            errorDialog.setIcon(QMessageBox.Critical)
            errorDialog.setWindowTitle("An Error occured")
            errorDialog.setWindowIcon(self.WIcon)
            res = renameProfile(current.text(), name)
            if res == -1:
                errorDialog.setText('Name already existed.')
            elif res == -4:
                errorDialog.setText('Names cannot contain \\ / : * ? " < > |')
            elif res == 0:
                self.configList.item(self.configList.currentRow()).setText(name)
                self.updateConfigList()
                return
            errorDialog.exec()


class LCUWorker(QObject):
    modes = Sig(dict)

    def __init__(self):
        super().__init__()
        self.connector = Connector()
        
        @self.connector.ready
        async def connect(connection):
            while True:
                modesm = await connection.request('get', '/lol-game-queues/v1/queues')
                if not modesm.status == 500:
                    modesm = await modesm.json()
                    break
            print("Logged in")

            maps = (await (await connection.request('get', '/lol-maps/v2/maps')).json())
            mapIdName = {}
            for map in maps:
                mapIdName[map["id"]] = map["name"]

            modesl = {}
            for mode in modesm:
                if mode["queueAvailability"] == "Available":
                    modesl[f'{mapIdName[mode["mapId"]]} ({mode["description"]})'] = mode["id"]
            modesl = {k: v for k, v in sorted(modesl.items())}
            modesl["Custom"] = -1
            self.modes.emit(modesl)

        @self.connector.ws.register("/lol-gameflow/v1/session", event_types = ("CREATE", "UPDATE", "DELETE"))
        async def gameFlow(connection, event):
            data = event.data
            phase = data['phase']
            
            if phase == "ChampSelect":
                queueId = data["gameData"]["queue"]["id"]
                print(queueId)
                config = fetchModeConfig(queueId)
                if config != -1:
                    replaceConfig(config)
                    print("Applied ", config)
                
    @Slot()
    def startLCU(self):
        self.connector.start()

if __name__ == "__main__":

    windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)

    app = QApplication(sys.argv)
    win = Window()
    if fetchConfig("showWindowOnStartup"):
        win.show()

    sys.exit(app.exec())