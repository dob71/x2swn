#!/usr/bin/env python
#
# This file is part of the X2SW bundle. You can redistribute it and/or 
# modify it under the terms of the GNU General Public License as published 
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import wx
import wx.wizard as wiz
import re
import tempfile
import shutil

from dulwich.client import get_transport_and_path
from dulwich.errors import ApplyDeltaError
from dulwich.index import Index, build_index_from_tree
from dulwich.pack import Pack, sha_to_hex
from dulwich.repo import Repo
from dulwich.server import update_server_info
from dulwich import client

VERSION_FILE = 'version.txt'
COMPAT_FILE = '.compat_ver_str.txt'

pronterface_restart = False

########################################################################
class TitledPage(wiz.WizardPageSimple):
    """"""
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        """Constructor"""
        wiz.WizardPageSimple.__init__(self, parent)
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer = sizer
        self.SetSizer(sizer)
 
        title = wx.StaticText(self, -1, title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        sizer.Add(title, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        sizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.ALL, 5)

########################################################################
class UpdateRepoPage(wiz.PyWizardPage):
    """Startup wizard page"""
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        wiz.PyWizardPage.__init__(self, parent)
        self.next = self.prev = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        title = wx.StaticText(self, label=title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sizer.Add(title)
 
        self.sizer.Add(wx.StaticText(self, -1, "\
This wizard helps you select and deploy X2SW profiles for your printer. Each\n\
X2SW profile contains configuration files for multiple software components\n\
(Slic3r profiles, Skeinforge profiles, Pronterface rc file).\n\
\n\
The profiles from either the online or local X2SW profile repository can be\n\
deployed. When deployed the profile files override the currently active\n\
configuration files of the software included in X2SW bundle."), 0, wx.ALL, 5)

        self.sizer.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5)
        self.offline_mode = wx.CheckBox(self, wx.ID_ANY, 'Use local repository (off-line mode)')
        self.sizer.Add(self.offline_mode)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)
 

    #----------------------------------------------------------------------
    def Run(self):
        global x2ProfilerApp
        self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
        x2ProfilerApp.repo = None
        if not x2ProfilerApp.tmp_repo_path == None:
            try:
                shutil.rmtree(x2ProfilerApp.tmp_repo_path)
            except:
                wx.MessageBox('Unable to delete: ' + x2ProfilerApp.tmp_repo_path, '', style = wx.OK|wx.ICON_EXCLAMATION)
                pass
            x2ProfilerApp.tmp_repo_path = None

    #----------------------------------------------------------------------
    def SetNext(self, next):
        self.next = next
 
    #----------------------------------------------------------------------
    def SetPrev(self, prev):
        self.prev = prev
 
    #----------------------------------------------------------------------
    def GetNext(self):
        if not self.offline_mode.GetValue():
            return self.next
        else:
            return self.next.GetNext()
 
    #----------------------------------------------------------------------
    def GetPrev(self):
        return self.prev

    #----------------------------------------------------------------------
    def OnPageChanging(self, event):
        # If no temp repo then we need to use the local one 
        global x2ProfilerApp
        try:
            if self.offline_mode.GetValue():
                x2ProfilerApp.repo = Repo(x2ProfilerApp.x2swProfilesPath)
            else:
                x2ProfilerApp.tmp_repo_path = tempfile.mkdtemp()
                x2ProfilerApp.repo = Repo.init(x2ProfilerApp.tmp_repo_path)
        except:
            pass

        if x2ProfilerApp.repo == None:
            event.Veto()
 

