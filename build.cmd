@echo off
rem Compila ClassicForever.exe con el compilador de C# que ya trae Windows (.NET Framework 4.8).
rem No hace falta instalar Visual Studio ni el SDK de .NET. Lo mismo corre en GitHub Actions.
setlocal
cd /d "%~dp0"
set "FW=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319"
if not exist "%FW%\csc.exe" ( echo No encuentro %FW%\csc.exe & exit /b 1 )
if not exist dist mkdir dist
"%FW%\csc.exe" /nologo /target:winexe /platform:x64 /optimize+ /codepage:65001 ^
  /out:dist\ClassicForever.exe /win32icon:src\app.ico /win32manifest:src\app.manifest ^
  /resource:src\MainWindow.xaml,ForeverLauncher.MainWindow.xaml ^
  /resource:src\img\panel.png,ForeverLauncher.img.panel.png ^
  /resource:src\img\logo.png,ForeverLauncher.img.logo.png ^
  /resource:src\img\close.png,ForeverLauncher.img.close.png ^
  /resource:src\img\play_es.png,ForeverLauncher.img.play_es.png ^
  /resource:src\img\play_en.png,ForeverLauncher.img.play_en.png ^
  /resource:src\img\update.png,ForeverLauncher.img.update.png ^
  /resource:src\img\nav_news.png,ForeverLauncher.img.nav_news.png ^
  /resource:src\img\nav_patch.png,ForeverLauncher.img.nav_patch.png ^
  /resource:src\img\nav_settings.png,ForeverLauncher.img.nav_settings.png ^
  /r:"%FW%\WPF\PresentationFramework.dll" /r:"%FW%\WPF\PresentationCore.dll" /r:"%FW%\WPF\WindowsBase.dll" ^
  /r:"%FW%\System.Xaml.dll" /r:"%FW%\System.Web.Extensions.dll" /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:"%FW%\System.IO.Compression.dll" /r:"%FW%\System.IO.Compression.FileSystem.dll" ^
  src\*.cs
if errorlevel 1 exit /b 1
echo OK: dist\ClassicForever.exe
