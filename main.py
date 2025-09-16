import sys
import sublime
import sublime_plugin
import subprocess
from datetime import datetime
from pathlib import Path
from .utils import admin
from datetime import datetime
from .utils.constants import pluginName


if int(sublime.version()) >= 3114:

    # Clear module cache to force reloading all modules of this package.
    prefix = __package__ + "."  # don't clear the base package
    for module_name in [
        module_name
        for module_name in sys.modules
        if module_name.startswith(prefix) and module_name != __name__
    ]:
        del sys.modules[module_name]
    prefix = None

    # Import public API classes
    # from .core.command import MyTextCommand
    # from .core.events import MyEventListener

    def plugin_loaded():
        """
        Initialize plugin
        """
        print(f'{pluginName} (re)loaded')
        pass

    def plugin_unloaded():
        """
        Complete tasks.
        Cleanup package caches.
        Exit threads.
        """
        print(f'{pluginName} unloaded')
        pass

else:
    raise ImportWarning("Doesn't support Sublime Text versions prior to 3114")


class MessageOutputUtils():
    def msgBox(self, msg):
        admin.msgBox(msg, self.name())

    def ok_cancel_dialog(self, msg):
        return admin.ok_cancel_dialog(msg, self.name())

    def status_message(self, msg):
        admin.status_message(msg, self.name())


class ScrapSaverCommand(sublime_plugin.TextCommand, MessageOutputUtils):
    """
    Cuts selected text from the file and pastes it to an identically named file (plus a '.scrap' suffix),
    `- which is located in a directory tree parallel to (mirroring) the project directory .
    """
    def run(self, edit):
        # Main:
        # Get selection(s)
        sel = self.view.sel()
        selblock = ''
        datestr = f'The text below was cut on {datetime.now().strftime("%d/%m/%Y")}'
        # datestr = f'{self.name()}: {datetime.now().strftime("%d/%m/%Y")}'
        # print(f'dir = {dir(self)}')
        # print(f'repr = {self.__repr__}')
        # print(f'name = {self.name()}')
        for s in sel:       
            if not s.empty():
                # build 'selblock' with selected text wrapped in meaningful context info and delimeters
                # allows for multiple selections
                # selblock += f'#{"-"*60}\n#{datestr}\n#{"-"*len(datestr)}\n{self.view.substr(s)}\n'
                selblock += f'#-----{datestr}-----\n{self.view.substr(s)}\n'
        if selblock:
            # something was selected for 'scrapping' so process it
            windowVariables = self.view.window().extract_variables()
            scrapTreeRoot, dotlessSuffix = admin.getScrappitVars(windowVariables, self.name())
            if scrapTreeRoot is None:
                return
            if not admin.checkAndCreateScrapRootDir(scrapTreeRoot, self.name()):
                return
            scrapWriteFile = admin.getScrappitFile(windowVariables, self.name(), create=True)
            if scrapWriteFile is None:
                return
            else:
                try:
                    with scrapWriteFile.open('a') as f:
                        f.write(f'{selblock}')
                except Exception as e:
                    self.msgBox(f'Error writing scrap to file: {str(scrapWriteFile)}\n\n{str(e)}\n\nAccordingly no text has been cut.')
                else:
                    self.view.replace(edit, s, '')
                    self.status_message(f'Selected scrap cut + sent text to: {str(scrapWriteFile)}')
        else:
            self.status_message('No text selected for scrapping. Nothing done.')


class ClickDecode():
    def get_path(self, paths):
        view = self.window.active_view()

        if paths:
            # a path has been passed to the command (ie. we've been called from the sidebar)
            return paths[0]

        if view and view.file_name():
            # check that the file actually exists on disk
            return view.file_name()

def subl(*args):
    # print(args)
    executable_path = sublime.executable_path()
    if sublime.platform() == 'osx':
        app_path = executable_path[:executable_path.rfind('.app/') + 5]
        executable_path = app_path + 'Contents/SharedSupport/bin/subl'

    subprocess.Popen([executable_path] + list(args))

