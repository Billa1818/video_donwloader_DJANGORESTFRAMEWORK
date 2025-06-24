from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from .models import Platform, VideoDownload

# Create your tests here.

class DownloaderAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.platform = Platform.objects.create(
            name='youtube', display_name='YouTube', is_active=True
        )

    def test_platform_list(self):
        url = reverse('platform-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('YouTube', str(response.data))

    def test_supported_format_list(self):
        url = reverse('supported-format-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_download(self):
        url = reverse('download-create')
        data = {
            'source_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'requested_quality': 'best',
            'download_audio_only': False
        }
        response = self.client.post(url, data)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])

    def test_download_list(self):
        url = reverse('download-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_detail(self):
        download = VideoDownload.objects.create(
            source_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            platform=self.platform
        )
        url = reverse('download-detail', args=[download.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_status(self):
        download = VideoDownload.objects.create(
            source_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            platform=self.platform
        )
        url = reverse('download-status', args=[download.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_delete(self):
        download = VideoDownload.objects.create(
            source_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            platform=self.platform
        )
        url = reverse('download-delete', args=[download.id])
        response = self.client.delete(url)
        self.assertIn(response.status_code, [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND])

    def test_validate_url(self):
        url = reverse('validate-url')
        data = {'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'}
        response = self.client.post(url, data)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_bulk_download(self):
        url = reverse('bulk-download')
        data = {
            'urls': [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'https://www.youtube.com/watch?v=Zi_XLOBDo_Y'
            ],
            'requested_quality': 'best',
            'download_audio_only': False
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
