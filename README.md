X2SW is a software bundle of Printrun, Skeinforge and Slic3r where 
all three packages are tightly integrated and augmented with a 
set of profiles and tools for working with dual extruding machines
running X2 Mod of the Marlin firmware (https://github.com/dob71/Marlin/tree/m).
X2SW was designed to simplify the software and profiles deployment for 
RepRap X2 3D printers. It can as easily be used for any other kind of 
RepRap printers.

The software installer for MS Windows (XP, Vista, Win7) and binary packages 
for Linux are available. The Windows installer takes care of all the software 
setup from Arduino drivers to the software configuration profiles.

All the configuration files are deployed in the .x2sw folder in the root
of the bundle. You can choose either to work with the configuration 
files "in-place" (i.e. right where they are in the bundle) or deploy them 
into ".x2sw" folder under you user home directory. You can use the X2Profiler 
app integrated into Proterface to change where the configuration files are 
stored. X2Profiler starts automatically on the first Pronterface run after 
installing the X2SW bundle or can be started manually from under the "File" 
menu.

You can also change the location of the configuration manually. If you'd like 
to use the profiles "in-place" then create "~/.x2sw" folder and 
"~/.x2sw/.use_local" file using 'touch ~/.x2sw/.use_local' under Unix or 
'echo "" > %USERPROFILE%\.x2sw\.use_local` under Windows. 

The .x2sw folder is a standard GIT repository that can be used to store and 
retrieve various versions of your profiles as well as compare them and even  
push the profiles back for merging to the central online profiles repositoy.

The bundle is self-contained. The configuration and/or profile files for 
unmodified versions of the software packages (Printrun, Skeinforge, Slic3r) 
are not going to be affected (the unmodified versions of the software do 
not use .x2sw subfolder to store all the related profiles and rc files).

If you would like to run the included software packages from sources (rather 
than precompiled binaries), check the Printrun's readme file (README.printrun) 
for more information about the installation of the Python dependencies.
Look at the end of the slic3r/README.markdown for instructions on how to run 
Slic3r from sources. You can ignore this information if using the binary 
package of the x2sw bundle or the installer.

The modified versions of the software in the x2sw bundle can be found here:
X2SW: https://github.com/dob71/x2swn
Use it if interested in running from sources.
This repository uses "git subtree" to combine all the software components. 
The profiles repository is included as a GIT submodule (you'll need to pull
it after cloning if interested in having a local copy of this repository). 

The packager repository (builds the installer and binary packages):
https://github.com/dob71/x2sw_packager
(this repo uses "git submodules")

The profiles repository is here:
https://github.com/dob71/x2sw_profiles

The repositories of the individual packages as they are being prepared for 
bundling are here:
Skeinforge: https://github.com/dob71/sf
Slic3r: https://github.com/dob71/Slic3r
Printrun: https://github.com/dob71/Printrun.git

