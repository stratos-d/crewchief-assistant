@echo off
echo Building CrewChief Assistant...
echo.

poetry run pyinstaller CrewChiefAssistant.spec --clean

echo.
if exist "dist\CrewChiefAssistant.exe" (
    echo Build successful!
    echo Output: dist\CrewChiefAssistant.exe
) else (
    echo Build failed!
)

pause