########################################################################
class DownloadingPage(wiz.PyWizardPage):
    """Wizard page for updating the profiles repo"""
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        global x2ProfilerApp

        wiz.PyWizardPage.__init__(self, parent)
        self.next = self.prev = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        title = wx.StaticText(self, label=title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sizer.Add(title)

        self.status =  wx.StaticText(self, -1, "Downloading from " + x2ProfilerApp.repo_url + "...")
        self.sizer.Add(self.status, 0, wx.ALL, 5)
        self.sizer.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5)
 
        self.count = 0
        self.gauge = wx.Gauge(self, -1, 100, size = (250, 25))
        self.sizer.Add(self.gauge)
        self.gauge.SetBezelFace(3)
        self.gauge.SetShadowWidth(3)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)

        self.lasttopic = None
        self.msgbuf = ''

    #----------------------------------------------------------------------
    def Run(self):
        global x2ProfilerApp
        self.Show()
        self.GetParent().Update()
        try:
            self.cmd_fetch(x2ProfilerApp.repo, x2ProfilerApp.repo_url)
            self.gauge.SetValue(100)
            self.status.SetLabel('Done fetching from ' + x2ProfilerApp.repo_url)
        except Exception as e:
            self.status.SetLabel('Failure to create temporary repository for:\n' + x2ProfilerApp.repo_url)
            self.gauge.SetValue(0)
            wx.MessageBox("Error:\n\n" + str(e), '', style = wx.OK|wx.ICON_EXCLAMATION)

    #----------------------------------------------------------------------
    def flush(self, msg=None):
        if self.lasttopic:
            self.status.SetLabel(self.lasttopic)
            self.gauge.SetValue(0)
        self.lasttopic = None
        if msg:
            self.status.SetLabel(msg)

    #----------------------------------------------------------------------
    # as it is done in hggit (not sure why it has to be so complex...)
    def progress(self, msg):
        # Counting objects: 3, done.
        # Compressing objects: 100% (3/3), done.
        # Total 3 (delta 0), reused 0 (delta 0)
        msgs = re.split('[\r\n]', self.msgbuf + msg)
        self.msgbuf = msgs.pop()
        for msg in msgs:
            ### for debugging ### print 'msg:' + msg + '\n'
            td = msg.split(':', 1)
            data = td.pop()
            if not td:
                self.flush(data)
                continue
            topic = td[0]
            m = re.search('\((\d+)/(\d+)\)', data)
            if m:
                if self.lasttopic and self.lasttopic != topic:
                    self.flush()
                self.lasttopic = topic
                pos, total = map(int, m.group(1, 2))
                try:
                    perc = int((pos * 100) / total)
                except:
                    perc = 0
                self.gauge.SetValue(perc)
            else:
                self.flush(msg)
        self.Show()
        self.GetParent().Update()

    #----------------------------------------------------------------------
    def cmd_fetch(self, r, url_path):
        c, path = get_transport_and_path(url_path)
        c._fetch_capabilities.remove('thin-pack')
        ### for debugging ### c = client.SubprocessGitClient(thin_packs=False)
        path = url_path
        determine_wants = r.object_store.determine_wants_all
        refs = c.fetch(path, r, progress=self.progress)
        for k in refs.keys():
           if k[-3:] == '^{}': # Annotated tag ref
               k = k[:-3]
           r[k] = refs[k]

    #----------------------------------------------------------------------
    def SetNext(self, next):
        self.next = next
 
    #----------------------------------------------------------------------
    def SetPrev(self, prev):
        self.prev = prev
 
    #----------------------------------------------------------------------
    def GetNext(self):
        return self.next
 
    #----------------------------------------------------------------------
    def GetPrev(self):
        return self.prev

