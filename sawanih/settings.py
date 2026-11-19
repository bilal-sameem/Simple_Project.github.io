"""Sawanih settings: LAN server mode and packaged desktop app mode."""
import os
import sys
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FROZEN = getattr(sys, "frozen", False)   # True when running as the packaged .exe

# Writable per-user folder for the installed app. Development keeps using the project folder.
if FROZEN:
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Sawanih"
else:
    DATA_DIR = BASE_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = os.environ.get("SAWANIH_DEBUG") == "1"

SECRET_KEY = os.environ.get("SAWANIH_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-key-not-for-production"
    elif FROZEN:
        key_file = DATA_DIR / "secret.key"
        if not key_file.exists():
            key_file.write_text(secrets.token_urlsafe(50))
        SECRET_KEY = key_file.read_text().strip()
    else:
        raise RuntimeError(
            "SAWANIH_SECRET_KEY is not set. Put it in start_sawanih.bat: "
            "set SAWANIH_SECRET_KEY=your-generated-key"
        )

if FROZEN:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
else:
    ALLOWED_HOSTS = ["uoy", "192.168.1.51", "localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "login",
    "sawanih",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sawanih.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sawanih.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kabul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
PRIVATE_MEDIA_ROOT = DATA_DIR / "private_media"

LOGIN_URL = "login"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"