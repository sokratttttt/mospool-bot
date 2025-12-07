"""
Views for Posts app - веб-интерфейс управления постами.
"""
import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.db.models import Count, Q

from .models import Post, Platform, PostCategory, PostTemplate, Publication, ProjectData, ScheduleSlot
from .services.content_generator import ContentGenerator


def dashboard(request):
    """Главная страница - дашборд"""
    # Статистика
    total_posts = Post.objects.count()
    published_posts = Post.objects.filter(status='published').count()
    scheduled_posts = Post.objects.filter(status='scheduled').count()
    failed_posts = Post.objects.filter(status='failed').count()
    
    # Последние публикации
    recent_publications = Publication.objects.select_related(
        'post', 'platform'
    ).order_by('-published_at')[:10]
    
    # Запланированные посты
    upcoming_posts = Post.objects.filter(
        status='scheduled',
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time')[:5]
    
    # Посты на модерации
    pending_posts = Post.objects.filter(status='pending').order_by('-created_at')[:5]
    
    # Активные платформы
    platforms = Platform.objects.filter(is_active=True)
    
    # Статистика по дням (последние 7 дней)
    week_ago = timezone.now() - timedelta(days=7)
    daily_stats = []
    for i in range(7):
        day = timezone.now() - timedelta(days=i)
        count = Publication.objects.filter(
            published_at__date=day.date(),
            status='success'
        ).count()
        daily_stats.append({
            'date': day.strftime('%d.%m'),
            'count': count
        })
    daily_stats.reverse()
    
    context = {
        'total_posts': total_posts,
        'published_posts': published_posts,
        'scheduled_posts': scheduled_posts,
        'failed_posts': failed_posts,
        'recent_publications': recent_publications,
        'upcoming_posts': upcoming_posts,
        'pending_posts': pending_posts,
        'platforms': platforms,
        'daily_stats': json.dumps(daily_stats),
    }
    
    return render(request, 'posts/dashboard.html', context)


def post_list(request):
    """Список всех постов"""
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    
    posts = Post.objects.select_related('category').prefetch_related('platforms')
    
    if status_filter:
        posts = posts.filter(status=status_filter)
    if category_filter:
        posts = posts.filter(category__slug=category_filter)
    
    posts = posts.order_by('-created_at')
    
    categories = PostCategory.objects.all()
    
    context = {
        'posts': posts,
        'categories': categories,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'status_choices': Post.STATUS_CHOICES,
    }
    
    return render(request, 'posts/post_list.html', context)


def post_create(request):
    """Создание нового поста"""
    if request.method == 'POST':
        title = request.POST.get('title', '')
        content = request.POST.get('content', '')
        category_id = request.POST.get('category')
        platform_ids = request.POST.getlist('platforms')
        scheduled_time = request.POST.get('scheduled_time')
        status = request.POST.get('status', 'draft')
        
        # Создаём пост
        post = Post.objects.create(
            title=title,
            content=content,
            category_id=category_id if category_id else None,
            status=status,
            created_by=request.user if request.user.is_authenticated else None,
        )
        
        # Добавляем платформы
        if platform_ids:
            post.platforms.set(platform_ids)
        
        # Устанавливаем время публикации
        if scheduled_time:
            post.scheduled_time = datetime.fromisoformat(scheduled_time)
            if status == 'approved':
                post.status = 'scheduled'
            post.save()
        
        # Загружаем изображение
        if 'image' in request.FILES:
            post.image = request.FILES['image']
            post.save()
        
        messages.success(request, f'Пост "{post.title}" успешно создан!')
        return redirect('post_detail', post_id=post.id)
    
    # GET - форма создания
    categories = PostCategory.objects.all()
    platforms = Platform.objects.filter(is_active=True)
    templates = PostTemplate.objects.filter(is_active=True)
    
    context = {
        'categories': categories,
        'platforms': platforms,
        'templates': templates,
    }
    
    return render(request, 'posts/post_create.html', context)


def post_detail(request, post_id):
    """Детальная страница поста"""
    post = get_object_or_404(Post, id=post_id)
    publications = post.publications.select_related('platform').order_by('-published_at')
    
    context = {
        'post': post,
        'publications': publications,
    }
    
    return render(request, 'posts/post_detail.html', context)


def post_edit(request, post_id):
    """Редактирование поста"""
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        post.title = request.POST.get('title', post.title)
        post.content = request.POST.get('content', post.content)
        post.content_telegram = request.POST.get('content_telegram', '')
        post.content_vk = request.POST.get('content_vk', '')
        
        category_id = request.POST.get('category')
        if category_id:
            post.category_id = category_id
        
        platform_ids = request.POST.getlist('platforms')
        if platform_ids:
            post.platforms.set(platform_ids)
        
        scheduled_time = request.POST.get('scheduled_time')
        if scheduled_time:
            post.scheduled_time = datetime.fromisoformat(scheduled_time)
        
        if 'image' in request.FILES:
            post.image = request.FILES['image']
        
        post.save()
        messages.success(request, 'Пост успешно обновлён!')
        return redirect('post_detail', post_id=post.id)
    
    categories = PostCategory.objects.all()
    platforms = Platform.objects.filter(is_active=True)
    
    context = {
        'post': post,
        'categories': categories,
        'platforms': platforms,
    }
    
    return render(request, 'posts/post_edit.html', context)


@require_POST
def post_publish(request, post_id):
    """Немедленная публикация поста"""
    post = get_object_or_404(Post, id=post_id)
    
    if not post.platforms.exists():
        messages.error(request, 'Выберите платформы для публикации!')
        return redirect('post_detail', post_id=post.id)
    
    # Публикуем
    from apps.publishers.manager import publish_post
    results = publish_post(post)
    
    success_count = sum(1 for r in results if r.get('success'))
    total_count = len(results)
    
    if success_count == total_count:
        messages.success(request, f'Пост опубликован на {success_count} платформах!')
    elif success_count > 0:
        messages.warning(request, f'Пост опубликован на {success_count} из {total_count} платформ')
    else:
        messages.error(request, 'Не удалось опубликовать пост')
    
    return redirect('post_detail', post_id=post.id)


@require_POST
def post_approve(request, post_id):
    """Одобрение поста"""
    post = get_object_or_404(Post, id=post_id)
    
    if post.scheduled_time and post.scheduled_time > timezone.now():
        post.status = 'scheduled'
    else:
        post.status = 'approved'
    
    post.save()
    messages.success(request, 'Пост одобрен!')
    return redirect('post_detail', post_id=post.id)


@require_POST
def post_delete(request, post_id):
    """Удаление поста"""
    post = get_object_or_404(Post, id=post_id)
    title = post.title
    post.delete()
    messages.success(request, f'Пост "{title}" удалён')
    return redirect('post_list')


def generate_content(request):
    """Страница генерации контента с ИИ"""
    if request.method == 'POST':
        category = request.POST.get('category', 'project')
        pool_type = request.POST.get('pool_type', '')
        size = request.POST.get('size', '')
        features = request.POST.get('features', '')
        use_ai = request.POST.get('use_ai') == 'on'
        
        data = {
            'pool_type': pool_type,
            'size': size,
            'features': features,
            'description': request.POST.get('description', ''),
            'title': request.POST.get('title', ''),
            'content': request.POST.get('tip_content', ''),
            'location': request.POST.get('location', 'Москва'),
        }
        
        generator = ContentGenerator()
        content = generator.generate_post_content(category, data, use_ai=use_ai)
        
        return JsonResponse({
            'success': True,
            'content': content,
            'ai_used': use_ai
        })
    
    categories = PostCategory.objects.all()
    
    context = {
        'categories': categories,
        'pool_types': ProjectData.POOL_TYPES,
    }
    
    return render(request, 'posts/generate.html', context)


def calendar(request):
    """Календарь публикаций"""
    # Получаем запланированные посты на текущий месяц
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1)
    
    scheduled_posts = Post.objects.filter(
        scheduled_time__gte=month_start,
        scheduled_time__lt=month_end,
        status__in=['scheduled', 'approved', 'published']
    ).order_by('scheduled_time')
    
    # Формируем события для календаря
    events = []
    for post in scheduled_posts:
        events.append({
            'id': post.id,
            'title': post.title,
            'start': post.scheduled_time.isoformat(),
            'status': post.status,
            'color': {
                'scheduled': '#17a2b8',
                'approved': '#28a745',
                'published': '#6c757d',
            }.get(post.status, '#007bff')
        })
    
    # Слоты расписания
    schedule_slots = ScheduleSlot.objects.filter(is_active=True)
    
    context = {
        'events': json.dumps(events),
        'schedule_slots': schedule_slots,
    }
    
    return render(request, 'posts/calendar.html', context)