########################################################################
class SelectProfilesPage(wiz.PyWizardPage):
    """Wizard page for selecting what profiles to deploy"""
    REF_TYPE_TAG = 1
    REF_TYPE_HEAD = 2
    REF_TYPE_RHEAD = 3
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        global x2ProfilerApp
        
        wiz.PyWizardPage.__init__(self, parent)
        self.next = self.prev = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        title = wx.StaticText(self, label=title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sizer.Add(title)
 
        self.under_title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.tree_title = wx.StaticText(self, -1, "Select the printer profile")
        self.under_title_sizer.Add(self.tree_title, 1, wx.ALL|wx.ALIGN_LEFT, 0)
        self.show_all = wx.CheckBox(self, wx.ID_ANY, 'Show All')
        self.show_all.Bind(wx.EVT_CHECKBOX, self.onCheckbox)
        self.all = False
        
        self.under_title_sizer.Add(self.show_all, 0, wx.ALL|wx.ALIGN_RIGHT, 0)
        self.sizer.Add(self.under_title_sizer, 0, wx.ALL|wx.EXPAND, 5)

        self.tree = wx.TreeCtrl(self, -1, style = wx.TR_HAS_BUTTONS|wx.TR_HAS_VARIABLE_ROW_HEIGHT)
        image_list = wx.ImageList(16, 16) 
        self.profile = image_list.Add(wx.Image("images/profile.png", wx.BITMAP_TYPE_PNG).ConvertToBitmap()) 
        self.profile_rb = image_list.Add(wx.Image("images/profile_rb.png", wx.BITMAP_TYPE_PNG).ConvertToBitmap()) 
        self.profile_lb = image_list.Add(wx.Image("images/profile_lb.png", wx.BITMAP_TYPE_PNG).ConvertToBitmap()) 
        self.folder = image_list.Add(wx.Image("images/folder.png", wx.BITMAP_TYPE_PNG).ConvertToBitmap()) 
        self.tree.AssignImageList(image_list) 
        self.sizer.Add(self.tree, 2, wx.EXPAND)

        self.sizer.Add(wx.StaticText(self, -1, "Selected profile description:"), 0, wx.ALL, 5)

        self.descript = wx.TextCtrl(self, -1, '', style = wx.TE_READONLY | wx.TE_MULTILINE)
        self.sizer.Add(self.descript, 1, wx.EXPAND)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)

        self.selection = None
        
    #----------------------------------------------------------------------
    def fillTree(self, refsList, path, node):
        for item_name,item_file,ref_type in refsList[path]:
            child_path = path + '/' + item_name
            if ref_type == self.REF_TYPE_TAG:
                child_ref_path = 'refs/tags' + child_path[4:]
                prof_image = self.profile
            elif ref_type == self.REF_TYPE_HEAD:
                child_ref_path = 'refs/heads' + child_path[4:]
                prof_image = self.profile_lb
            elif ref_type == self.REF_TYPE_RHEAD:
                child_ref_path = 'refs/remotes/origin' + child_path[4:]
                prof_image = self.profile_rb
            ### for debugging ### print child_ref_path
            child = self.tree.AppendItem(node, item_name)
            if item_file:
                child_ref_sha = self.refs[child_ref_path]
                self.tree.SetPyData(child, child_ref_sha)
                self.tree.SetItemImage(child, prof_image, wx.TreeItemIcon_Normal) 
            else:
                self.tree.SetItemImage(child, self.folder, wx.TreeItemIcon_Normal) 
            if refsList.has_key(child_path):
                self.fillTree(refsList, child_path, child)

    #----------------------------------------------------------------------
    def Run(self):
        # Prepare a tree-structured dictionary of refs paths
        global x2ProfilerApp
        self.repo = x2ProfilerApp.repo
        self.refs = self.repo.get_refs()
        refsList = {}
        # Make remote origin heads look similar to tags and local heads
        refkeys = ['refs/rheads'+item[19:] if item[:19]=='refs/remotes/origin' else item for item in self.refs.keys()]
        reflist = sorted(sorted(refkeys),key=lambda x: -len(x.split('/')))
        ### for debugging #### print reflist
        for ref in reflist:
            parts = ref.split('/')
            # We only use refs that have format refs/<tags|heads|rheads>/vX.X.X.X/<type>/...
            # Filter out one-level refs and anything that is neither tag or head
            if parts[0] != 'refs' or len(parts) <= 4:
                continue
            if parts[1] != 'tags' and parts[1] != 'heads' and parts[1] != 'rheads':
                continue
            # Is it a tag, a local branch head or remote branch head?
            ref_type = self.REF_TYPE_TAG
            if parts[1] == 'heads':
                ref_type = self.REF_TYPE_HEAD
            elif parts[1] == 'rheads':
                ref_type = self.REF_TYPE_RHEAD
            ver_prefix = parts[2]
            if not self.all and not ver_prefix.startswith('v' + x2ProfilerApp.ver_match_str):
                continue
            parts[1] = 'root'
            for ii in range(2, len(parts)):
                key = '/'.join(parts[1:ii])
                # see if already have the node path we are about to add
                if refsList.has_key(key + '/' + parts[ii]):
                    continue
                # build reference key
                # If at the end of the branch (i.e. the tag/head ref file name)
                file_ref = False
                if ii >= len(parts)-1: 
                    file_ref = True
                # Still going down the ref's path...
                # If we already started ading items to this subtree
                if refsList.has_key(key):
                    refsList[key].append([parts[ii],file_ref,ref_type])
                else:
                    refsList[key]=[[parts[ii],file_ref,ref_type]]
                ### for debugging ### print 'ii: '+ str(ii) +' ### key: ' + key + ' ### add: ' + parts[ii]
		
        # Build the UI tree (can do it above, but cleaner to separate)
        self.tree.DeleteAllItems()
        root_str = "FDM 3D Printer Profiles for X2SW"
        if self.all or len(x2ProfilerApp.ver[0]) == 0:
            root_str = root_str + " (all versions)"
        else:
            root_str = root_str + " v" + x2ProfilerApp.ver[0]
        root = self.tree.AddRoot(root_str)
        self.tree.SetItemImage(root, self.folder, wx.TreeItemIcon_Normal) 
        if refsList.has_key('root'):
            self.fillTree(refsList, 'root', root)

        self.tree.Expand(root)

        # On/off next button based on either a profile was selected or not
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)
        if self.selection != None:
            self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
        else:
            self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()

    #----------------------------------------------------------------------
    def OnSelChanged(self, event):
        global x2ProfilerApp
        self.selection = self.tree.GetPyData(event.GetItem())
        if self.selection != None:
            try:
                self.ShowDescription(self.selection)
                x2ProfilerApp.selection = self.selection
                self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
            except:
                x2ProfilerApp.selection = None
                self.descript.SetValue('')
                pass
        else:
            self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()
            x2ProfilerApp.selection = None
            self.descript.SetValue('')
        event.Skip()

    #----------------------------------------------------------------------
    def ShowDescription(self, ref):
        o = self.repo[ref]
        if o.type_name == 'tag':
            message = 'By: ' + o.tagger + '\n'
            #message += 'Type: annotated tag\n'
            message += o.message
        elif o.type_name == 'commit':
            message = 'By: ' + o.author + '\n'
            #message += 'Type: tagged commit\n'
            message += o.message
        self.descript.SetValue(message)

    #----------------------------------------------------------------------
    def onCheckbox(self, event):
        self.all = self.show_all.GetValue()
        self.Run()

    #----------------------------------------------------------------------
    def SetNext(self, next):
        self.next = next
 
    #----------------------------------------------------------------------
    def SetPrev(self, prev):
        self.prev = prev
 
    #----------------------------------------------------------------------
    def GetNext(self):
        return self.next
 
    #----------------------------------------------------------------------
    def GetPrev(self):
        return self.prev
 

