; TrackerX Installer Script for NSIS
; This script creates a professional Windows installer for TrackerX

; Include Modern UI
!include "MUI2.nsh"

; General Settings
Name "TrackerX"
OutFile "dist\TrackerX-Setup.exe"
InstallDir "$PROGRAMFILES\TrackerX"
InstallDirRegKey HKCU "Software\TrackerX" "Install_Dir"
RequestExecutionLevel user

; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Installer Sections
Section "Install"
  SetOutPath "$INSTDIR"
  
  ; Copy application files from dist\TrackerX
  File /r "dist\TrackerX\*.*"
  
  ; Create Start Menu shortcuts
  CreateDirectory "$SMPROGRAMS\TrackerX"
  CreateShortCut "$SMPROGRAMS\TrackerX\TrackerX.lnk" "$INSTDIR\TrackerX.exe" "" "$INSTDIR\TrackerX.exe" 0
  CreateShortCut "$SMPROGRAMS\TrackerX\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  
  ; Create Desktop shortcut
  CreateShortCut "$DESKTOP\TrackerX.lnk" "$INSTDIR\TrackerX.exe" "" "$INSTDIR\TrackerX.exe" 0
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Write registry keys for uninstall
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrackerX" "DisplayName" "TrackerX"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrackerX" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrackerX" "DisplayVersion" "0.1.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrackerX" "Publisher" "TrackerX"
  
  ; Store installation folder
  WriteRegStr HKCU "Software\TrackerX" "Install_Dir" "$INSTDIR"
SectionEnd

; Uninstaller Section
Section "Uninstall"
  ; Remove Start Menu shortcuts
  RMDir /r "$SMPROGRAMS\TrackerX"
  
  ; Remove Desktop shortcut
  Delete "$DESKTOP\TrackerX.lnk"
  
  ; Remove application files
  RMDir /r "$INSTDIR"
  
  ; Remove registry keys
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TrackerX"
  DeleteRegKey HKCU "Software\TrackerX"
SectionEnd
