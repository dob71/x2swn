set PYTHON_PATH=C:\Python27
set PERL_PATH=D:\CitrusPerl\bin
set PATH=%PYTHON_PATH%;%PATH%
call %PERL_PATH%\citrusvars.bat
python pronterface.py
