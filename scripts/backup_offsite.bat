@echo off
rem Copie les sauvegardes de la base vers un autre disque ou un partage reseau.
rem Modifiez DEST puis planifiez ce script (voir docs\Deploiement_FSS.md, section 5).
set SRC=C:\fss-portail\data\backups
set DEST=\\SERVEUR\partage\fss-backups
robocopy "%SRC%" "%DEST%" /E /XO /R:2 /W:5 /LOG+:C:\fss-portail\logs\backup_offsite.log
rem Les codes de retour robocopy 0 a 7 signifient "succes" (8 et plus = erreur).
if %ERRORLEVEL% GEQ 8 exit /b 1
exit /b 0