class ScrapWholePathCommand(sublime_plugin.WindowCommand, MessageOutputUtils, ClickDecode):
    """
    Cuts selected text from the file and pastes it to an identically named file (plus a '.scrap' suffix),
    `- which is located in a directory tree parallel to (mirroring) the project directory .
    """
    def run(self, paths=[]):
        path = self.get_path(paths)
        # self.msgBox(f'path to scrap = {path}')
        if path is not None:
            srcPathObj = Path(path)
            print(f'source path = {str(srcPathObj)}')
            windowVariables = self.window.extract_variables()
            scrapTreeRoot, dotlessSuffix = admin.getScrappitVars(windowVariables, self.name())
            if scrapTreeRoot is None:
                return
            if not admin.checkAndCreateScrapRootDir(scrapTreeRoot, self.name()):
                return
            projectTLD = windowVariables.get('folder')
            if projectTLD is None:
                self.status_message('Error: Cannot determine sublime text\'s top level folder.')
                return
            projectPath = Path(projectTLD)
            if srcPathObj.samefile(projectPath):
                self.status_message('Cannot scrap the whole project. Only parts thereof.')
                return
            fileRelativePath = srcPathObj.relative_to(projectTLD)
            destPathMirrorObj = scrapTreeRoot.joinpath(fileRelativePath)
            dateSuffix = "_ALL" + datetime.now().strftime("%Y%m%d_%H%M%S")
            destPathScrapNamedObj = destPathMirrorObj.with_name(destPathMirrorObj.name + dateSuffix)
            print(f'dest path = {str(destPathScrapNamedObj)}')
            try:
                destPathScrapNamedObj.parents[0].mkdir(parents=True, exist_ok=True)
                srcPathObj.rename(destPathScrapNamedObj)
            except Exception as e_details:
                self.msgBox(f'Error moving {str(srcPathObj)} to: {str(destPathScrapNamedObj)}\n\n{str(e_details)}')

class OpenScrapProjectCommand(sublime_plugin.WindowCommand, MessageOutputUtils):
    """
    Opens a new sublime text instance focusing on the current project's scrap folder
    """
    def run(self):
        windowVariables = self.window.extract_variables()
        scrapTreeRoot, dotlessSuffix = admin.getScrappitVars(windowVariables, self.name())
        if scrapTreeRoot is None:
            return
        # print(f'want to open at {scrapTreeRoot}')
        subl('-n', str(scrapTreeRoot.resolve()))

class ScrapCompareCommand(sublime_plugin.WindowCommand, MessageOutputUtils):
    """
    Open the '.scrap' file corresponding to the current file.
    This file (if scraps have been saved to it) is located in a directory tree parallel to the project directory.
    """
    def run(self):
        w = self.window
        windowVariables = w.extract_variables()
        scrapWriteFile = admin.getScrappitFile(windowVariables, self.name(), create=False)
        if scrapWriteFile is None:
            self.msgBox(f"No scrap file found corresponding to: {windowVariables['file_name']}")
            return
        else:
            split_type = admin.get_active_plugin_settings().get('scrapCompareWindowSplit')
            if w.num_groups() == 1:
                if split_type in ['horizontal', 'vertical']:
                    if (split_type == "horizontal"):
                        w.run_command('set_layout', {
                            'cols': [0.0, 1.0],
                            'rows': [0.0, 0.33, 1.0],
                            'cells': [[0, 0, 1, 1], [0, 1, 1, 2]]
                        })
                    elif (split_type == "vertical"):
                        w.run_command('set_layout', {
                            "cols": [0.0, 0.46, 1.0],
                            "rows": [0.0, 1.0],
                            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
                        })
                    w.focus_group(1)
            file_path = f"{scrapWriteFile}:0:0"
            self.window.open_file(file_path, sublime.ENCODED_POSITION)