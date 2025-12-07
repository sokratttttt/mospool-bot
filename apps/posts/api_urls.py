"""
API endpoints for Posts app
"""
from django.urls import path
from . import api_views

urlpatterns = [
    path('posts/', api_views.posts_list, name='api_posts_list'),
    path('posts/<int:post_id>/', api_views.post_detail, name='api_post_detail'),
    path('posts/<int:post_id>/publish/', api_views.publish_post, name='api_publish_post'),
    path('generate/', api_views.generate_content, name='api_generate'),
    path('platforms/status/', api_views.platforms_status, name='api_platforms_status'),
    path('scheduler/status/', api_views.scheduler_status, name='api_scheduler_status'),
]
