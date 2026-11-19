@echo off
cd /d "%~dp0"
set SAWANIH_SECRET_KEY=aONXVO6zqqURegD-vOFBRfvcfOiogDAkFSUkIaUPglO19gscBJgbOfe5_z6YcpgHhOQ
call venv\Scripts\activate
python -m waitress --listen=0.0.0.0:8000 sawanih.wsgi:application
