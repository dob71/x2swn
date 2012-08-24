#!/usr/bin/env python

from skeinforge.fabmetheus_utilities import archive
from subprocess import STDOUT
import printcore
import pronsole
import sys
import re
import os
import shutil
import subprocess
import wx

DEF_NT_PERL_PATH = 'C:\\cygwin\\bin\\perl addcolor.pl'
DEF_PERL_PATH = './addcolor.pl'

ID_BROWSE_BASE = 102
ID_BROWSE_INS = 103

class X2MergeDialog(wx.Dialog, pronsole.pronsole):
    '''GUI Frontend to addcolor.pl script.'''
    def __init__(self, *args, **kwds):
        pronsole.pronsole.__init__(self)
        self.mypath = os.path.abspath(os.path.dirname(sys.argv[0]))

        x2swProfilesPath = os.path.join(os.path.expanduser('~'), '.x2sw')
        rcDistroFilename = os.path.join(self.mypath, '.x2sw', '.x2mergerc')
        if(not os.path.exists(os.path.join(x2swProfilesPath, '.use_local'))):
            rcPathName = os.path.join(x2swProfilesPath, ".x2mergerc")
            try:
                if(not os.path.exists(x2swProfilesPath)):
                    print "Creating x2sw profiles path: " + x2swProfilesPath
                    os.makedirs(x2swProfilesPath)
                if((not os.path.exists(rcPathName)) and os.path.exists(rcDistroFilename)):
                    print "Deploying x2merge distro rc file to: " + rcPathName
                    shutil.copyfile(rcDistroFilename, rcPathName)
            except:
                print "Failure!"
        else:
            rcPathName = rcDistroFilename
        print "Using x2merge rc file pathname: " + rcPathName
        self.rc_filename = rcPathName

        kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.RESIZE_BORDER
        wx.Dialog.__init__(self, *args, **kwds)
        self.okButton = wx.Button(self, wx.ID_OK, "Generate and Load")
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.browseButton1 = wx.Button(self, ID_BROWSE_BASE, "...")
        self.browseButton2 = wx.Button(self, ID_BROWSE_INS, "...")
        self.Bind(wx.EVT_BUTTON, self.OnExit, self.cancelButton)
        self.Bind(wx.EVT_BUTTON, self.OnSave, self.okButton)
        self.Bind(wx.EVT_BUTTON, self.onBrowse, self.browseButton1)
        self.Bind(wx.EVT_BUTTON, self.onBrowse, self.browseButton2)
        
        if (os.name == 'nt'):
            self.settings.perlCmd = DEF_NT_PERL_PATH
        else: 
            self.settings.perlCmd = DEF_PERL_PATH
        self.settings.colorOn = 'c_on.gcode'
        self.settings.colorOff = 'c_off.gcode'
        self.settings.basePenGcode = 'base_penultimate.g'
        self.settings.insPenGcode = 'insert_penutimate.g'
        self.mixedGcode = None
        self.load_rc(self.rc_filename)

        self.scrollbarPanel = wx.ScrolledWindow(self, -1, style=wx.TAB_TRAVERSAL)
        self.settingsSizer = self.getFileSettings()
        self.scrollbarPanel.SetSizer(self.settingsSizer)

        self.__set_properties()   
        self.__do_layout()        
        self.Center()
        self.Show()
        
    def __set_properties(self):
        self.SetTitle("X2 Merge")
        
        # For some reason the dialog size is not consistent between Windows and Linux - this is a hack to get it working 
        if (os.name == 'nt'):
            self.SetMinSize(wx.DLG_SZE(self, (465, 245)))
        else:
            self.SetSize(wx.DLG_SZE(self, (465, 200)))
            
        self.SetPosition((0, 0))
        self.scrollbarPanel.SetScrollRate(10, 10)
        
    def __do_layout(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self.scrollbarPanel, 1, wx.EXPAND | wx.ALL, 5)
        actionsSizer = wx.BoxSizer(wx.HORIZONTAL)
        actionsSizer.Add(self.okButton, 0, 0, 0)
        actionsSizer.Add(self.cancelButton, 0, wx.LEFT, 10)
        mainSizer.Add(actionsSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        self.SetSizer(mainSizer)
        self.Layout()
                
    def onBrowse(self, e):
        if (ID_BROWSE_BASE == e.GetId()):
           filename = self.baseTc.GetValue()
           dname = "Path to base penultimate gcode file"
           usefilter = 1
        if (ID_BROWSE_INS == e.GetId()):
           filename = self.insTc.GetValue()
           dname = "Path to insert penultimate gcode file"
           usefilter = 1
        basedir = "."
        try:
            basedir=os.path.split(filename)[0]
        except:
            pass
        dlg=wx.FileDialog(self,dname,basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        if (usefilter == 1):
            dlg.SetWildcard("GCODE files (;*.gcode;*.gco;*.g;)")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            if not(os.path.exists(name)):
                wx.MessageBox("File not found!","Error")
                return
            path = os.path.split(name)[0]
        else:
            return
        filename = name
        if (ID_BROWSE_BASE == e.GetId()):
           filename = self.baseTc.SetValue(filename)
        if (ID_BROWSE_INS == e.GetId()):
           filename = self.insTc.SetValue(filename)

    def getFileSettings(self):
        settingsSizer = wx.BoxSizer(wx.VERTICAL)
        settingsRow = 0

        infoStaticBox = wx.StaticBox(self.scrollbarPanel, -1, "X2 Merge Info")
        infoStaticBoxSizer = wx.StaticBoxSizer(infoStaticBox, wx.VERTICAL)
        infoSizer = wx.GridBagSizer(hgap=1, vgap=1)
        infoSizer.AddGrowableCol(0)
        text = "This dialog allows selection of the files for passing over \
to the addcolor.pl script. The script mixes gcode from the files \
and produces printing instructions for 2 extruder prints. \
The 'base' (to be printed by Ext 0) and 'insert' (to be printed by Ext 1) \
files should be Skeinforge penultimate gcode files (see Skeinforge Export settings) \
sliced at the same layer height.\n\
The extruder 1 on/off files (they are picked from the Skeinforge alterations folder) are inserted \
when the extruder has to switch from 0 to 1 and then back to 0 while printing a layer. \n\
You might need to edit the path to perl in the script command line if your  \
setup doesn't work with the default setting. \n\
The resulted merged gcode is stripped and automatically loaded for printing by pronterface UI."
        infoText = wx.StaticText(self.scrollbarPanel, -1, text)
        if (os.name == 'nt'):
            infoStaticBoxSizer.SetMinSize((320, -1))
            infoText.Wrap(600)
        else: 
            infoStaticBoxSizer.SetMinSize((450, -1))
            infoText.Wrap(410)
        infoSizer.Add(infoText, pos=(0, 0))
        infoStaticBoxSizer.Add(infoSizer, 1, wx.EXPAND | wx.ALL, 0)
        settingsSizer.Add(infoStaticBoxSizer, 1, wx.EXPAND | wx.ALL, 0)
        
        parametersBoxSizer = wx.BoxSizer(wx.VERTICAL)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Base penultimate gcode:")
        settingLabel.Wrap(300)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.basePenGcode, size=(150, -1))
        self.baseTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingSizer.Add(self.browseButton1, 0, wx.LEFT|wx.TOP, 10)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Insert penultimate gcode:")
        settingLabel.Wrap(300)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.insPenGcode, size=(150, -1))
        self.insTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingSizer.Add(self.browseButton2, 0, wx.LEFT|wx.TOP, 10)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Ext 1 On gcode:")
        settingLabel.Wrap(300)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.colorOn, size=(150, -1))
        self.extOnTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Ext 1 Off gcode:")
        settingLabel.Wrap(300)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.colorOff, size=(150, -1))
        self.extOffTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Script command line:")
        settingLabel.Wrap(300)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.perlCmd, size=(150, -1))
        self.perlExeTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingsSizer.Add(parametersBoxSizer, 0, wx.EXPAND | wx.ALL, 0)

        return settingsSizer

    def OnExit(self, e):
        self.Destroy()
        
    def OnSave(self, e):
        self.settings.colorOn = self.extOnTc.GetValue()
        self.settings.colorOff = self.extOffTc.GetValue()
        self.settings.basePenGcode = self.baseTc.GetValue()
        self.settings.insPenGcode = self.insTc.GetValue()
        self.settings.perlCmd = self.perlExeTc.GetValue()
        self.set("colorOn", self.settings.colorOn)
        self.set("colorOff", self.settings.colorOff)
        self.set("basePenGcode", self.settings.basePenGcode)
        self.set("insPenGcode", self.settings.insPenGcode)
        self.set("perlCmd", self.settings.perlCmd)
        altpath = archive.getSettingsPath('alterations')
        if (re.search("penultimate[^/\\\]*$", self.settings.basePenGcode) != None):
            mixed = re.sub("penultimate([^/\\\\]*)$", "mixed\\1", self.settings.basePenGcode)
        else:
            mixed = re.sub("(\\.[^\\./\\\\]*)$", "_mixed.g", self.settings.basePenGcode)
        if (mixed == None):
            mixed = "mixed.g"
        cmd = self.settings.perlCmd + " '"  + self.settings.basePenGcode + "' '" +  self.settings.insPenGcode + \
              "' '" + altpath + "\\" + self.settings.colorOn + "' '" + altpath + "\\" + self.settings.colorOff + "'"
        try:
            out=open(mixed,"w+")
            out.write("")
        except IOError,x:
            print str(x)
            self.EndModal(2)
            self.Destroy()
            return
        print "Starting gcode mixing script:\n", cmd
        code = subprocess.call(cmd, stdout=out, stderr=out)
        if (code != 0):
           out.seek(0)
           outErr = out.read();
           out.close()
           os.remove(mixed)
           print "Failure, code " + str(code) + ". Output:\n" + outErr;
           self.EndModal(2)
           self.Destroy()
        else:   
           out.close()
           print "Done, successfully mixed"
           self.mixedGcode = mixed
           self.EndModal(1)
           self.Destroy()

    def GetPath(self):
        return self.mixedGcode

class SkeinforgeX2MergeApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        print X2MergeDialog(None, -1, "").ShowModal()
        return 1

if __name__ == "__main__":
    skeinforgeX2MergeApp = SkeinforgeX2MergeApp(0)
    skeinforgeX2MergeApp.MainLoop()
