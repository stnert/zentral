"""
Django settings for server project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import os
# Import the zentral settings (base.json)
from zentral.conf import settings as zentral_settings
from .celery import app as celery_app

__all__ = ('celery_app',)

django_zentral_settings = zentral_settings['django']

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = django_zentral_settings['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = django_zentral_settings.get('DEBUG', False)

ADMINS = ((admin_name, admin_email)
          for admin_name, admin_email in django_zentral_settings.get('ADMINS'))
DEFAULT_FROM_EMAIL = django_zentral_settings.get('DEFAULT_FROM_EMAIL', None)
SERVER_EMAIL = django_zentral_settings.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

ALLOWED_HOSTS = django_zentral_settings['ALLOWED_HOSTS']

MEDIA_ROOT = django_zentral_settings.get("MEDIA_ROOT", "")

if "CACHES" in django_zentral_settings:
    CACHES = django_zentral_settings["CACHES"]

# django default is 2.5MB. increased to 10MB.
DATA_UPLOAD_MAX_MEMORY_SIZE = django_zentral_settings.get('DATA_UPLOAD_MAX_MEMORY_SIZE', 10485760)

EMAIL_BACKEND = django_zentral_settings.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = django_zentral_settings.get("EMAIL_HOST", 'localhost')
EMAIL_PORT = django_zentral_settings.get("EMAIL_PORT", 25)
EMAIL_HOST_USER = django_zentral_settings.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = django_zentral_settings.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = django_zentral_settings.get("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = django_zentral_settings.get("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = django_zentral_settings.get("EMAIL_TIMEOUT")
EMAIL_SSL_KEYFILE = django_zentral_settings.get("EMAIL_SSL_KEYFILE")
EMAIL_SSL_CERTFILE = django_zentral_settings.get("EMAIL_SSL_CERTFILE")
EMAIL_FILE_PATH = django_zentral_settings.get("EMAIL_FILE_PATH")

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrapform',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'django_celery_results',
    'accounts',
    'base',
    'realms',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = django_zentral_settings.get("AUTH_PASSWORD_VALIDATORS", [])

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'realms.auth_backends.RealmBackend',
]

SESSION_COOKIE_SECURE = True

if "SESSION_COOKIE_AGE" in django_zentral_settings:
    SESSION_COOKIE_AGE = django_zentral_settings["SESSION_COOKIE_AGE"]

if "SESSION_EXPIRE_AT_BROWSER_CLOSE" in django_zentral_settings:
    SESSION_EXPIRE_AT_BROWSER_CLOSE = django_zentral_settings["SESSION_EXPIRE_AT_BROWSER_CLOSE"]

MAX_PASSWORD_AGE_DAYS = django_zentral_settings.get("MAX_PASSWORD_AGE_DAYS", None)

LOGIN_REDIRECT_URL = '/'

# add the zentral apps
for app_name in zentral_settings.get('apps', []):
    INSTALLED_APPS.append(app_name)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'base.middlewares.csp_middleware',
]

if MAX_PASSWORD_AGE_DAYS:
    MIDDLEWARE.insert(MIDDLEWARE.index("django.contrib.messages.middleware.MessageMiddleware") + 1,
                      "accounts.middleware.force_password_change_middleware")

ROOT_URLCONF = 'server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'zentral.conf.context_processors.extra_links',
                'zentral.conf.context_processors.probe_creation_links',
            ],
        },
    },
]

WSGI_APPLICATION = 'server.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'zentral'),
        'USER': os.environ.get('POSTGRES_USER', 'zentral'),
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': 3600
    }
}
for key in ('HOST', 'PASSWORD', 'PORT'):
    val = os.environ.get('POSTGRES_{}'.format(key))
    if val:
        DATABASES['default'][key] = val

CELERY_RESULT_BACKEND = 'django-db'
CELERY_BROKER_URL = django_zentral_settings.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = django_zentral_settings.get("LANGUAGE_CODE", "en-us")

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)
if DEBUG:
    STATIC_URL = '/static_debug/'
else:
    STATIC_URL = '/static/'
STATIC_ROOT = django_zentral_settings.get("STATIC_ROOT", "/zentral_static")
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"


# LOGGING
# everything in the console.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s PID%(process)d %(module)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
        },
        'py.warnings': {
            'handlers': ['console'],
        },
        'server': {
            'handlers': ['console'],
        },
        'zentral': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'elasticsearch': {
            'level': 'ERROR',
            'handlers': ['console'],
        }
    }
}
