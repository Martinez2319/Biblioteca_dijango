"""Configuración de Django para `biblioteca_virtual`.

Light refactor: se mantiene la estructura original, se añaden constantes SEO,
context processor global y se lee PAYPAL_CURRENCY desde el entorno.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Seguridad y entorno
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get('JWT_SECRET', 'django-insecure-key')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['*']

# Detrás del proxy (k8s ingress + proxy de /app/frontend/proxy.js) usamos los
# headers X-Forwarded-* para construir URLs absolutas con el host/esquema
# real. Sin esto, canonical/og:url apuntarían al upstream interno.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# Apps y middleware
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'corsheaders',
    'rest_framework',
    'core',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'api.middleware.JWTAuthMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Procesador propio: inyecta SITE_NAME, SITE_URL y config PayPal
                'core.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# Base de datos (SQLite solo para sesiones / Django admin;
# el dominio real vive en MongoDB via api.db)
# ---------------------------------------------------------------------------
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'biblioteca_virtual')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# CORS / DRF
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
}

# ---------------------------------------------------------------------------
# Integraciones externas (PayPal, email, JWT)
# ---------------------------------------------------------------------------
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET', '')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
PAYPAL_CURRENCY = os.environ.get('PAYPAL_CURRENCY', 'USD')
REMOTE_API_KEY = os.environ.get('REMOTE_API_KEY', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'secret')
JWT_EXPIRY_HOURS = 24

# Email Settings (Gmail SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')

# ---------------------------------------------------------------------------
# SEO
# ---------------------------------------------------------------------------
# URL pública del sitio (usada para canonical/sitemap/og:url). Puede quedar
# vacía: cuando la petición llega con host real, usamos request.build_absolute_uri.
SITE_URL = os.environ.get('SITE_URL', '').rstrip('/')
SITE_NAME = os.environ.get('SITE_NAME', 'Biblioteca Virtual')
DEFAULT_META_DESCRIPTION = os.environ.get(
    'DEFAULT_META_DESCRIPTION',
    'Biblioteca Virtual: lee libros digitales gratis y premium en cualquier '
    'dispositivo. Descubre ficción, ciencia, historia, autoayuda y más.'
)
DEFAULT_META_IMAGE = os.environ.get(
    'DEFAULT_META_IMAGE',
    '/static/img/og-default.jpg'
)
