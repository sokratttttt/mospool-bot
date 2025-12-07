"""
URL routes for Posts app
"""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Posts
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('posts/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:post_id>/publish/', views.post_publish, name='post_publish'),
    path('posts/<int:post_id>/approve/', views.post_approve, name='post_approve'),
    path('posts/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    
    # Content generation
    path('generate/', views.generate_content, name='generate_content'),
    
    # Calendar
    path('calendar/', views.calendar, name='calendar'),
    
    # Projects
    path('projects/', views.projects, name='projects'),
    path('projects/create/', views.project_create, name='project_create'),
    
    # Settings
    path('settings/', views.settings_page, name='settings'),
]
