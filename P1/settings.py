import os
import ssl
from pathlib import Path

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = '1@gmail.com'  # Your Gmail Address
EMAIL_HOST_PASSWORD = 'ngxm bvjz ttjw gzgu'  # Your App Password (Not Gmail Password)

# For Encryption
SALT_KEY = '0123456789abcdefghijklmnopqrstuvwxyz'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-o9%6qc^k0v9!9+qw#l2r))!_@nri4^2ow8qt^n_n)x$_!g8_k#'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Security Settings
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  
SESSION_COOKIE_AGE = 60 * 30  
SESSION_COOKIE_SECURE = True       # HTTPS par session ko lazim banaen
SESSION_COOKIE_HTTPONLY = True      # JavaScript session ko access na kar sake
SESSION_COOKIE_SAMESITE = 'Strict'  # Cross-site attacks (CSRF) se bachao
SESSION_SAVE_EVERY_REQUEST = True

ALLOWED_HOSTS = ['*']
#ALLOWED_HOSTS = ['100.115.147.119','localhost']


INSTALLED_APPS = [
    #'admin_interface',
    #'colorfield',
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'django.contrib.humanize', # For Comma
    'app', # App
    'dbbackup',  # django-dbbackup
    'import_export',  # import_export
    'axes',
]

MIDDLEWARE = [
    'app.middleware.LicenseMiddleware',
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

AXES_FAILURE_LIMIT = 5  # 5 bar se zyada ghalat password par user block hoga
AXES_COOLOFF_TIME = 1  # 1 ghante baad dobara koshish ki ijazat hogi

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


# Database Configuration
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get("DB_NAME", "defaultdb"),
        'USER': os.environ.get("DB_USER", "avnadmin"),
        'PASSWORD': os.environ.get("DB_PASS", os.environ.get("DB_PASSWORD", "")),
        'HOST': os.environ.get("DB_HOST", "mysql-2444d53b-moneymaster370-5b49.g.aivencloud.com"),
        'PORT': os.environ.get("DB_PORT", "12300"),
        'OPTIONS': {
            'ssl': ssl_ctx,
            'connect_timeout': 30,
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
#LANGUAGE_CODE = 'ur' 

#TIME_ZONE = 'UTC'
TIME_ZONE = 'Asia/Karachi'

USE_I18N = True
USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': BASE_DIR / 'dbbackup'}
DBBACKUP_HOSTNAME = 'geek'
DBBACKUP_TMP_FILE_MAX_SIZE = 100*1024*1024
DBBACKUP_CLEANUP_KEEP = 2 # py manage.py dbbackup --clean
