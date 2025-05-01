@REM For live update html.. cuz sphinx buildin makefile cannot have extra things

@REM Set the source and build directories
set "SOURCEDIR=."
set "BUILDDIR=_build"
set "PORT=0"
set "SPHINXAUTOBUILD=%~dp0../.venv/Scripts/sphinx-autobuild"

%SPHINXAUTOBUILD% %SOURCEDIR% %BUILDDIR% --port=%PORT% --host=0.0.0.0
