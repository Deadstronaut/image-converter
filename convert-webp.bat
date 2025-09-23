@echo off
cd /d %~dp0

:: Node + Python kontrol
where node >nul 2>nul || (echo Node bulunamadı && pause && exit /b)
where python >nul 2>nul || (echo Python bulunamadı && pause && exit /b)

:: Kullanıcıdan prefix al
set /p PREFIX=Bucket prefix gir (Orn: elektronik/tablet/honor): 
set /p QUALITY=WebP kalite gir (1-100): 

if "%PREFIX%"=="" (
  echo Prefix bos olamaz!
  pause
  exit /b
)

:: Çalıştır
echo *** Basladi: %PREFIX% kalite=%QUALITY%
node scripts\convert-webp.mjs --prefix "%PREFIX%" --quality %QUALITY% --model rmbg20 --update-db
echo *** Tamamlandi: %PREFIX%
pause
