from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from django.utils.html import format_html
from django.conf import settings
from .models import Platform, VideoDownload, SupportedFormat
from .tasks import download_video_task
import yt_dlp
import os
from urllib.parse import urlparse
import re

class DownloadFromUrlForm(forms.Form):
    url = forms.URLField(label="URL de la vidéo", required=True)
    quality = forms.ChoiceField(label="Qualité", required=False)
    audio_only = forms.BooleanField(label="Audio uniquement", required=False)

    def __init__(self, *args, **kwargs):
        qualities = kwargs.pop('qualities', None)
        super().__init__(*args, **kwargs)
        if qualities:
            self.fields['quality'].choices = [(q, q) for q in qualities]
        else:
            self.fields['quality'].choices = [("best", "Meilleure qualité disponible")]

@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name', 'is_active', 'base_url', 'created_at')
    search_fields = ('name', 'display_name')
    list_filter = ('is_active',)
    ordering = ('name',)

@admin.register(VideoDownload)
class VideoDownloadAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'platform', 'source_url', 'requested_quality', 'download_audio_only',
        'status', 'progress_percentage', 'file_size_mb', 'created_at', 'completed_at', 'expires_at', 'download_link_admin'
    )
    search_fields = ('title', 'source_url')
    list_filter = ('platform', 'status', 'download_audio_only')
    readonly_fields = ('file_path', 'file_size', 'progress_percentage', 'created_at', 'updated_at', 'started_at', 'completed_at', 'download_link_admin')
    ordering = ('-created_at',)
    actions = ['mark_as_completed', 'mark_as_failed']
    change_list_template = "admin/downloader/videodownload_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-from-url/', self.admin_site.admin_view(self.download_from_url), name='download-from-url'),
        ]
        return custom_urls + urls

    def download_from_url(self, request):
        context = dict(
            self.admin_site.each_context(request),
        )
        qualities = None
        url = None
        if request.method == 'POST':
            url = request.POST.get('url')
            audio_only = bool(request.POST.get('audio_only'))
            if url and 'get_formats' in request.POST:
                # Utiliser yt-dlp pour détecter les formats
                try:
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                        formats = info.get('formats', [])
                        # On ne garde que les formats combinés (vidéo+audio)
                        qualities = sorted(set(
                            str(f.get('height', 'audio'))
                            for f in formats
                            if (
                                (f.get('vcodec') and f['vcodec'] != 'none') and
                                (f.get('acodec') and f['acodec'] != 'none')
                            )
                        ))
                        if not qualities:
                            qualities = ['best']
                except Exception as e:
                    context['error'] = f"Erreur lors de la détection des formats : {e}"
            elif url and 'download' in request.POST:
                # Détecter la plateforme à partir de l'URL
                platform = self.detect_platform(url)
                if not platform:
                    context['error'] = "Impossible de détecter la plateforme pour cette URL."
                else:
                    quality = request.POST.get('quality', 'best')
                    vd = VideoDownload.objects.create(
                        source_url=url,
                        platform=platform,
                        requested_quality=quality,
                        download_audio_only=audio_only,
                        status='pending',
                    )
                    download_video_task.delay(str(vd.id))
                    return redirect(f'../{vd.id}/change/')
        form = DownloadFromUrlForm(initial={'url': url}, qualities=qualities)
        context['form'] = form
        context['qualities'] = qualities
        return render(request, 'admin/downloader/download_from_url.html', context)

    def detect_platform(self, url):
        domain = urlparse(url).netloc.lower()
        platform_patterns = {
            'youtube': [r'youtube\\.com', r'youtu\\.be', r'youtube-nocookie\\.com'],
            'facebook': [r'facebook\\.com', r'fb\\.watch', r'fb\\.com'],
            'instagram': [r'instagram\\.com', r'instagr\\.am'],
            'tiktok': [r'tiktok\\.com', r'vm\\.tiktok\\.com'],
            'twitter': [r'twitter\\.com', r'x\\.com', r't\\.co'],
            'vimeo': [r'vimeo\\.com', r'player\\.vimeo\\.com'],
            'dailymotion': [r'dailymotion\\.com', r'dai\\.ly'],
        }
        from .models import Platform
        for platform_name, patterns in platform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, domain):
                    try:
                        return Platform.objects.get(name=platform_name, is_active=True)
                    except Platform.DoesNotExist:
                        continue
        return None

    def download_link_admin(self, obj):
        if obj.file_path:
            url = obj.file_path.url if hasattr(obj.file_path, 'url') else obj.download_url
            return format_html('<a href="{}" download>Télécharger</a>', url)
        return "-"
    download_link_admin.short_description = "Lien de téléchargement"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_as_completed.short_description = "Marquer comme terminé"

    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_as_failed.short_description = "Marquer comme échoué"

@admin.register(SupportedFormat)
class SupportedFormatAdmin(admin.ModelAdmin):
    list_display = ('id', 'platform', 'format_name', 'mime_type', 'is_video', 'is_audio', 'max_quality')
    search_fields = ('format_name', 'mime_type')
    list_filter = ('platform', 'is_video', 'is_audio')
    ordering = ('platform', 'format_name') 