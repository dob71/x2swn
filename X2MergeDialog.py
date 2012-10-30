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

class X2MergeDialog(wx.Dialog, pronsole.pronsole):
    '''Gcode mixer for dual extruder prints.'''
    def __init__(self, *args, **kwds):
        pronsole.pronsole.__init__(self)

        kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.RESIZE_BORDER
        wx.Dialog.__init__(self, *args, **kwds)
        self.okButton = wx.Button(self, wx.ID_OK, "Generate and Load")
        self.cancelButton = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.OnExit, self.cancelButton)
        self.Bind(wx.EVT_BUTTON, self.OnSave, self.okButton)

        self.scrollbarPanel = wx.ScrolledWindow(self, -1, style=wx.TAB_TRAVERSAL)
        self.browseButton1 = wx.Button(self.scrollbarPanel, wx.ID_ANY, "...", name = 'base')
        self.browseButton2 = wx.Button(self.scrollbarPanel, wx.ID_ANY, "...", name = 'ins')
        self.Bind(wx.EVT_BUTTON, self.onBrowse, self.browseButton1)
        self.Bind(wx.EVT_BUTTON, self.onBrowse, self.browseButton2)
        
        self.settings.colorOn = 'c_on.gcode'
        self.settings.colorOff = 'c_off.gcode'
        self.settings.basePenGcode = 'base_penultimate.g'
        self.settings.insPenGcode = 'insert_penutimate.g'
        self.mixedGcode = None
        self.load_default_rc(".x2mergerc")

        self.__set_properties()   
        self.__do_layout()        

        self.Center()
        self.Show()
        
    def __set_properties(self):
        self.SetTitle("X2 Merge")
        
        # For some reason the dialog size is not consistent between Windows and Linux - this is a hack to get it working 
        self.SetMinSize(wx.DLG_SZE(self, (465, 220)))
        self.SetPosition((0, 0))
        
    def __do_layout(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.scrollbarPanel.SetScrollRate(10, 10)
        self.scrollbarPanel.SetSizer(self.getFileSettings())
        mainSizer.Add(self.scrollbarPanel, 1, wx.EXPAND | wx.ALL, 5)
		
        actionsSizer = wx.BoxSizer(wx.HORIZONTAL)
        actionsSizer.Add(self.okButton, 0, 0, 0)
        actionsSizer.Add(self.cancelButton, 0, wx.LEFT, 10)
        mainSizer.Add(actionsSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
		
        self.SetSizer(mainSizer)
        self.Layout()

    def makeUpMixFileName(self, filename):
        if (re.search("penultimate[^/\\\]*$", filename) != None):
            mixed = re.sub("penultimate([^/\\\\]*)$", "mixed\\1", filename)
        else:
            mixed = re.sub("(\\.[^\\./\\\\]*)$", "_mixed.g", filename)
        if (mixed == None):
            mixed = "mixed.g"
        self.outFileTc.SetValue(mixed)
                
    def Mix(self, out):
        fn_base = self.settings.basePenGcode
        fn_color = self.settings.insPenGcode
        fn_alt_start = os.path.join(self.altpath, self.settings.colorOn)
        fn_alt_end = os.path.join(self.altpath, self.settings.colorOff)
        mixed_layers = 0

        if (len(fn_alt_start) == 0):
            fn_alt_start = os.path.join(self.altpath, 'pla_c_on.gcode')
        if (len(fn_alt_end) == 0):
            fn_alt_end = os.path.join(self.altpath, 'pla_c_off.gcode')

        ALTSTART = open(fn_alt_start, 'r') 
        ALTEND = open(fn_alt_end, 'r')
        BASE = open(fn_base, 'r')
        COLOR = open(fn_color, 'r')

        # Read in the alt start and stop files
        alt_start = '';
        for l in ALTSTART:
            l = l.rstrip('\n').rstrip('\r')
            l = re.sub(';.*', '', l).strip()
            if (len(l) > 0):
                alt_start += (l + '\n')
        ALTSTART.close()
        alt_stop = ''
        for l in ALTEND:
            l = l.rstrip('\n').rstrip('\r')
            l = re.sub('[;(].*', '', l).strip()
            if (len(l) > 0):
                alt_stop += (l + '\n')
        ALTEND.close()

        # Read in the layers of the color model, format: (<layer> 0.32 )
        color_layer = {}
        layer_height = 0.0
        g_one_seen = False
        layer_code = '';
        in_layer_code = False
        g_one_seen = False
        for l in COLOR:
            if (not in_layer_code) and ('<layer>' in l):
                in_layer_code = True;
            elif in_layer_code and ('</layer>' in l):
                in_layer_code = False;
            elif not in_layer_code:
                continue
            if '</layer>' in l: 
                if g_one_seen:
                    color_layer[layer_height] = layer_code
                layer_code = '' 
                g_one_seen = False
                continue 
            m = re.match(r'.*<layer>\s+([\d\.]+)', l)
            if m:
                layer_height = float(m.group(1))
            l = l.rstrip('\n').rstrip('\r')
            l = re.sub('[;(].*', '', l).strip()
            if (len(l) > 0):
                layer_code += (l + '\n')
                if l.startswith('g1') or l.startswith('G1'):
                    g_one_seen = True
        COLOR.close()
        # Read and print the base gcode lines doing what the script is designed for
        layer_height = 0.0
        for l in BASE:
            # capture the layer height
            m = re.match(r'.*<layer>\s+([\d\.]+)', l)
            if m:
                layer_height = float(m.group(1))
                continue
            # if done with the layer add matching color part layer
            if ('</layer>' in l):
                if (layer_height in color_layer) and (len(color_layer[layer_height]) > 0):
                    print >>out, alt_start + color_layer[layer_height] + alt_stop
                    mixed_layers += 1
                continue
            l = l.rstrip('\n').rstrip('\r')
            l = re.sub('[;(].*', '', l).strip()
            if (len(l) > 0):
                print >>out, l
        BASE.close()
        return mixed_layers

    def onBrowse(self, e):
        if ('base' == e.GetEventObject().GetName()):
           filename = self.baseTc.GetValue()
           dname = "Path to base penultimate gcode file"
           usefilter = 1
        if ('ins' == e.GetEventObject().GetName()):
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
        if ('base' == e.GetEventObject().GetName()):
           self.baseTc.SetValue(filename)
           self.makeUpMixFileName(filename)
        if ('ins' == e.GetEventObject().GetName()):
           self.insTc.SetValue(filename)

    def getFileSettings(self):
        settingsSizer = wx.BoxSizer(wx.VERTICAL)
        settingsRow = 0

        infoStaticBox = wx.StaticBox(self.scrollbarPanel, -1, "X2 Merge Info")
        infoStaticBoxSizer = wx.StaticBoxSizer(infoStaticBox, wx.VERTICAL)
        infoSizer = wx.GridBagSizer(hgap=1, vgap=1)
        infoSizer.AddGrowableCol(0)
        text = "This script mixes Skeinforge penultimate gcode files \
and produces printing instructions for 2 extruder prints. \
The 'base' (to be printed by Ext 0) and 'insert' (to be printed by Ext 1) \
files should be Skeinforge penultimate gcode files (see Skeinforge Export settings) \
sliced at the same layer height.\n\
The extruder 1 on/off files (they are picked from the Skeinforge alterations folder) are inserted \
when the extruder has to switch from 0 to 1 and then back to 0 while printing a layer. \n\
The resulted merged gcode is stripped and automatically loaded for printing by pronterface UI. \
It is also saved in the automatically generated file named as shown in the 'Output file name' box."
        infoText = wx.StaticText(self.scrollbarPanel, -1, text)
        infoStaticBoxSizer.SetMinSize((600, -1))
        infoText.Wrap(600)
        infoSizer.Add(infoText, pos=(0, 0))
        infoStaticBoxSizer.Add(infoSizer, 1, wx.EXPAND | wx.ALL, 0)
        settingsSizer.Add(infoStaticBoxSizer, 1, wx.EXPAND | wx.ALL, 0)
        
        parametersBoxSizer = wx.BoxSizer(wx.VERTICAL)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Base penultimate gcode:")
        settingLabel.Wrap(200)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.basePenGcode, size=(200, -1))
        self.baseTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingSizer.Add(self.browseButton1, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Insert penultimate gcode:")
        settingLabel.Wrap(200)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.insPenGcode, size=(200, -1))
        self.insTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingSizer.Add(self.browseButton2, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Ext 1 On gcode:")
        settingLabel.Wrap(200)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.colorOn, size=(200, -1))
        self.extOnTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Ext 1 Off gcode:")
        settingLabel.Wrap(200)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value=self.settings.colorOff, size=(200, -1))
        self.extOffTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)

        settingRow = wx.BoxSizer(wx.VERTICAL)
        settingSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingLabel = wx.StaticText(self.scrollbarPanel, -1, "Output file name:")
        settingLabel.Wrap(200)
        settingSizer.Add(settingLabel, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        textCtrl = wx.TextCtrl(self.scrollbarPanel, value='', size=(150, -1))
        self.outFileTc = textCtrl
        settingSizer.Add(textCtrl, 0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        settingRow.Add(settingSizer, 0, wx.TOP, 10)
        parametersBoxSizer.Add(settingRow, 0, wx.EXPAND, 0)
        self.makeUpMixFileName(self.settings.basePenGcode)

        settingsSizer.Add(parametersBoxSizer, 0, wx.EXPAND | wx.ALL, 0)

        return settingsSizer

    def OnExit(self, e):
        self.EndModal(-1)
        self.Destroy()
        
    def OnSave(self, e):
        self.settings.colorOn = self.extOnTc.GetValue()
        self.settings.colorOff = self.extOffTc.GetValue()
        self.settings.basePenGcode = self.baseTc.GetValue()
        self.settings.insPenGcode = self.insTc.GetValue()
        self.set("colorOn", self.settings.colorOn)
        self.set("colorOff", self.settings.colorOff)
        self.set("basePenGcode", self.settings.basePenGcode)
        self.set("insPenGcode", self.settings.insPenGcode)
        self.altpath = archive.getSettingsPath('alterations')
        mixed = self.outFileTc.GetValue()
        try:
            out=open(mixed,"w+")
            out.write("")
        except IOError,x:
            print str(x)
            self.EndModal(2)
            self.Destroy()
            return

        print "Starting gcode mixing script..."

        try:
            mixed_layers = self.Mix(out)
            code = 0
        except IOError, e:
            print e.errno
            print e
            code = -1
        except:
            print "The script has failed. Internal error!"
            code = -1

        if (code != 0):
           try:
               os.remove(mixed)
           except:
               pass
           self.EndModal(2)
           self.Destroy()
        else:   
           out.close()
           print "Done, successfully mixed %d layers" % mixed_layers
           self.mixedGcode = mixed
           self.EndModal(1)
           self.Destroy()

    def GetPath(self):
        return self.mixedGcode

class SkeinforgeX2MergeApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        return True

if __name__ == "__main__":
    skeinforgeX2MergeApp = SkeinforgeX2MergeApp(0)
    X2MergeDialog(None, -1, "").ShowModal()
    exit()