########################################################################
class ChooseModePage(wiz.PyWizardPage):
    """Wizard page for managing in-place mode"""
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        wiz.PyWizardPage.__init__(self, parent)
        self.next = self.prev = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        title = wx.StaticText(self, label=title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sizer.Add(title)

        self.sel_box = wx.StaticText(self, -1, '\n\n')
        self.sizer.Add(self.sel_box, 0, wx.ALL, 5)
        self.sizer.Add(wx.StaticText(self, -1, "\
This page helps to control where the X2SW profile configuration files are stored.\n\
If the \"in-place\" mode is ON all the included software stores the config files\n\
locally under \".x2sw\" in X2SW installation folder. If it is OFF the files are\n\
stored under \".x2sw\" in the user home folder.\n\
\n\
The \"in-place\" mode is configured per user account and applies to all installed\n\
copies of the X2SW bundle. The deployment path for the mode chosen is shown above.\n\
\n\
If you want to change the \"in-place\" mode setting and skip the profile deployment\n\
step, cancel the wizard after choosing the desired mode."), 0, wx.ALL, 5)

        self.sizer.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5)

        self.inplace_mode = wx.CheckBox(self, wx.ID_ANY, 'Use In-Place mode')
        self.sizer.Add(self.inplace_mode)
        if os.path.exists(os.path.join(os.path.expanduser('~'), '.x2sw', '.use_local')):
            self.inplace_mode.SetValue(True)
        self.inplace_mode.Bind(wx.EVT_CHECKBOX, self.onCheckbox)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)
 
    #----------------------------------------------------------------------
    def UpdatePageUi(self):
        global x2ProfilerApp
        if self.selection != None:
            if not x2ProfilerApp.tmp_repo_path == None:
                paths_str = "\nFrom repository: " + x2ProfilerApp.repo_url + "\nDeployment path: " + x2ProfilerApp.x2swProfilesTgtPath
            else:
                paths_str = "\nFrom repository: " + x2ProfilerApp.x2swProfilesPath + ".git\nDeployment path: " + x2ProfilerApp.x2swProfilesTgtPath
            self.sel_box.SetLabel('Profile: ' + self.selection[10:] + paths_str)
        else:
            paths_str = "\nRepository path: none\nDeployment path: none"
            self.sel_box.SetLabel('Profile: ' + 'not selected' + paths_str)

    #----------------------------------------------------------------------
    def Run(self):
        global x2ProfilerApp
        self.selection = x2ProfilerApp.selection
        if self.selection == None:
            self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()
        else:
            self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
        self.UpdatePageUi()

    #----------------------------------------------------------------------
    def onCheckbox(self, event):
        global x2ProfilerApp

        inplace_path = os.path.join(os.path.expanduser('~'), '.x2sw')
        inplace_file = os.path.join(inplace_path, '.use_local')
        if not os.path.exists(inplace_path):
            os.mkdir(inplace_path)
        if self.inplace_mode.IsChecked():
            with file(inplace_file, 'a'): 
                pass
        else:
            os.remove(inplace_file)
        x2ProfilerApp.changes = True

        x2ProfilerApp.DetermineProfilesPaths()
        self.UpdatePageUi()

    #----------------------------------------------------------------------
    def SetNext(self, next):
        self.next = next
 
    #----------------------------------------------------------------------
    def SetPrev(self, prev):
        self.prev = prev
 
    #----------------------------------------------------------------------
    def GetNext(self):
        return self.next
 
    #----------------------------------------------------------------------
    def GetPrev(self):
        return self.prev

 
