X2 Software Bundle
==================

X2SW is a software bundle of Printrun, Skeinforge and Slic3r where 
all the three packages are tightly integrated and can be easily deployed 
and configured. The configuration for specific printer (if available in the 
profiles repository) can be retrieved using x2Profiler app (integrated with 
the Printrun UI version included in the bundle).

The software installer for MS Windows (XP, Vista, Win7...) and binary packages 
for Linux are available. The Windows installer takes care of all the software 
setup from Arduino drivers to the software configuration profiles. Note that
if you select the Arduino drivers to install, for each driver Windows will show
warning about it not being signed (choose to install anyway when the warning 
pops up).

All the configuration profiles that come with the bundle are stored in the 
local GIT repository under .x2sw folder in the root of the bundle. The 
x2Profiler app helps to select the specifc profile for your printer (either
from the local or online repositiry), choose the profile target location and 
deploy it. x2Profiler starts automatically on the first Pronterface run after 
installing the X2SW bundle (if installing the first time) or can be 
started manually from under the "File" menu. 

When choosing the profile deployment location note that the chosen setting 
is shared by all the installations of the x2sw bundle for the user account. You
can choose either to work with the configuration files "in-place" (i.e. right 
where they are in the bundle) or deploy them into ".x2sw" folder under your 
user home directory. If you deploy to the user home, all your X2SW copies will 
share the same configuration files, otherwise each will use its own local set. 

The .x2sw folder in the root of the bundle is a standard GIT repository.
It can be used to store and retrieve various versions of your profiles 
manually using GIT as well as compare them and pull back to the online  
repository for sharing with other X2SW software bundle users.

The bundle is self-contained. The configuration files for the unmodified 
versions of the included software (Printrun, Skeinforge, Slic3r) are not 
affected since those files are stored in different locations.

Running from Sources
====================

If you would like to run the included software packages from sources (rather 
than precompiled binaries), check the Printrun readme file (README.printrun) 
for more information about the installation of the Python dependencies and 
look at the end of the slic3r/README.markdown for instructions on how to run 
Slic3r from sources. You can ignore this and the following information if using 
the binary package or the installer.

For running the x2Profiler from sources install Dulwich v0.8.5 or later: 
http://www.samba.org/~jelmer/dulwich/
Install by running: <path_to_python>/python setup.py --pure install

The X2SW source repository that can be used for running from sources is here:
https://github.com/dob71/x2swn
This repository uses "git subtree" to combine all the software components. 
The profiles repository is included as a GIT submodule (clone recursively
if interested in having a local copy of this repository). Alternatively 
you can use x2Profiler UI to retrieve a suitable profile for your printer 
directly from the online repository.

For Developers
==============

The packager repository (builds the installer and binary packages) is here:
https://github.com/dob71/x2sw_packager
(this repo uses "git submodules")

The profiles repository is here:
https://github.com/dob71/x2sw_profiles

The repositories of the individual packages as they are being prepared for 
bundling are here:
Skeinforge: https://github.com/dob71/sf
Slic3r: https://github.com/dob71/Slic3r
Printrun: https://github.com/dob71/Printrun.git

