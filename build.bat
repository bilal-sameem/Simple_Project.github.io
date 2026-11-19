@echo off
call venv\Scripts\activate

set SAWANIH_SECRET_KEY=build-only-temporary-key

del Sawanih.spec
rmdir /s /q build
rmdir /s /q dist

python manage.py collectstatic --noinput

python -m PyInstaller launcher.py --name Sawanih --onedir ^
  --add-data "staticfiles;staticfiles" ^
  --add-data "sawanih/templates;sawanih/templates" ^
  --add-data "login/templates;login/templates" ^
  --collect-submodules sawanih --collect-submodules login ^
  --collect-all django --collect-all whitenoise ^
  --hidden-import waitress --hidden-import whitenoise.middleware

pause