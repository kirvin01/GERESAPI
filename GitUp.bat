@echo off
REM Fecha y hora
for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "$culture = [System.Globalization.CultureInfo]::GetCultureInfo('es-ES'); (Get-Date).ToString('ddd, dd-MM-yyyy HH:mm', $culture)"`) do set fecha_hora=%%a

set commitmsg=Actualizacion %fecha_hora%

REM Subir cambios en todos los submódulos
git submodule foreach "git add . && git commit -m \"%commitmsg%\" && git push || echo Sin cambios en el submodulo"

REM Subir cambios en el proyecto principal
git add .
git commit -m "%commitmsg%"
git push origin master

echo.
echo ✅ Actualización enviada a GitHub con mensaje: %commitmsg%
pause

