@echo off
rem Builds Egger Detector. Double-click it; the finished jar lands in the OUTPUT folder.
rem No delayed expansion: a "!" in the folder path would otherwise get lost.
setlocal DisableDelayedExpansion
rem pushd (not cd) also works when this folder is on a network share (\\server\share\...)
pushd "%~dp0"
if not exist "%~nx0" goto nofolder

rem --- the files a half-extracted zip (or an antivirus) would be missing
set "MISSING="
for %%F in (gradlew.bat build.gradle settings.gradle gradle.properties gradle\wrapper\gradle-wrapper.jar gradle\wrapper\gradle-wrapper.properties src\main\java\com\eggerdetector\Detector.java src\main\resources\fabric.mod.json) do if not exist "%%F" set "MISSING=%%F"
if defined MISSING goto missing

rem --- Java 25 or newer (Minecraft 26.1 itself runs on Java 25)
set "JAVA_EXE=java"
if defined JAVA_HOME set "JAVA_EXE=%JAVA_HOME:"=%\bin\java.exe"
set "JV_FILE=%TEMP%\eggerdetector-java-version.txt"
"%JAVA_EXE%" -version 2> "%JV_FILE%"
if errorlevel 1 goto nojava
set "JV="
set "JMAJOR="
rem the line with " version ", e.g.  openjdk version "25.0.1" 2025-10-21
for /f "tokens=3" %%v in ('findstr /c:" version " "%JV_FILE%"') do if not defined JV set "JV=%%~v"
del "%JV_FILE%" 2>nul
if defined JV for /f "delims=." %%m in ("%JV%") do set "JMAJOR=%%m"
rem could not read the version: let Gradle decide (it says clearly if Java is too old)
if not defined JMAJOR set "JMAJOR=99"
if %JMAJOR% LSS 25 goto oldjava
echo Using Java %JV%

rem clean first, so an older version's jar never ends up in OUTPUT next to the new one.
rem The Gradle wrapper is started directly: gradlew.bat breaks when the folder path contains "&".
"%JAVA_EXE%" -Xmx64m -Xms64m -Dorg.gradle.appname=gradlew -jar "%CD%\gradle\wrapper\gradle-wrapper.jar" clean build --no-daemon
if errorlevel 1 goto failed

if not exist OUTPUT mkdir OUTPUT
del /q "OUTPUT\eggerdetector-*.jar" 2>nul
set "BUILT="
for %%J in (build\libs\eggerdetector-*.jar) do call :copyjar "%%J" "%%~nxJ"
if not defined BUILT goto nojar
echo.
echo Done: OUTPUT\%BUILT%
echo Put it in your .minecraft\mods folder together with Fabric API (Mod Menu recommended for the settings button).
echo Cloth Config is already inside the jar.
popd
pause
exit /b 0

:copyjar
rem skip a -sources jar (the name changes when "-sources" is taken out of it)
set "NAME=%~2"
if not "%NAME:-sources=%"=="%NAME%" goto :eof
copy /y %1 OUTPUT\ >nul
set "BUILT=%NAME%"
goto :eof

:missing
echo Missing file: %MISSING%
echo Extract the WHOLE zip into a folder first, then run build.bat from there.
goto fail

:nofolder
echo Cannot open the folder this script is in.
pause
exit /b 1

:nojava
del "%JV_FILE%" 2>nul
if defined JAVA_HOME goto badjavahome
echo Java was not found. Install Java 25 (for example Eclipse Temurin 25 from adoptium.net) and run this again.
goto fail

:badjavahome
echo JAVA_HOME is set to "%JAVA_HOME:"=%" but there is no bin\java.exe in it.
echo Point JAVA_HOME at your Java 25 folder (the one that contains "bin"), or remove JAVA_HOME.
goto fail

:oldjava
echo Found Java %JV% - this build needs Java 25 or newer.
echo Install Java 25 (for example Eclipse Temurin 25 from adoptium.net). If you have it, set JAVA_HOME to its folder.
goto fail

:failed
echo.
echo BUILD FAILED - see the messages above.
goto fail

:nojar
echo The build finished but no jar was found in build\libs.
goto fail

:fail
popd
pause
exit /b 1
