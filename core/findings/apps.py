from django.apps import AppConfig

class FindingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.findings'  # <--- CHANGE THIS (It probably says 'findings')