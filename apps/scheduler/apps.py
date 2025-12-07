from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scheduler'
    verbose_name = 'Планировщик'
    
    def ready(self):
        """Запускаем планировщик при старте Django"""
        # Импортируем здесь чтобы избежать circular imports
        from .scheduler import start_scheduler
        start_scheduler()