########################################################################
class DeployPage(wiz.PyWizardPage):
    """Wizard page confirming what where to deploy"""
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        wiz.PyWizardPage.__init__(self, parent)
        self.next = self.prev = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        title = wx.StaticText(self, label=title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sizer.Add(title)

        self.sel_box = wx.StaticText(self, -1, '\n\n')
        self.sizer.Add(self.sel_box, 0, wx.ALL, 5)
        self.sizer.Add(wx.StaticText(self, -1, "\
When you click \"Next\" the content of the X2SW profile selected will override\n\
the configuration files of the all X2SW software components under the \"Deployment\n\
path\". When ready confirm that you'd like to deploy and continue to the next page.\n\
\n\
WARNING: All the user files (if any) under the \"Deployment path\" will be lost!!!"), 0, wx.ALL, 5)

        self.sizer.Add(wx.StaticText(self, -1, ""), 0, wx.ALL, 5)

        self.deploy_profile = wx.CheckBox(self, wx.ID_ANY, 'Deploy profile')
        self.sizer.Add(self.deploy_profile)
        self.deploy_profile.Bind(wx.EVT_CHECKBOX, self.onCheckbox)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)

 
    #----------------------------------------------------------------------
    def UpdatePageUi(self):
        global x2ProfilerApp
        if self.selection != None:
            if not x2ProfilerApp.tmp_repo_path == None:
                paths_str = "\nFrom repository: " + x2ProfilerApp.repo_url + "\nDeployment path: " + x2ProfilerApp.x2swProfilesTgtPath
            else:
                paths_str = "\nFrom repository: " + x2ProfilerApp.x2swProfilesPath + ".git\nDeployment path: " + x2ProfilerApp.x2swProfilesTgtPath
            self.sel_box.SetLabel('Profile: ' + self.selection[10:] + paths_str)
        else:
            paths_str = "\nRepository path: none\nDeployment path: none"
            self.sel_box.SetLabel('Profile: ' + 'not selected' + paths_str)

    #----------------------------------------------------------------------
    def Run(self):
        global x2ProfilerApp
        self.selection = x2ProfilerApp.selection
        self.deploy_profile.SetValue(False)
        self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()
        if self.selection != None:
            self.deploy_profile.Enable()
        else:
            self.deploy_profile.Disable()
        self.UpdatePageUi()

    #----------------------------------------------------------------------
    def onCheckbox(self, event):
        if self.deploy_profile.IsChecked():
            self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
        else:
            self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()

    #----------------------------------------------------------------------
    def OnPageChanging(self, event):
        # Disable buttons as we moving forward 
        if event.GetDirection():
            self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()

    #----------------------------------------------------------------------
    def SetNext(self, next):
        self.next = next
 
    #----------------------------------------------------------------------
    def SetPrev(self, prev):
        self.prev = prev
 
    #----------------------------------------------------------------------
    def GetNext(self):
        return self.next
 
    #----------------------------------------------------------------------
    def GetPrev(self):
        return self.prev

 
