@echo off
setlocal
set "URL=https://github.com/hershaleh/Chrome-extension-from-Zip/releases/download/latest/ZipExtensionLoader-Setup.exe"
set "INSTALLER=%TEMP%\ZipExtensionLoader-Setup.exe"

echo Downloading the latest ZIP Extension Loader installer...
curl.exe --fail --location --silent --show-error --retry 3 "%URL%" --output "%INSTALLER%"
if errorlevel 1 (
  echo Update download failed. Check your internet connection and try again.
  del "%INSTALLER%" >nul 2>&1
  exit /b 1
)

echo Installing update silently...
start /wait "" "%INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
set "RESULT=%ERRORLEVEL%"
del "%INSTALLER%" >nul 2>&1
if not "%RESULT%"=="0" (
  echo Installer returned exit code %RESULT%.
  exit /b %RESULT%
)
echo Update completed.
exit /b 0
