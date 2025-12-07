"""
API Views for Posts app - JSON API endpoints
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from .models import Post, Platform
from .services.content_generator import ContentGenerator


@require_GET
def posts_list(request):
    """Список постов (API)"""
    status = request.GET.get('status')
    
    posts = Post.objects.all()
    if status:
        posts = posts.filter(status=status)
    
    posts = posts.order_by('-created_at')[:50]
    
    data = [{
        'id': post.id,
        'title': post.title,
        'status': post.status,
        'category': post.category.name if post.category else None,
        'scheduled_time': post.scheduled_time.isoformat() if post.scheduled_time else None,
        'created_at': post.created_at.isoformat(),
    } for post in posts]
    
    return JsonResponse({'posts': data})


@require_GET
def post_detail(request, post_id):
    """Детали поста (API)"""
    post = get_object_or_404(Post, id=post_id)
    
    data = {
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'content_telegram': post.content_telegram,
        'content_vk': post.content_vk,
        'status': post.status,
        'category': post.category.name if post.category else None,
        'platforms': [p.name for p in post.platforms.all()],
        'scheduled_time': post.scheduled_time.isoformat() if post.scheduled_time else None,
        'image': post.image.url if post.image else None,
        'ai_generated': post.ai_generated,
        'created_at': post.created_at.isoformat(),
        'published_at': post.published_at.isoformat() if post.published_at else None,
    }
    
    return JsonResponse({'post': data})


@csrf_exempt
@require_POST
def publish_post(request, post_id):
    """Публикация поста (API)"""
    post = get_object_or_404(Post, id=post_id)
    
    if not post.platforms.exists():
        return JsonResponse({
            'success': False,
            'error': 'No platforms selected'
        }, status=400)
    
    from apps.publishers.manager import publish_post as do_publish
    results = do_publish(post)
    
    return JsonResponse({
        'success': all(r.get('success') for r in results),
        'results': results
    })


@csrf_exempt
@require_POST
def generate_content(request):
    """Генерация контента (API)"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    category = data.get('category', 'project')
    use_ai = data.get('use_ai', True)
    
    generator = ContentGenerator()
    content = generator.generate_post_content(category, data, use_ai=use_ai)
    
    return JsonResponse({
        'success': True,
        'content': content
    })


@require_GET
def platforms_status(request):
    """Статус платформ (API)"""
    from apps.publishers.manager import PublisherManager
    
    try:
        manager = PublisherManager.from_database()
        status = manager.test_all_connections()
    except Exception as e:
        status = {'error': str(e)}
    
    platforms = Platform.objects.filter(is_active=True)
    data = [{
        'name': p.name,
        'display_name': p.display_name,
        'is_active': p.is_active,
        'connected': status.get(p.name, False)
    } for p in platforms]
    
    return JsonResponse({'platforms': data})


@require_GET
def scheduler_status(request):
    """Статус планировщика (API)"""
    from apps.scheduler.scheduler import get_scheduler_status
    
    status = get_scheduler_status()
    return JsonResponse(status)
