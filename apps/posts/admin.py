"""
Django Admin configuration for Posts app
Админ-панель для управления публикациями
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Platform, PostCategory, PostTemplate, 
    Post, Publication, ProjectData, ScheduleSlot
)


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'is_active', 'channel_id', 'updated_at']
    list_filter = ['is_active', 'name']
    search_fields = ['display_name', 'channel_id']
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'display_name', 'is_active')
        }),
        ('API настройки', {
            'fields': ('api_token', 'channel_id'),
            'classes': ('collapse',),
        }),
    )


@admin.register(PostCategory)
class PostCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description']
    search_fields = ['name']


@admin.register(PostTemplate)
class PostTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'template_text']
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'category', 'is_active')
        }),
        ('Шаблон', {
            'fields': ('template_text', 'hashtags'),
        }),
        ('Настройки ИИ', {
            'fields': ('ai_prompt',),
            'classes': ('collapse',),
        }),
    )


class PublicationInline(admin.TabularInline):
    model = Publication
    extra = 0
    readonly_fields = ['platform', 'status', 'external_id', 'external_url', 'published_at', 'error_message']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status_badge', 'platforms_list', 'scheduled_time', 'created_at']
    list_filter = ['status', 'category', 'platforms', 'ai_generated', 'created_at']
    search_fields = ['title', 'content']
    date_hierarchy = 'created_at'
    filter_horizontal = ['platforms']
    inlines = [PublicationInline]
    readonly_fields = ['created_at', 'updated_at', 'published_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('title', 'category', 'status')
        }),
        ('Контент', {
            'fields': ('content', 'content_telegram', 'content_vk', 'image'),
        }),
        ('Публикация', {
            'fields': ('platforms', 'scheduled_time'),
        }),
        ('ИИ генерация', {
            'fields': ('ai_generated', 'ai_prompt_used', 'template'),
            'classes': ('collapse',),
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',),
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'approved': '#28a745',
            'scheduled': '#17a2b8',
            'publishing': '#007bff',
            'published': '#28a745',
            'failed': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def platforms_list(self, obj):
        return ", ".join([p.display_name for p in obj.platforms.all()])
    platforms_list.short_description = 'Платформы'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['post', 'platform', 'status', 'external_id', 'published_at']
    list_filter = ['status', 'platform', 'published_at']
    search_fields = ['post__title', 'external_id']
    readonly_fields = ['post', 'platform', 'status', 'external_id', 'external_url', 'error_message', 'published_at']


@admin.register(ProjectData)
class ProjectDataAdmin(admin.ModelAdmin):
    list_display = ['title', 'pool_type', 'size', 'location', 'is_published', 'created_at']
    list_filter = ['pool_type', 'is_published', 'created_at']
    search_fields = ['title', 'description', 'location']
    
    fieldsets = (
        ('Основное', {
            'fields': ('title', 'pool_type', 'size', 'location')
        }),
        ('Детали', {
            'fields': ('features', 'description'),
        }),
        ('Изображения', {
            'fields': ('main_image', 'images'),
        }),
        ('Статус', {
            'fields': ('is_published', 'source_url'),
        }),
    )
    
    actions = ['create_post_from_project']
    
    @admin.action(description='Создать пост из выбранных проектов')
    def create_post_from_project(self, request, queryset):
        from .services.content_generator import ContentGenerator
        generator = ContentGenerator()
        
        created_count = 0
        for project in queryset.filter(is_published=False):
            try:
                post = generator.create_post_from_project(project)
                project.is_published = True
                project.save()
                created_count += 1
            except Exception as e:
                self.message_user(request, f"Ошибка для {project.title}: {e}", level='error')
        
        self.message_user(request, f"Создано постов: {created_count}")


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ['day_of_week', 'time', 'is_active', 'platforms_list', 'preferred_category']
    list_filter = ['is_active', 'day_of_week', 'platforms']
    filter_horizontal = ['platforms']
    
    def platforms_list(self, obj):
        return ", ".join([p.display_name for p in obj.platforms.all()])
    platforms_list.short_description = 'Платформы'


# Customize admin site
admin.site.site_header = '🏊 Бассейны: Соцсети'
admin.site.site_title = 'Управление публикациями'
admin.site.index_title = 'Панель управления'
