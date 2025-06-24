from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import (
    Platform, VideoDownload, DownloadStatistics, 
    DownloadHistory, SupportedFormat
)
from .serializers import (
    PlatformSerializer, VideoDownloadCreateSerializer,
    VideoDownloadSerializer, VideoDownloadListSerializer,
    VideoDownloadStatusSerializer, DownloadHistorySerializer,
    DownloadStatisticsSerializer, DownloadStatsAggregatedSerializer,
    URLValidationSerializer, BulkDownloadSerializer,
    SupportedFormatSerializer
)
from .tasks import download_video_task, download_bulk_videos_task
import logging

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination standard pour les listes"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PlatformListView(generics.ListAPIView):
    """Liste des plateformes supportées"""
    queryset = Platform.objects.filter(is_active=True)
    serializer_class = PlatformSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Récupère la liste de toutes les plateformes supportées",
        responses={200: "Liste des plateformes"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SupportedFormatListView(generics.ListAPIView):
    """Liste des formats supportés par plateforme"""
    queryset = SupportedFormat.objects.select_related('platform')
    serializer_class = SupportedFormatSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['platform', 'is_video', 'is_audio']
    
    @swagger_auto_schema(
        operation_description="Récupère la liste des formats supportés par plateforme",
        manual_parameters=[
            openapi.Parameter('platform', openapi.IN_QUERY, description="ID de la plateforme", type=openapi.TYPE_INTEGER),
            openapi.Parameter('is_video', openapi.IN_QUERY, description="Filtrer par format vidéo", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_audio', openapi.IN_QUERY, description="Filtrer par format audio", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: "Liste des formats supportés"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VideoDownloadCreateView(generics.CreateAPIView):
    """Créer un nouveau téléchargement de vidéo"""
    serializer_class = VideoDownloadCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Crée un nouveau téléchargement de vidéo",
        request_body=VideoDownloadCreateSerializer,
        responses={
            201: "Téléchargement créé avec succès",
            400: "Données invalides"
        },
        examples=[
            {
                "Exemple YouTube": {
                    "value": {
                        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        "requested_quality": "best",
                        "download_audio_only": False
                    }
                }
            }
        ]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Créer l'objet VideoDownload
        instance = serializer.save()
        
        # Lancer la tâche Celery
        try:
            task = download_video_task.delay(str(instance.id))
            logger.info(f"Tâche de téléchargement lancée: {task.id} pour la vidéo {instance.id}")
        except Exception as e:
            logger.error(f"Erreur lors du lancement de la tâche: {e}")
            instance.status = 'failed'
            instance.error_message = "Erreur lors du lancement du téléchargement"
            instance.save()
        
        # Retourner la réponse avec les détails complets
        response_serializer = VideoDownloadSerializer(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class VideoDownloadListView(generics.ListAPIView):
    """Liste des téléchargements avec filtres et recherche"""
    queryset = VideoDownload.objects.select_related('platform').order_by('-created_at')
    serializer_class = VideoDownloadListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'platform', 'download_audio_only']
    search_fields = ['title', 'source_url']
    ordering_fields = ['created_at', 'completed_at', 'file_size']
    ordering = ['-created_at']
    
    @swagger_auto_schema(
        operation_description="Récupère la liste des téléchargements avec filtres et pagination",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filtrer par statut", type=openapi.TYPE_STRING, enum=['pending', 'processing', 'completed', 'failed', 'cancelled']),
            openapi.Parameter('platform', openapi.IN_QUERY, description="ID de la plateforme", type=openapi.TYPE_INTEGER),
            openapi.Parameter('download_audio_only', openapi.IN_QUERY, description="Filtrer par type de téléchargement", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('search', openapi.IN_QUERY, description="Rechercher dans le titre ou l'URL", type=openapi.TYPE_STRING),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Trier par champ", type=openapi.TYPE_STRING, enum=['created_at', '-created_at', 'completed_at', '-completed_at', 'file_size', '-file_size']),
            openapi.Parameter('page', openapi.IN_QUERY, description="Numéro de page", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Taille de page (max 100)", type=openapi.TYPE_INTEGER),
        ],
        responses={200: "Liste des téléchargements"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VideoDownloadDetailView(generics.RetrieveAPIView):
    """Détails d'un téléchargement spécifique"""
    queryset = VideoDownload.objects.select_related('platform')
    serializer_class = VideoDownloadSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    
    @swagger_auto_schema(
        operation_description="Récupère les détails complets d'un téléchargement",
        responses={
            200: "Détails du téléchargement",
            404: "Téléchargement non trouvé"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VideoDownloadStatusView(generics.RetrieveAPIView):
    """Statut d'un téléchargement (pour polling)"""
    queryset = VideoDownload.objects.all()
    serializer_class = VideoDownloadStatusSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    
    @swagger_auto_schema(
        operation_description="Récupère le statut actuel d'un téléchargement (idéal pour le polling)",
        responses={
            200: "Statut du téléchargement",
            404: "Téléchargement non trouvé"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VideoDownloadDeleteView(generics.DestroyAPIView):
    """Supprimer un téléchargement"""
    queryset = VideoDownload.objects.all()
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    
    @swagger_auto_schema(
        operation_description="Supprime un téléchargement et son fichier associé",
        responses={
            204: "Téléchargement supprimé",
            404: "Téléchargement non trouvé"
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Supprimer le fichier physique si il existe
        if instance.file_path:
            try:
                instance.file_path.delete()
            except Exception as e:
                logger.warning(f"Erreur lors de la suppression du fichier: {e}")
        
        # Supprimer l'objet de la base de données
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DownloadHistoryListView(generics.ListAPIView):
    """Historique des téléchargements"""
    queryset = DownloadHistory.objects.select_related('download', 'download__platform')
    serializer_class = DownloadHistorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['download__platform', 'download__status']
    ordering_fields = ['created_at', 'processing_time_seconds', 'download_speed_kbps']
    ordering = ['-created_at']
    
    @swagger_auto_schema(
        operation_description="Récupère l'historique des téléchargements avec métadonnées techniques",
        manual_parameters=[
            openapi.Parameter('download__platform', openapi.IN_QUERY, description="ID de la plateforme", type=openapi.TYPE_INTEGER),
            openapi.Parameter('download__status', openapi.IN_QUERY, description="Statut du téléchargement", type=openapi.TYPE_STRING),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Trier par champ", type=openapi.TYPE_STRING),
        ],
        responses={200: "Historique des téléchargements"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DownloadStatisticsListView(generics.ListAPIView):
    """Statistiques de téléchargement par jour et plateforme"""
    queryset = DownloadStatistics.objects.select_related('platform')
    serializer_class = DownloadStatisticsSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['platform', 'date']
    ordering_fields = ['date', 'total_downloads', 'success_rate']
    ordering = ['-date']
    
    @swagger_auto_schema(
        operation_description="Récupère les statistiques de téléchargement par jour et plateforme",
        manual_parameters=[
            openapi.Parameter('platform', openapi.IN_QUERY, description="ID de la plateforme", type=openapi.TYPE_INTEGER),
            openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Trier par champ", type=openapi.TYPE_STRING),
        ],
        responses={200: "Statistiques de téléchargement"}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@swagger_auto_schema(
    method='post',
    operation_description="Valide une URL avant téléchargement et détecte la plateforme",
    request_body=URLValidationSerializer,
    responses={
        200: openapi.Response(
            description="URL validée",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'url': openapi.Schema(type=openapi.TYPE_STRING),
                    'is_valid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'platform': openapi.Schema(type=openapi.TYPE_STRING),
                    'platform_display': openapi.Schema(type=openapi.TYPE_STRING),
                    'supported_qualities': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
                }
            )
        ),
        400: "URL invalide"
    },
    examples=[
        {
            "Exemple YouTube": {
                "value": {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
            }
        }
    ]
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_url(request):
    """Valider une URL avant téléchargement"""
    serializer = URLValidationSerializer(data=request.data)
    if serializer.is_valid():
        return Response(serializer.to_representation(serializer.validated_data))
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    operation_description="Crée plusieurs téléchargements en lot",
    request_body=BulkDownloadSerializer,
    responses={
        201: openapi.Response(
            description="Téléchargements créés",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'downloads': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                }
            )
        ),
        400: "Données invalides"
    },
    examples=[
        {
            "Exemple bulk": {
                "value": {
                    "urls": [
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        "https://www.youtube.com/watch?v=Zi_XLOBDo_Y"
                    ],
                    "requested_quality": "best",
                    "download_audio_only": False
                }
            }
        }
    ]
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def bulk_download(request):
    """Téléchargement en lot"""
    serializer = BulkDownloadSerializer(data=request.data)
    if serializer.is_valid():
        urls = serializer.validated_data['urls']
        requested_quality = serializer.validated_data['requested_quality']
        download_audio_only = serializer.validated_data['download_audio_only']
        
        # Créer les objets VideoDownload
        downloads = []
        for url in urls:
            try:
                create_serializer = VideoDownloadCreateSerializer(
                    data={
                        'source_url': url,
                        'requested_quality': requested_quality,
                        'download_audio_only': download_audio_only
                    },
                    context={'request': request}
                )
                if create_serializer.is_valid():
                    download = create_serializer.save()
                    downloads.append(download)
            except Exception as e:
                logger.error(f"Erreur lors de la création du téléchargement pour {url}: {e}")
                continue
        
        if downloads:
            # Lancer la tâche Celery pour le téléchargement en lot
            download_ids = [str(d.id) for d in downloads]
            try:
                task = download_bulk_videos_task.delay(download_ids)
                logger.info(f"Tâche de téléchargement en lot lancée: {task.id}")
            except Exception as e:
                logger.error(f"Erreur lors du lancement de la tâche en lot: {e}")
            
            # Retourner les détails des téléchargements créés
            response_serializer = VideoDownloadListSerializer(downloads, many=True)
            return Response({
                'message': f'{len(downloads)} téléchargements créés',
                'downloads': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'error': 'Aucun téléchargement valide créé'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_description="Récupère les statistiques agrégées de téléchargement",
    responses={
        200: "Statistiques agrégées de téléchargement"
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def download_stats(request):
    """Statistiques agrégées de téléchargement"""
    # Calculs des statistiques
    total_downloads = VideoDownload.objects.count()
    successful_downloads = VideoDownload.objects.filter(status='completed').count()
    failed_downloads = VideoDownload.objects.filter(status='failed').count()
    
    success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0
    
    # Taille totale en GB
    total_size_bytes = VideoDownload.objects.filter(
        status='completed'
    ).aggregate(total=Sum('file_size'))['total'] or 0
    total_size_gb = total_size_bytes / (1024**3)
    
    # Plateforme la plus populaire
    popular_platform = VideoDownload.objects.values(
        'platform__display_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    most_popular_platform = popular_platform['platform__display_name'] if popular_platform else 'Aucune'
    
    # Taille moyenne des fichiers
    avg_file_size = VideoDownload.objects.filter(
        status='completed',
        file_size__isnull=False
    ).aggregate(avg=Avg('file_size'))['avg'] or 0
    avg_file_size_mb = avg_file_size / (1024**2)
    
    # Téléchargements des dernières 24h et 7 jours
    now = timezone.now()
    downloads_last_24h = VideoDownload.objects.filter(
        created_at__gte=now - timedelta(days=1)
    ).count()
    
    downloads_last_week = VideoDownload.objects.filter(
        created_at__gte=now - timedelta(days=7)
    ).count()
    
    stats = {
        'total_downloads': total_downloads,
        'successful_downloads': successful_downloads,
        'failed_downloads': failed_downloads,
        'success_rate': round(success_rate, 2),
        'total_size_gb': round(total_size_gb, 2),
        'most_popular_platform': most_popular_platform,
        'avg_file_size_mb': round(avg_file_size_mb, 2),
        'downloads_last_24h': downloads_last_24h,
        'downloads_last_week': downloads_last_week,
    }
    
    serializer = DownloadStatsAggregatedSerializer(stats)
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_description="Récupère les statistiques par plateforme",
    responses={
        200: openapi.Response(
            description="Statistiques par plateforme",
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'platform_name': openapi.Schema(type=openapi.TYPE_STRING),
                        'total_downloads': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'avg_file_size_mb': openapi.Schema(type=openapi.TYPE_NUMBER)
                    }
                )
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def platform_stats(request):
    """Statistiques par plateforme"""
    platforms = Platform.objects.all()
    stats = []
    
    for platform in platforms:
        downloads = VideoDownload.objects.filter(platform=platform)
        total = downloads.count()
        successful = downloads.filter(status='completed').count()
        success_rate = (successful / total * 100) if total > 0 else 0
        
        avg_file_size = downloads.filter(
            status='completed',
            file_size__isnull=False
        ).aggregate(avg=Avg('file_size'))['avg'] or 0
        avg_file_size_mb = avg_file_size / (1024**2)
        
        stats.append({
            'platform_name': platform.display_name,
            'total_downloads': total,
            'success_rate': round(success_rate, 2),
            'avg_file_size_mb': round(avg_file_size_mb, 2)
        })
    
    return Response(stats)


@swagger_auto_schema(
    method='post',
    operation_description="Annule un téléchargement en cours",
    responses={
        200: "Téléchargement annulé",
        404: "Téléchargement non trouvé"
    }
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def cancel_download(request, download_id):
    """Annuler un téléchargement"""
    try:
        download = VideoDownload.objects.get(id=download_id)
        
        if download.status in ['pending', 'processing']:
            download.status = 'cancelled'
            download.save()
            
            # TODO: Implémenter la logique pour arrêter la tâche Celery
            # Cela nécessiterait de stocker l'ID de la tâche Celery
            
            return Response({'message': 'Téléchargement annulé'})
        else:
            return Response(
                {'error': 'Impossible d\'annuler un téléchargement terminé'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except VideoDownload.DoesNotExist:
        return Response(
            {'error': 'Téléchargement non trouvé'},
            status=status.HTTP_404_NOT_FOUND
        )


@swagger_auto_schema(
    method='get',
    operation_description="Vérifie l'état de santé de l'API et des services",
    responses={
        200: openapi.Response(
            description="État de santé",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'timestamp': openapi.Schema(type=openapi.TYPE_STRING),
                    'database': openapi.Schema(type=openapi.TYPE_STRING),
                    'celery': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Vérification de l'état de santé de l'API"""
    # Vérifier la base de données
    try:
        VideoDownload.objects.count()
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    
    # Vérifier Celery (optionnel)
    try:
        from celery import current_app
        active_tasks = current_app.control.inspect().active()
        celery_status = 'connected' if active_tasks is not None else 'disconnected'
    except:
        celery_status = 'disconnected'
    
    health_data = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'database': db_status,
        'celery': celery_status
    }
    
    return Response(health_data)