########################################################################
class ReportResultPage(wiz.PyWizardPage):
    """Wizard page completing the deployment"""
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        wiz.PyWizardPage.__init__(self, parent)
        self.next = self.prev = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        title = wx.StaticText(self, label=title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sizer.Add(title)

        self.sel_box = wx.StaticText(self, -1, '\n\n')
        self.sizer.Add(self.sel_box, 0, wx.ALL, 5)
        self.status = wx.StaticText(self, -1, "Processing...") 
        self.sizer.Add(self.status, 0, wx.ALL, 5)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)

    #----------------------------------------------------------------------
    def afterRun(self):
        self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
 
    #----------------------------------------------------------------------
    def Run(self):
        self.status.SetLabel("Processing...")
        global x2ProfilerApp
        self.selection = x2ProfilerApp.selection
        if self.selection != None:
            if not x2ProfilerApp.tmp_repo_path == None:
                paths_str = "\nFrom repository: " + x2ProfilerApp.repo_url + "\nDeployment path: " + x2ProfilerApp.x2swProfilesTgtPath
            else:
                paths_str = "\nFrom repository: " + x2ProfilerApp.x2swProfilesPath + ".git\nDeployment path: " + x2ProfilerApp.x2swProfilesTgtPath
            self.sel_box.SetLabel('Profile: ' + self.selection[10:] + paths_str)
        else:
            paths_str = "\nRepository path: none\nDeployment path: none"
            self.sel_box.SetLabel('Profile: ' + 'not selected' + paths_str)
        self.Show()
        self.GetParent().Update()
        if not x2ProfilerApp.page5.deploy_profile.IsChecked():
            self.status.SetLabel("No changes performed, no profile selected!")
        else:
            try:
                self.DoDeploy(self.selection)
                self.status.SetLabel("The operation has completed successfully.")
            except Exception as e:
                self.status.SetLabel("\
The operation has failed! If using Windows in-place profile storage try to run\n\
the X2SW app in Windows XP(SP 2) compatibility mode or run it as Administrator.\n\
You can also cd to X2SW profiles folder and use GIT to check out the desired\n\
profile manually or attempt to diagnose and fix the issue.")
                wx.MessageBox("Error:\n\n" + str(e), '', style = wx.OK|wx.ICON_EXCLAMATION)
        x2ProfilerApp.changes = True
        self.Show()
        self.GetParent().Update()
        wx.CallAfter(self.afterRun)

    #----------------------------------------------------------------------
    def DoDeploy(self, ref):
        global x2ProfilerApp
        self.repo = x2ProfilerApp.repo
        self.refs = self.repo.get_refs()
        o = self.repo[ref]
        while o.type_name == 'tag':
            type_name, sha = o._get_object()
            o = self.repo.get_object(sha)
        if not o.type_name == 'commit':
            raise ValueError('Unable to find the tagged commit!')

        # We can only do a clean checkout, so clenaup
        self.RmAllProfiles(x2ProfilerApp.x2swProfilesPath)

        # Dulwich can't handle detached head, so use a temp branch as a workaround
        self.repo.refs.set_symbolic_ref('HEAD', 'refs/heads/temp')
        self.repo['HEAD'] = o.id
        build_index_from_tree(self.repo.path, self.repo.index_path(),
                              self.repo.object_store, o.tree)

        # Make the deployment folder (if not there) and checkout files into it
        if not os.path.isdir(x2ProfilerApp.x2swProfilesTgtPath):
            os.makedirs(x2ProfilerApp.x2swProfilesTgtPath)
        else:
            # Cleanup the deployment destination
            self.RmAllProfiles(x2ProfilerApp.x2swProfilesTgtPath)

        build_index_from_tree(x2ProfilerApp.x2swProfilesTgtPath, self.repo.index_path(),
                              self.repo.object_store, o.tree)

    #----------------------------------------------------------------------
    def RmAllProfiles(self, path):
        if not path.endswith('.x2sw'):
            raise ValueError('The path to RmAllProfiles() does not appear to be correct!')
        for root, dirs, files in os.walk(path):
            if root == path:
                if '.git' in dirs:
                    dirs.remove('.git')
                if '.git' in files:
                    files.remove('.git')
                if '.use_local' in files:
                    files.remove('.use_local')
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                shutil.rmtree(os.path.join(root, name))
                dirs.remove(name)

    #----------------------------------------------------------------------
    def SetNext(self, next):
        self.next = next
 
    #----------------------------------------------------------------------
    def SetPrev(self, prev):
        self.prev = prev
 
    #----------------------------------------------------------------------
    def GetNext(self):
        return self.next
 
    #----------------------------------------------------------------------
    def GetPrev(self):
        return self.prev
 

