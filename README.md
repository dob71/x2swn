X2SW is a software bundle of Printrun, Skeinforge and Slic3r. 
It is currently used for X2 (RepRap Prusa Mendel with 2 extruders).

The purpose of this project is to provide for REPRAPpers an easy to use 
complete set of tools and deployable machine profiles that would 
allow to get a machine up and running right off-the-shelf.

The software packages and configuration profiles available here have some 
modifications to improve support for the dual extruding machines.

All the configuration files are deployed in the .x2sw folder in the root
of the bundle. You can choose either to work with the configuration 
files "in-place" (i.e. right where they are in the bundle) or deploy them 
into ".x2sw" folder under you user home directory. If you'd like to use the 
profiles in-place create "~/.x2sw" folder and then "~/.x2sw/.use_local" file 
using 'touch ~/.x2sw/.use_local' under Unix or 
'echo "" > %USERPROFILE%\.x2sw\.use_local` under Windows.

If you have existing profiles under .x2sw in your home folder and no 
".use_local" file the software will use your existing profiles. The 
new profiles are not going to be deployed (you can rename or remove 
your old profiles if interested in deploying the new ones).

The bundle is self-contained, configuration and/or profile files that 
unmodified versions of the software packages included in the bundle are 
not going to be affected (the unmodified versions of the software do 
not use .x2sw subfolder to store all the related profiles and rc files).

If you would like to run the included software packages from sources (rather 
that precompiled binaries), check the Printrun's readme file (README.printrun) 
for more information about the installation of the Python dependencies.
Look at the end of the slic3r/README.markdown for instructions on how to run 
slic3r from sources. You can ignore this information if using the binary 
package of the x2sw bundle.

