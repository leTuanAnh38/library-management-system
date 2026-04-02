from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Mẹo: Django runserver thường chạy file này 2 lần (1 cho code, 1 cho reloader)
        # Kiểm tra điều kiện này để chắc chắn lịch chỉ được bật 1 lần
        if os.environ.get('RUN_MAIN', None) != 'true':
            from . import scheduler
            scheduler.start()