########################################################################
class X2ProfilerApp():
    """Main app class"""

    #----------------------------------------------------------------------
    def imagefile(self, filename):
        if os.path.exists(os.path.join(os.path.dirname(__file__), "images", filename)):
            return os.path.join(os.path.dirname(__file__), "images", filename)
        else:
            return os.path.join(os.path.split(os.path.split(__file__)[0])[0], "images", filename)

    #----------------------------------------------------------------------
    def DetermineProfilesPaths(self):
        self.x2swProfilesTgtPath = os.path.join(os.path.expanduser('~'), '.x2sw')
        if (os.path.exists(os.path.join(self.x2swProfilesTgtPath, '.use_local'))):
            self.x2swProfilesTgtPath = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), '.x2sw')
        self.x2swProfilesPath = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.x2swProfilesPath = os.path.join(self.x2swProfilesPath, '.x2sw')

    #----------------------------------------------------------------------
    def ReadOurVersion(self):
        versionfile = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), VERSION_FILE)
        if os.path.exists(versionfile):
            with open(versionfile) as f:
                self.ver = f.read().splitlines()
        else:
            self.ver = [ None ]
        # Match string (major.minor.) use: vrsion_str_tocheck.startswith(ver_match_str)
        self.ver_match_str = ""
        if self.ver[0]:
            ver = self.ver[0]
            ver = ver[:ver.find('.', ver.find('.') + 1) + 1]
            self.ver_match_str = ver
        else:
            self.ver = [ "" ]

    #----------------------------------------------------------------------
    def IsProfileCompatible(self):
        compat_file = os.path.join(self.x2swProfilesPath, COMPAT_FILE)
        we_are_compatible = False
        match_strs = []
        if os.path.exists(compat_file):
            with open(compat_file) as f:
                match_strs = f.read().splitlines()
        for match_str in match_strs:
            if self.ver[0] and self.ver[0].startswith(match_str):
                we_are_compatible = True
                break
        return we_are_compatible

    #----------------------------------------------------------------------
    def UpdateCompatFile(self):
        compat_file = os.path.join(self.x2swProfilesPath, COMPAT_FILE)
        we_are_compatible = False
        match_strs = []
        if os.path.exists(compat_file):
            with open(compat_file) as f:
                match_strs = f.read().splitlines()
        match_strs.append(self.ver_match_str)
        if os.path.exists(self.x2swProfilesPath):
            with open(compat_file, "w") as myfile:
                for line in match_strs:
                    myfile.write(line + "\n")
        return

    #----------------------------------------------------------------------
    def Run(self, onlyIfVersionCheckFails = False):
        global x2ProfilerApp
        x2ProfilerApp = self

        self.DetermineProfilesPaths()
        self.repo = None
        self.changes = False

        ### for debugging ### self.repo_url = 'D:\\tmp\\.x2sw'
        self.repo_url = 'https://github.com/dob71/x2sw_profiles.git'
        self.selection = None
        self.tmp_repo_path = None

        # Read our version (x2ProfilerApp.ver array contains strings from version.txt)
        self.ReadOurVersion()
        
        # If running for version check only, be done if have copatible profiles
        if onlyIfVersionCheckFails:
            if self.IsProfileCompatible():
                return
            else:
                msg = "The current profile is not compatible with X2SW v" + self.ver[0] + ". "\
                      "Would you like to run X2Profiler and download compatible set of profiles? "\
                      "\n\n"\
                      "Click [Cancel] to mark the currnet profile compatible and no loger display this message "\
                      "(dangerous, the app might no longer start). Click [No] to skip the update just for now. "\
                      "You'll be asked to update again next time app starts."\
                      "\n\n"\
                      "Profile path: " + self.x2swProfilesPath
                res = wx.MessageBox(msg, style = wx.YES_NO|wx.CANCEL|wx.YES_DEFAULT|wx.ICON_QUESTION)
                if res == wx.CANCEL:
                    self.UpdateCompatFile()
                    return
                elif res == wx.NO:
                    return

        image = wx.Image(self.imagefile("wiz.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.wizard = wiz.Wizard(None, -1, "X2 Profile Manager", image)
        self.page1 = UpdateRepoPage(self.wizard, "Update Profiles")
        self.page2 = DownloadingPage(self.wizard, "Downloading")
        self.page3 = SelectProfilesPage(self.wizard, "Select Profile")
        self.page4 = ChooseModePage(self.wizard, "Storage Mode")
        self.page5 = DeployPage(self.wizard, "Deploy Profile")
        self.page6 = ReportResultPage(self.wizard, "Deploying")

        # Set the initial order of the pages
        self.page1.SetNext(self.page2)
        self.page2.SetPrev(self.page1)
        self.page2.SetNext(self.page3)
        self.page3.SetPrev(self.page1) # Always skip downloading page on the way back
        self.page3.SetNext(self.page4)
        self.page4.SetPrev(self.page3)
        self.page4.SetNext(self.page5)
        self.page5.SetPrev(self.page4)
        self.page5.SetNext(self.page6)
        self.page6.SetPrev(self.page5)

        iconpath = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'x2.ico')
        if os.path.exists(iconpath):
            self.wizard.SetIcon(wx.Icon(iconpath,wx.BITMAP_TYPE_ICO))
        self.wizard.Bind(wiz.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)
        self.wizard.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)

        self.wizard.FitToPage(self.page1)
        self.wizard.GetPageAreaSizer().Add(self.page1)
        self.wizard.RunWizard(self.page1)
        self.wizard.Destroy()

        if not x2ProfilerApp.tmp_repo_path == None:
            try:
                shutil.rmtree(x2ProfilerApp.tmp_repo_path)
                x2ProfilerApp.tmp_repo_path = None
            except:
                pass

        return self.changes

    #----------------------------------------------------------------------
    def OnPageChanged(self, event):
        cp = self.wizard.GetCurrentPage()
        if hasattr(cp, 'Run'): 
            wx.CallAfter(cp.Run)

    #----------------------------------------------------------------------
    def OnPageChanging(self, event):
        pg = event.GetPage()
        if hasattr(pg, 'OnPageChanging'): 
            pg.OnPageChanging(event)


########################################################################
if __name__ == "__main__":
    app = wx.App(False)
    X2ProfilerApp().Run()

