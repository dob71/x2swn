#!/usr/bin/env python

# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

try:
    import wx  # NOQA
except:
    print("wxPython is not installed. This program requires wxPython to run.")
    if sys.version_info.major >= 3:
        print("""\
As you are currently running python3, this is most likely because wxPython is
not yet available for python3. You should try running with python2 instead.""")
        sys.exit(-1)
    else:
        raise

import sys
import os
import x2Profiler
import printrun.pronterface

if __name__ == '__main__':
    app = wx.App(False)

    # If starting the first time ever (no ~/.x2sw folder) run profiler, also
    # run it if the RC file is not in the selected storage location.
    rc_filename = ".pronsolerc"
    myPath = os.path.abspath(os.path.dirname(sys.argv[0]))
    x2swProfilesPath = os.path.join(os.path.expanduser('~'), '.x2sw')
    rcDistroFilename = os.path.join(myPath, '.x2sw', rc_filename)
    if(not os.path.exists(os.path.join(x2swProfilesPath, '.use_local'))):
            rcPathName = os.path.join(x2swProfilesPath, rc_filename)
    else:
            rcPathName = rcDistroFilename
    if os.path.exists(os.path.join(myPath, '.x2sw')) and \
       not os.path.exists(rcPathName):
        try:
            x2Profiler.X2ProfilerApp().Run()
        except:
            pass
    x2Profiler.X2ProfilerApp().Run(onlyIfVersionCheckFails = True)

    while(True):
        x2Profiler.pronterface_restart = False
        main = printrun.pronterface.PronterWindow(app)
        main.Show()
        try:
            app.MainLoop()
        except:
            pass
        if not x2Profiler.pronterface_restart:
            break
        elif hasattr(sys, 'frozen') and platform.system() is 'Linux':
            # reload() is not working under Linux binary, wrapper script
            # will do it there when sees exit code 22.
            exit(22)
        reload(printrun.pronterface)