def projects(request):
    """Список проектов бассейнов"""
    projects = ProjectData.objects.order_by('-created_at')
    
    context = {
        'projects': projects,
        'pool_types': ProjectData.POOL_TYPES,
    }
    
    return render(request, 'posts/projects.html', context)


def project_create(request):
    """Создание проекта"""
    if request.method == 'POST':
        project = ProjectData.objects.create(
            title=request.POST.get('title'),
            pool_type=request.POST.get('pool_type'),
            size=request.POST.get('size'),
            features=request.POST.get('features', ''),
            location=request.POST.get('location', ''),
            description=request.POST.get('description', ''),
        )
        
        if 'main_image' in request.FILES:
            project.main_image = request.FILES['main_image']
            project.save()
        
        messages.success(request, f'Проект "{project.title}" создан!')
        
        # Если нужно сразу создать пост
        if request.POST.get('create_post'):
            generator = ContentGenerator()
            post = generator.create_post_from_project(project)
            messages.info(request, f'Создан пост: {post.title}')
            return redirect('post_detail', post_id=post.id)
        
        return redirect('projects')
    
    context = {
        'pool_types': ProjectData.POOL_TYPES,
    }
    
    return render(request, 'posts/project_create.html', context)


def settings_page(request):
    """Страница настроек"""
    platforms = Platform.objects.all()
    schedule_slots = ScheduleSlot.objects.order_by('day_of_week', 'time')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'test_telegram':
            from apps.publishers.telegram_publisher import get_telegram_publisher
            publisher = get_telegram_publisher()
            if publisher and publisher.test_connection():
                messages.success(request, 'Telegram подключён успешно!')
            else:
                messages.error(request, 'Ошибка подключения к Telegram')
        
        elif action == 'test_vk':
            from apps.publishers.vk_publisher import get_vk_publisher
            publisher = get_vk_publisher()
            if publisher and publisher.test_connection():
                messages.success(request, 'VK подключён успешно!')
            else:
                messages.error(request, 'Ошибка подключения к VK')
        
        elif action == 'test_mistral':
            from apps.ai_generator.mistral_client import get_mistral_client
            client = get_mistral_client()
            result = client.generate_text("Скажи 'привет' одним словом")
            if result:
                messages.success(request, f'Mistral AI работает! Ответ: {result}')
            else:
                messages.error(request, 'Ошибка подключения к Mistral AI')
        
        return redirect('settings')
    
    # Получаем статус планировщика
    from apps.scheduler.scheduler import get_scheduler_status
    scheduler_status = get_scheduler_status()
    
    context = {
        'platforms': platforms,
        'schedule_slots': schedule_slots,
        'scheduler_status': scheduler_status,
        'days_of_week': ScheduleSlot.DAYS_OF_WEEK,
    }
    
    return render(request, 'posts/settings.html', context)
