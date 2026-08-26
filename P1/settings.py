import os
import ssl
from pathlib import Path

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = '1@gmail.com'  
EMAIL_HOST_PASSWORD = 'ngxm bvjz ttjw gzgu'  

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret! (Strictly from Environment/Secrets)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# For Encryption (Strictly from Environment/Secrets)
SALT_KEY = os.environ.get('DJANGO_SALT_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Security Settings
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  
SESSION_COOKIE_AGE = 60 * 30  
SESSION_COOKIE_SECURE = True       
SESSION_COOKIE_HTTPONLY = True      
SESSION_COOKIE_SAMESITE = 'Strict'  
SESSION_SAVE_EVERY_REQUEST = True

ALLOWED_HOSTS = ['*']

# Cloudflare Tunnels aur External Proxies ke liye CSRF Trusted Origins Configuration
CSRF_TRUSTED_ORIGINS = [
    'https://*.trycloudflare.com',
    'http://*.trycloudflare.com',
    'https://*.loca.lt',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Cloudflare Reverse Proxy Headers Fix
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ceo_module',
    'django.contrib.humanize', 
    'app', 
    'dbbackup',  
    'import_export',  
    'axes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AXES_FAILURE_LIMIT = 5  
AXES_COOLOFF_TIME = 1  

ROOT_URLCONF = 'P1.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'P1.wsgi.application'

# Database Configuration (Environment Variables & Aiven MySQL Support)
db_host = os.environ.get("DB_HOST") or "mysql-2444d53b-moneymaster370-5b49.g.aivencloud.com"
db_user = os.environ.get("DB_USER") or "avnadmin"
db_pass = os.environ.get("DB_PASS") or os.environ.get("DB_PASSWORD") or ""
db_name = os.environ.get("DB_NAME") or "defaultdb"
db_port = int(os.environ.get("DB_PORT") or "12300")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': db_pass,
        'HOST': db_host,
        'PORT': db_port,
        'OPTIONS': {
            'ssl': {
                'check_hostname': False,
            },
            'connect_timeout': 30,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': BASE_DIR / 'dbbackup'}
DBBACKUP_HOSTNAME = 'geek'
DBBACKUP_TMP_FILE_MAX_SIZE = 100*1024*1024
DBBACKUP_CLEANUP_KEEP = 2
