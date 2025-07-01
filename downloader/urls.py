from django.urls import path
from . import views

urlpatterns = [
    path('platforms/', views.PlatformListView.as_view(), name='platform-list'),
    path('formats/', views.available_formats, name='available-formats'),
    path('downloads/', views.VideoDownloadListView.as_view(), name='download-list'),
    path('downloads/create/', views.VideoDownloadCreateView.as_view(), name='download-create'),
    path('downloads/<uuid:id>/', views.VideoDownloadDetailView.as_view(), name='download-detail'),
    path('downloads/<uuid:id>/status/', views.VideoDownloadStatusView.as_view(), name='download-status'),
    path('downloads/<uuid:id>/delete/', views.VideoDownloadDeleteView.as_view(), name='download-delete'),
    path('validate-url/', views.validate_url, name='validate-url'),
    path('bulk-download/', views.bulk_download, name='bulk-download'),
    path('downloads/<uuid:download_id>/cancel/', views.cancel_download, name='cancel-download'),
    path('health/', views.health_check, name='health-check'),
] 