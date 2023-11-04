from os import path as op, getenv, listdir, makedirs, remove, rmdir, rename
import sys
from psutil import process_iter as pi
from pickle import load, dump
import winreg
from configparser import ConfigParser as CfgP
from requests import get

VERSION = "v1.0"
GITHUBURL = "https://github.com/developers192/Adaptive"
RELEASEURL = GITHUBURL + "/releases/latest"
ISSUESURL = GITHUBURL + "/issues/new"
APPID = f'com.ria.adaptive.{VERSION[1:].replace(".", "")}'
PROFILESDIR = op.join(getenv("APPDATA"), "Adaptive", "Profiles")
DEFAULTCONFIG = {
	"leaguePath": "",
	"showWindowOnStartup": True,
	"updateOnStartup": True,
	"modeConfigs": {}
}
CONFIGDIR = op.join(getenv("APPDATA"), "Adaptive", "config.adapt")

def resourcePath(relative_path):
	try:
		base_path = sys._MEIPASS
	except Exception:
		base_path = op.abspath(".")

	return op.join(base_path, relative_path)

def procPath(name):
	for proc in pi():
		if proc.name() == name:
			return proc.exe()
	return False

def checkLeaguePath(path):
	try:
		for p in listdir(path):
			if p == "LeagueClient.exe":
				return True
	except:
		return False
	return False

def getLeaguePath():
	path = procPath("LeagueClient.exe")
	if path:
		path = op.dirname(path)
		return path
	return ""

def fetchConfig(entry):
	makedirs(op.dirname(CONFIGDIR), exist_ok = True)
	try:
		with open(CONFIGDIR, "rb") as f:
			data = load(f)
	except FileNotFoundError:
		with open(CONFIGDIR, "wb") as f:
			dump(DEFAULTCONFIG, f)
		data = DEFAULTCONFIG
	try: data = data[entry]
	except KeyError: 
		editConfig(entry, DEFAULTCONFIG[entry])
		data = DEFAULTCONFIG[entry]
	return data

def editConfig(entry, value):
	makedirs(op.dirname(CONFIGDIR), exist_ok = True)
	with open(CONFIGDIR, "rb") as f:
		data = load(f)
	data[entry] = value
	with open(CONFIGDIR, "wb") as f:
		dump(data, f)
	return

def currentPath():
	if hasattr(sys, 'frozen'):
		basis = sys.executable
	else:
		basis = sys.argv[0]
	return basis

def toggleAutostart():
    with winreg.OpenKey(
            key=winreg.HKEY_CURRENT_USER,
            sub_key=r'Software\Microsoft\Windows\CurrentVersion\Run',
            reserved=0,
            access=winreg.KEY_ALL_ACCESS,
    ) as key:
        try:
            if not checkAutostart():
                winreg.SetValueEx(key, "RiaAdaptive", 0, winreg.REG_SZ, currentPath())
            else:
                winreg.DeleteValue(key, "RiaAdaptive")
        except OSError:
            return False
    return True

def checkAutostart():
    with winreg.OpenKey(
            key=winreg.HKEY_CURRENT_USER,
            sub_key=r'Software\Microsoft\Windows\CurrentVersion\Run',
            reserved=0,
            access=winreg.KEY_ALL_ACCESS,
    ) as key:
        idx = 0
        while idx < 1_000:     # Max 1.000 values
            try:
                key_name, _, _ = winreg.EnumValue(key, idx)
                if key_name == "RiaAdaptive":
                    return True
                idx += 1
            except OSError:
                break
    return False

def profileList():
	makedirs(PROFILESDIR, exist_ok = True)
	return list(listdir(PROFILESDIR))

def addCurrentProfile(name):
	if name in profileList() or name == "No changes":
		return -1
	if len(set(("\\", "/", ":", "*", "?", '"', "<", ">", "|")).intersection(name)) > 0:
		return -4
	makedirs(op.join(PROFILESDIR, name), exist_ok = True)
	
	leaguePath = fetchConfig("leaguePath")
	if leaguePath == "": return -2

	dat = {}
	for t in ("game.cfg", "input.ini"):
		try:
			with open(op.join(fetchConfig("leaguePath"), "Config", t), "r") as f:
				dat[t] = f.read()
		except FileNotFoundError:
			return -3
	
	for t in dat:
		with open(op.join(PROFILESDIR, name, t), "w") as f:
			f.write(dat[t])

	return 0

def removeProfile(name):
	for t in ("game.cfg", "input.ini"):
		try: remove(op.join(PROFILESDIR, name, t))
		except OSError: pass
	try: rmdir(op.join(PROFILESDIR, name))
	except OSError: pass

	current = fetchConfig("modeConfigs")
	for k in current.copy():
		if current[k] == name:
			del current[k]
	editConfig("modeConfigs", current)

def renameProfile(name, newName):
	if newName in profileList() or newName == "No changes":
		return -1
	if len(set(("\\", "/", ":", "*", "?", '"', "<", ">", "|")).intersection(newName)) > 0:
		return -4
	try:
		rename(op.join(PROFILESDIR, name), op.join(PROFILESDIR, newName))
	except: return -2

	current = fetchConfig("modeConfigs")
	for k in current:
		if current[k] == name:
			current[k] = newName
	editConfig("modeConfigs", current)
	return 0

def fetchModeConfig(modeId):
	current = fetchConfig("modeConfigs")
	try: return current[modeId]
	except KeyError:
		return -1

def editModeConfig(modeId, config):
	current = fetchConfig("modeConfigs")
	if config == -1:
		if modeId in current:
			del current[modeId]
	else:
		current[modeId] = config
	editConfig("modeConfigs", current)
	print(fetchConfig("modeConfigs"))

def replaceConfig(config):
	for t in ("game.cfg", "input.ini"):
		cfg = CfgP()
		cfg.optionxform = str
		cfg.read(op.join(PROFILESDIR, config, t))
		cfgL = CfgP()
		cfgL.optionxform = str
		cfgL.read(op.join(fetchConfig("leaguePath"), "Config", t))
		
		for section in cfg:
			for option in cfg[section]:
				cfgL[section][option] = cfg[section][option]

		with open(op.join(fetchConfig("leaguePath"), "Config", t), "w") as f:
			cfgL.write(f, space_around_delimiters = False)

def isOutdated():
	latestver = get(RELEASEURL).url.split(r"/")[-1]
	if latestver != VERSION:
		return latestver
	return False