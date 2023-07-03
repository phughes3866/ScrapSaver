import os
import string
import sublime
from pathlib import Path
from datetime import datetime
from .constants import pluginName, pluginSettingsFile


def msgBoxTitle(fromCommand=None, oneLine=False):
    titleStr = f'{pluginName}'
    if oneLine:
        pluspart = ['', f'[{fromCommand}]'][fromCommand is not None]
    else:
        pluspart = ['', f'\n[Command: {fromCommand}]'][fromCommand is not None]
    return f'{titleStr}{pluspart}'


def msgBox(msg: str, fromCommand=None):
    sublime.message_dialog(f'{msgBoxTitle(fromCommand)}\n\n{msg}')


def status_message(msg: str, fromCommand=None):
    sublime.status_message(f'{msgBoxTitle(fromCommand, oneLine=True)}: {msg}')


def ok_cancel_dialog(msg: str, fromCommand=None):
    return sublime.ok_cancel_dialog(f'{msgBoxTitle(fromCommand)}\n\n{msg}')


def getScrappitVars(windowVariables, callerName):
    def errorInScrapFolderStr(e):
        msgBox(f'Error calculating path for scrap-tree-mirror:\n\n [{str(e)}]\n\nCheck your {pluginName} settings.', callerName)

    active_settings = get_active_plugin_settings()
    scrapTreeRootStr = active_settings.get('scrapFolderName', '')
    allScrapsParentDir = active_settings.get('allScrapsParentDir', '')
    dotlessSuffix = active_settings.get('scrapSuffix', 'scrap').strip(string.punctuation)
    if scrapTreeRootStr == "":
        try:
            if allScrapsParentDir == "":
                scrapTreeRootPath = Path(f"{windowVariables['folder']}_{dotlessSuffix}")
            else:
                scrapTreeRootPath = Path(allScrapsParentDir, os.path.basename(windowVariables['folder']))
        except Exception as e:
            errorInScrapFolderStr(e)
            return None, None
    else:
        try:
            scrapTreeRootPath = Path(scrapTreeRootStr)
        except Exception as e:
            errorInScrapFolderStr(e)
            return None, None
        else:
            if not scrapTreeRootPath.is_absolute():
                errorInScrapFolderStr(f'Settings yielded a relative path [{str(scrapTreeRootPath)}]. An absolute path is required.')
                return None, None
            elif Path(f"{windowVariables['folder']}") in scrapTreeRootPath.parents:
                errorInScrapFolderStr(f'Cannot be a subfolder of the project directory. {str(scrapTreeRootPath)} is disallowed.')
                return None, None
    return scrapTreeRootPath, dotlessSuffix


def getScrappitFile(windowVariables, callerName, create=True):
    scrapTreeRoot, dotlessSuffix = getScrappitVars(windowVariables, callerName)
    if scrapTreeRoot is None:
        return None
    else:
        fileRelativePath = Path(windowVariables['file_path']).relative_to(windowVariables['folder'])
        # print(f"rel path: {fileRelativePath}")
        scrapWriteDir = scrapTreeRoot.joinpath(fileRelativePath)
        scrapWriteFile = scrapTreeRoot.joinpath(fileRelativePath, windowVariables['file_name'] + f'.{dotlessSuffix}')
        if scrapWriteFile.is_file():
            return scrapWriteFile
        elif create:
            titleMsg = f'# Scrap collection file created by Sublime Text plugin: {pluginName} {datetime.now().strftime("%d %B, %Y")} #'
            boundaryStr = f"{'#'*len(titleMsg)}"
            newFileMsg = f"{boundaryStr}\n{titleMsg}\n{boundaryStr}\n"
            try:
                scrapWriteDir.mkdir(parents=True, exist_ok=True)
                scrapWriteFile.write_text(newFileMsg)
            except Exception as e:
                msgBox(f'Error creating new scrap file [{scrapWriteFile.name()}]\n\n{str(e)}', callerName)
                return None
            else:
                return scrapWriteFile


def checkAndCreateScrapRootDir(thisScrapRoot, callerName, create=True):
    if not thisScrapRoot.exists():
        if create is True:
            if ok_cancel_dialog(f"Create new directory for scraps?\n\nMake: {thisScrapRoot} ??", callerName):
                try:
                    thisScrapRoot.mkdir(parents=True)
                # except FileExistsError:
                except Exception as e:
                    # directory already exists
                    msgBox(f"Unable to create folder: {thisScrapRoot}\n\nError: {str(e)}")
                    return False
            else:
                return True
    elif thisScrapRoot.is_dir():
        if not os.access(str(thisScrapRoot), os.W_OK):
            msgBox(f"Error: Dir {str(thisScrapRoot)} is not writeable.", callerName)
            return False
        else:
            return True
    else:
        msgBox(f"Error: The configured scrap directory [{str(thisScrapRoot)}] points to a non-directory entity.", callerName)
        return False


def get_active_plugin_settings():
    my_plugin_factory_settings = sublime.load_settings(pluginSettingsFile).to_dict()
    cur_proj_plugin_overrides = sublime.active_window().active_view().settings().get(pluginName, {})
    # any current project settings in the .sublime-project file will override same name Default/User 
    # `- (factory) settings in the plugin's .sublime-settings file
    active_settings = dict(my_plugin_factory_settings, **cur_proj_plugin_overrides)
    return active_settings
