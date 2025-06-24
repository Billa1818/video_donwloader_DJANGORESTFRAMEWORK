from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from .models import (
    Platform, VideoDownload, DownloadStatistics, 
    DownloadHistory, SupportedFormat
)
import re
from urllib.parse import urlparse


class PlatformSerializer(serializers.ModelSerializer):
    """Serializer pour les plateformes"""
    
    class Meta:
        model = Platform
        fields = ['id', 'name', 'display_name', 'is_active', 'base_url', 'created_at']
        read_only_fields = ['id', 'created_at']


class SupportedFormatSerializer(serializers.ModelSerializer):
    """Serializer pour les formats supportés"""
    platform_name = serializers.CharField(source='platform.display_name', read_only=True)
    
    class Meta:
        model = SupportedFormat
        fields = [
            'id', 'platform', 'platform_name', 'format_name', 
            'mime_type', 'is_video', 'is_audio', 'max_quality'
        ]
        read_only_fields = ['id']


class VideoDownloadCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un nouveau téléchargement"""
    
    class Meta:
        model = VideoDownload
        fields = [
            'source_url', 'requested_quality', 'download_audio_only'
        ]
    
    def validate_source_url(self, value):
        """Valide l'URL source et détecte la plateforme"""
        # Validation de base de l'URL
        validator = URLValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError("URL invalide")
        
        # Détection de la plateforme
        platform = self.detect_platform(value)
        if not platform:
            raise serializers.ValidationError(
                "Plateforme non supportée. Plateformes supportées : YouTube, Facebook, Instagram, TikTok, Twitter, Vimeo, Dailymotion"
            )
        
        # Vérifier que la plateforme est active
        if not platform.is_active:
            raise serializers.ValidationError(f"La plateforme {platform.display_name} n'est pas disponible actuellement")
        
        return value
    
    def detect_platform(self, url):
        """Détecte la plateforme à partir de l'URL"""
        domain = urlparse(url).netloc.lower()
        
        platform_patterns = {
            'youtube': [r'youtube\.com', r'youtu\.be', r'youtube-nocookie\.com'],
            'facebook': [r'facebook\.com', r'fb\.watch', r'fb\.com'],
            'instagram': [r'instagram\.com', r'instagr\.am'],
            'tiktok': [r'tiktok\.com', r'vm\.tiktok\.com'],
            'twitter': [r'twitter\.com', r'x\.com', r't\.co'],
            'vimeo': [r'vimeo\.com', r'player\.vimeo\.com'],
            'dailymotion': [r'dailymotion\.com', r'dai\.ly'],
        }
        
        for platform_name, patterns in platform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, domain):
                    try:
                        return Platform.objects.get(name=platform_name, is_active=True)
                    except Platform.DoesNotExist:
                        continue
        
        return None
    
    def create(self, validated_data):
        """Crée un nouveau téléchargement avec la plateforme détectée"""
        source_url = validated_data['source_url']
        platform = self.detect_platform(source_url)
        
        # Ajouter les métadonnées de la requête
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        validated_data['platform'] = platform
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Récupère l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VideoDownloadSerializer(serializers.ModelSerializer):
    """Serializer complet pour les téléchargements de vidéos"""
    platform_name = serializers.CharField(source='platform.display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    quality_display = serializers.CharField(source='get_requested_quality_display', read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    download_url = serializers.ReadOnlyField()
    filename = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoDownload
        fields = [
            'id', 'source_url', 'platform', 'platform_name',
            'title', 'description', 'duration', 'duration_formatted',
            'thumbnail_url', 'requested_quality', 'quality_display',
            'download_audio_only', 'status', 'status_display',
            'progress_percentage', 'error_message', 'file_path',
            'file_size', 'file_size_mb', 'actual_quality',
            'download_url', 'filename', 'created_at', 'updated_at',
            'started_at', 'completed_at', 'expires_at'
        ]
        read_only_fields = [
            'id', 'platform', 'title', 'description', 'duration',
            'thumbnail_url', 'status', 'progress_percentage',
            'error_message', 'file_path', 'file_size', 'actual_quality',
            'created_at', 'updated_at', 'started_at', 'completed_at'
        ]
    
    def get_filename(self, obj):
        """Retourne le nom du fichier"""
        return obj.get_filename()
    
    def get_duration_formatted(self, obj):
        """Formate la durée en format lisible"""
        if obj.duration:
            hours = obj.duration // 3600
            minutes = (obj.duration % 3600) // 60
            seconds = obj.duration % 60
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        return None


class VideoDownloadListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des téléchargements"""
    platform_name = serializers.CharField(source='platform.display_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoDownload
        fields = [
            'id', 'title', 'platform_name', 'status', 'status_display',
            'progress_percentage', 'file_size_mb', 'duration_formatted',
            'thumbnail_url', 'created_at', 'completed_at'
        ]
    
    def get_duration_formatted(self, obj):
        """Formate la durée en format lisible"""
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return f"{minutes:02d}:{seconds:02d}"
        return None


class VideoDownloadStatusSerializer(serializers.ModelSerializer):
    """Serializer pour les mises à jour de statut"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = VideoDownload
        fields = [
            'id', 'status', 'status_display', 'progress_percentage',
            'error_message', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id']


class DownloadHistorySerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des téléchargements"""
    download_title = serializers.CharField(source='download.title', read_only=True)
    platform_name = serializers.CharField(source='download.platform.display_name', read_only=True)
    processing_time_formatted = serializers.SerializerMethodField()
    download_speed_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = DownloadHistory
        fields = [
            'id', 'download', 'download_title', 'platform_name',
            'extractor_used', 'format_id', 'codec', 'bitrate', 'fps',
            'processing_time_seconds', 'processing_time_formatted',
            'download_speed_kbps', 'download_speed_formatted',
            'uploader', 'upload_date', 'view_count', 'like_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_processing_time_formatted(self, obj):
        """Formate le temps de traitement"""
        if obj.processing_time_seconds:
            minutes = obj.processing_time_seconds // 60
            seconds = obj.processing_time_seconds % 60
            return f"{minutes}m {seconds}s"
        return None
    
    def get_download_speed_formatted(self, obj):
        """Formate la vitesse de téléchargement"""
        if obj.download_speed_kbps:
            if obj.download_speed_kbps >= 1000:
                mbps = obj.download_speed_kbps / 1000
                return f"{mbps:.1f} Mbps"
            else:
                return f"{obj.download_speed_kbps} Kbps"
        return None


class DownloadStatisticsSerializer(serializers.ModelSerializer):
    """Serializer pour les statistiques"""
    platform_name = serializers.CharField(source='platform.display_name', read_only=True)
    success_rate = serializers.ReadOnlyField()
    total_size_gb = serializers.SerializerMethodField()
    
    class Meta:
        model = DownloadStatistics
        fields = [
            'id', 'platform', 'platform_name', 'date',
            'total_downloads', 'successful_downloads', 'failed_downloads',
            'success_rate', 'total_size_mb', 'total_size_gb'
        ]
        read_only_fields = ['id']
    
    def get_total_size_gb(self, obj):
        """Convertit la taille en GB"""
        if obj.total_size_mb:
            return round(obj.total_size_mb / 1024, 2)
        return 0


class DownloadStatsAggregatedSerializer(serializers.Serializer):
    """Serializer pour les statistiques agrégées"""
    total_downloads = serializers.IntegerField()
    successful_downloads = serializers.IntegerField()
    failed_downloads = serializers.IntegerField()
    success_rate = serializers.FloatField()
    total_size_gb = serializers.FloatField()
    most_popular_platform = serializers.CharField()
    avg_file_size_mb = serializers.FloatField()
    downloads_last_24h = serializers.IntegerField()
    downloads_last_week = serializers.IntegerField()


class URLValidationSerializer(serializers.Serializer):
    """Serializer pour valider une URL avant téléchargement"""
    url = serializers.URLField()
    
    def validate_url(self, value):
        """Valide l'URL et retourne les informations de la plateforme"""
        # Réutilise la logique de détection de plateforme
        create_serializer = VideoDownloadCreateSerializer()
        platform = create_serializer.detect_platform(value)
        
        if not platform:
            raise serializers.ValidationError(
                "Plateforme non supportée"
            )
        
        if not platform.is_active:
            raise serializers.ValidationError(
                f"La plateforme {platform.display_name} n'est pas disponible"
            )
        
        return value
    
    def to_representation(self, instance):
        """Retourne les informations de validation"""
        url = instance.get('url')
        create_serializer = VideoDownloadCreateSerializer()
        platform = create_serializer.detect_platform(url)
        
        return {
            'url': url,
            'is_valid': True,
            'platform': platform.name if platform else None,
            'platform_display': platform.display_name if platform else None,
            'supported_qualities': ['144p', '240p', '360p', '480p', '720p', '1080p', 'best'],
            'supports_audio_only': True
        }


class BulkDownloadSerializer(serializers.Serializer):
    """Serializer pour les téléchargements en lot"""
    urls = serializers.ListField(
        child=serializers.URLField(),
        min_length=1,
        max_length=10,  # Limite à 10 URLs par lot
        help_text="Liste des URLs à télécharger (max 10)"
    )
    requested_quality = serializers.ChoiceField(
        choices=VideoDownload.QUALITY_CHOICES,
        default='best'
    )
    download_audio_only = serializers.BooleanField(default=False)
    
    def validate_urls(self, value):
        """Valide chaque URL dans la liste"""
        create_serializer = VideoDownloadCreateSerializer()
        valid_urls = []
        
        for url in value:
            try:
                platform = create_serializer.detect_platform(url)
                if platform and platform.is_active:
                    valid_urls.append(url)
            except:
                continue
        
        if not valid_urls:
            raise serializers.ValidationError("Aucune URL valide trouvée")
        
        return valid_urls