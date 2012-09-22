#!/usr/bin/env python

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
        except:
            self.status.SetLabel('Failure to create temporary repository for:\n' + x2ProfilerApp.repo_url)
            self.gauge.SetValue(0)

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
            print 'msg:' + msg + '\n'
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
 
    #----------------------------------------------------------------------
    def __init__(self, parent, title):
        wiz.PyWizardPage.__init__(self, parent)
        self.next = self.prev = None
        self.sizer = wx.BoxSizer(wx.VERTICAL)
 
        title = wx.StaticText(self, label=title)
        title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.sizer.Add(title)
 
        self.sizer.Add(wx.StaticText(self, -1, "Select the printer profile (no changes are made at this step)"), 0, wx.ALL, 5)

        self.tree = wx.TreeCtrl(self, -1, style = wx.TR_HAS_BUTTONS|wx.TR_HAS_VARIABLE_ROW_HEIGHT)
        image_list = wx.ImageList(16, 16) 
        self.profile = image_list.Add(wx.Image("images/profile.png", wx.BITMAP_TYPE_PNG).ConvertToBitmap()) 
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
    def fillTree(self, tagsList, path, node):
        for item_name,item_file in tagsList[path]:
            child_path = path + '/' + item_name
            ref = None
            child = self.tree.AppendItem(node, item_name)
            if item_file:
                self.tree.SetPyData(child, 'refs/' + child_path)
                self.tree.SetItemImage(child, self.profile, wx.TreeItemIcon_Normal) 
            else:
                self.tree.SetItemImage(child, self.folder, wx.TreeItemIcon_Normal) 
            if tagsList.has_key(child_path):
                self.fillTree(tagsList, child_path, child)
 
    #----------------------------------------------------------------------
    def Run(self):
        # Prepare a tree-structured dictionary of refs paths
        global x2ProfilerApp
        self.repo = x2ProfilerApp.repo
        self.refs = self.repo.get_refs()
        tagsList = {}
        reflist = sorted(sorted(self.refs.keys()),key=lambda x: -len(x.split('/')))
        for ref in reflist:
            parts = ref.split('/')
            if parts[0] != 'refs' or parts[1] != 'tags' or len(parts) <= 2:
                continue
            for ii in range(2, len(parts)):
                key = '/'.join(parts[1:ii])
                # see if already have the node path we are about to add
                if tagsList.has_key(key + '/' + parts[ii]):
                    continue
                # If at the end of the branch (i.e. the real tag file name)
                tag_file = False
                if ii >= len(parts)-1: 
                    tag_file = True
                # Still going down the ref's path...
                # If we already started ading items to this subtree
                if tagsList.has_key(key):
                    tagsList[key].append([parts[ii],tag_file])
                else:
                    tagsList[key]=[[parts[ii],tag_file]]
                #print 'ii: '+ str(ii) +'### key: ' + key + ' ### add: ' + parts[ii]
        
        # Build the UI tree (can do it above, but cleaner to separate)
        self.tree.DeleteAllItems()
        root = self.tree.AddRoot("FDM 3D Printers")
        self.tree.SetItemImage(root, self.folder, wx.TreeItemIcon_Normal) 
        if tagsList.has_key('tags'):
            self.fillTree(tagsList, 'tags', root)
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
        #self.GetParent().FindWindowById(wx.ID_FORWARD).Disable()
        self.Show()
        self.GetParent().Update()
        if not x2ProfilerApp.page5.deploy_profile.IsChecked():
            self.status.SetLabel("No changes performed, no profile selected!")
        else:
            try:
                self.DoDeploy(self.selection)
                self.status.SetLabel("The operation has completed successfully.")

            except:
                self.status.SetLabel("\
The operation has failed! Please examine the X2SW profiles folder and\n\
use GIT to manually checkout the desired profile or fix the repository.")
        #self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()

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
    def Run(self):
        global x2ProfilerApp
        x2ProfilerApp = self

        self.DetermineProfilesPaths()
        self.repo = None

        ### for debugging ### self.repo_url = 'D:\\tmp\\.x2sw'
        self.repo_url = 'http://github.com/dob71/x2sw_profiles.git'
        self.selection = None
        self.tmp_repo_path = None

        image = wx.Image(self.imagefile("wiz.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.wizard = wiz.Wizard(None, -1, "X2 Profile Manager", image)
        self.page1 = UpdateRepoPage(self.wizard, "Update Profiles")
        self.page2 = DownloadingPage(self.wizard, "Downloading")
        self.page3 = SelectProfilesPage(self.wizard, "Select Profile")
        self.page4 = ChooseModePage(self.wizard, "Storage Mode")
        self.page5 = DeployPage(self.wizard, "Deploy Profile")
        self.page6 = ReportResultPage(self.wizard, "Completed")

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

        return True

    #----------------------------------------------------------------------
    def OnPageChanged(self, event):
        cp = self.wizard.GetCurrentPage()
        if hasattr(cp, 'Run'): 
            cp.Run()

    #----------------------------------------------------------------------
    def OnPageChanging(self, event):
        pg = event.GetPage()
        if hasattr(pg, 'OnPageChanging'): 
            pg.OnPageChanging(event)


########################################################################
if __name__ == "__main__":
    app = wx.App(False)
    X2ProfilerApp().Run()

