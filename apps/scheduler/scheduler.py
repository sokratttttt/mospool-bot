"""
Scheduler - планировщик задач на APScheduler.
Бесплатная альтернатива Celery + Redis.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Глобальный планировщик
_scheduler: Optional[BackgroundScheduler] = None
_is_started = False


def get_scheduler() -> BackgroundScheduler:
    """Получить или создать планировщик"""
    global _scheduler
    
    if _scheduler is None:
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(10)
        }
        job_defaults = {
            'coalesce': True,  # Объединять пропущенные запуски
            'max_instances': 1,  # Не запускать параллельно одну и ту же задачу
            'misfire_grace_time': 60 * 5  # 5 минут на выполнение пропущенной задачи
        }
        
        _scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Europe/Moscow'
        )
    
    return _scheduler


def start_scheduler():
    """Запустить планировщик"""
    global _is_started
    
    if _is_started:
        return
    
    scheduler = get_scheduler()
    
    # Добавляем основные задачи
    
    # Проверка запланированных постов каждую минуту
    scheduler.add_job(
        check_scheduled_posts,
        CronTrigger(minute='*'),
        id='check_scheduled_posts',
        name='Проверка запланированных постов',
        replace_existing=True
    )
    
    # Очистка старых логов раз в день
    scheduler.add_job(
        cleanup_old_publications,
        CronTrigger(hour=3, minute=0),  # 3:00 AM
        id='cleanup_old_publications',
        name='Очистка старых публикаций',
        replace_existing=True
    )
    
    # Проверка здоровья API каждые 6 часов
    scheduler.add_job(
        check_api_health,
        CronTrigger(hour='*/6'),
        id='check_api_health',
        name='Проверка API',
        replace_existing=True
    )
    
    try:
        scheduler.start()
        _is_started = True
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


def stop_scheduler():
    """Остановить планировщик"""
    global _is_started
    
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        _is_started = False
        logger.info("Scheduler stopped")


def schedule_post(post, publish_time: datetime) -> str:
    """
    Запланировать публикацию поста.
    
    Args:
        post: Post instance
        publish_time: Время публикации
        
    Returns:
        Job ID
    """
    scheduler = get_scheduler()
    
    job_id = f"publish_post_{post.id}"
    
    scheduler.add_job(
        publish_single_post,
        DateTrigger(run_date=publish_time),
        args=[post.id],
        id=job_id,
        name=f'Публикация: {post.title}',
        replace_existing=True
    )
    
    logger.info(f"Scheduled post {post.id} for {publish_time}")
    return job_id


def cancel_scheduled_post(post) -> bool:
    """
    Отменить запланированную публикацию.
    
    Args:
        post: Post instance
        
    Returns:
        True если задача была отменена
    """
    scheduler = get_scheduler()
    job_id = f"publish_post_{post.id}"
    
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Cancelled scheduled post {post.id}")
        return True
    except Exception:
        return False


# =============================================================================
# Scheduled Tasks
# =============================================================================

def check_scheduled_posts():
    """
    Проверяет и публикует запланированные посты.
    Запускается каждую минуту.
    """
    try:
        import django
        django.setup()
    except:
        pass
    
    try:
        from apps.posts.models import Post
        from django.utils import timezone
        
        now = timezone.now()
        
        # Получаем посты которые пора публиковать
        posts = Post.objects.filter(
            status='scheduled',
            scheduled_time__lte=now
        )
        
        for post in posts:
            try:
                publish_single_post(post.id)
            except Exception as e:
                logger.error(f"Failed to publish post {post.id}: {e}")
                post.status = 'failed'
                post.save()
                
    except Exception as e:
        logger.error(f"check_scheduled_posts error: {e}")


def publish_single_post(post_id: int):
    """
    Публикация одного поста.
    
    Args:
        post_id: ID поста
    """
    try:
        import django
        django.setup()
    except:
        pass
    
    try:
        from apps.posts.models import Post
        from apps.publishers.manager import publish_post
        
        post = Post.objects.get(id=post_id)
        
        if post.status not in ('approved', 'scheduled'):
            logger.warning(f"Post {post_id} is not approved/scheduled, skipping")
            return
        
        post.status = 'publishing'
        post.save()
        
        results = publish_post(post)
        
        success_count = sum(1 for r in results if r.get('success'))
        logger.info(f"Published post {post_id}: {success_count}/{len(results)} platforms succeeded")
        
    except Exception as e:
        logger.error(f"publish_single_post error for {post_id}: {e}")
        try:
            from apps.posts.models import Post
            post = Post.objects.get(id=post_id)
            post.status = 'failed'
            post.save()
        except:
            pass


def cleanup_old_publications(days: int = 90):
    """
    Удаление старых записей о публикациях.
    
    Args:
        days: Возраст записей для удаления
    """
    try:
        import django
        django.setup()
    except:
        pass
    
    try:
        from apps.posts.models import Publication
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        deleted, _ = Publication.objects.filter(
            published_at__lt=cutoff_date
        ).delete()
        
        if deleted:
            logger.info(f"Cleaned up {deleted} old publication records")
            
    except Exception as e:
        logger.error(f"cleanup_old_publications error: {e}")


def check_api_health():
    """
    Проверка доступности API платформ.
    """
    try:
        import django
        django.setup()
    except:
        pass
    
    try:
        from apps.publishers.manager import PublisherManager
        
        manager = PublisherManager.from_database()
        results = manager.test_all_connections()
        
        for platform, is_healthy in results.items():
            if is_healthy:
                logger.info(f"API health check: {platform} OK")
            else:
                logger.warning(f"API health check: {platform} FAILED")
                # TODO: Отправить уведомление админу
                
    except Exception as e:
        logger.error(f"check_api_health error: {e}")


def get_scheduler_status() -> dict:
    """
    Получить статус планировщика.
    
    Returns:
        Dict со статусом и списком задач
    """
    scheduler = get_scheduler()
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
        })
    
    return {
        'running': scheduler.running,
        'job_count': len(jobs),
        'jobs': jobs
    }
