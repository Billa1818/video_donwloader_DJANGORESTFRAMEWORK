import requests
import time

BASE_URL = 'http://127.0.0.1:8000/api'

# 1. Demander l'URL à l'utilisateur
url_to_test = input('Entrez l\'URL de la vidéo à tester : ').strip()

# 2. Valider l'URL et détecter la plateforme
validate_url = f'{BASE_URL}/validate-url/'
resp = requests.post(validate_url, json={'url': url_to_test})
try:
    print('Validation URL:', resp.status_code, resp.json())
except Exception:
    print('Validation URL:', resp.status_code, resp.text)

# 3. Afficher les formats disponibles
formats_url = f'{BASE_URL}/formats/'
resp = requests.post(formats_url, json={'url': url_to_test})
try:
    formats = resp.json().get('formats', [])
    print(f'Formats disponibles ({len(formats)}):')
    for f in formats:
        print(f"- id={f['format_id']} ext={f['ext']} height={f['height']} vcodec={f['vcodec']} acodec={f['acodec']} note={f['format_note']}")
except Exception:
    print('Erreur formats:', resp.status_code, resp.text)
    formats = []

if not formats:
    print("Aucun format disponible pour cette vidéo.")
    exit(1)

# 4. Demander à l'utilisateur de choisir un format_id
format_id = input('Entrez le format_id à utiliser pour le téléchargement : ').strip()

# 5. Lancer le téléchargement avec ce format_id
print(f'\nTentative de téléchargement avec format_id: {format_id}')
create_url = f'{BASE_URL}/downloads/create/'
data = {
    'source_url': url_to_test,
    'requested_quality': format_id,
    'download_audio_only': False
}
resp = requests.post(create_url, json=data)
try:
    print('Création téléchargement:', resp.status_code, resp.json())
    download_id = resp.json().get('id')
except Exception:
    print('Création téléchargement:', resp.status_code, resp.text)
    download_id = None
if not download_id:
    exit(1)

# 6. Vérifier le statut du téléchargement
status_url = f'{BASE_URL}/downloads/{download_id}/status/'
for i in range(10):
    resp = requests.get(status_url)
    try:
        print(f'Statut tentative {i+1}:', resp.status_code, resp.json())
        status = resp.json().get('status')
        error_message = resp.json().get('error_message')
    except Exception:
        print(f'Statut tentative {i+1}:', resp.status_code, resp.text)
        status = None
        error_message = None
    if status == 'completed':
        break
    if status == 'failed' and error_message and 'Requested format is not available' in error_message:
        break
    time.sleep(5)

# 7. Récupérer les infos du téléchargement (lien de téléchargement)
detail_url = f'{BASE_URL}/downloads/{download_id}/'
resp = requests.get(detail_url)
try:
    print('Détail téléchargement:', resp.status_code, resp.json())
    download_url = resp.json().get('download_url')
except Exception:
    print('Détail téléchargement:', resp.status_code, resp.text)
    download_url = None
# 8. Télécharger le fichier si prêt
if download_url:
    if not download_url.startswith('http'):
        download_url = f'http://127.0.0.1:8000{download_url}'
    file_resp = requests.get(download_url)
    with open('video_test.mp4', 'wb') as f:
        f.write(file_resp.content)
    print('Vidéo téléchargée sous video_test.mp4')
else:
    print('Lien de téléchargement non disponible.')
# 9. Lister tous les téléchargements
list_url = f'{BASE_URL}/downloads/'
resp = requests.get(list_url)
try:
    print('Liste des téléchargements:', resp.status_code, resp.json())
except Exception:
    print('Liste des téléchargements:', resp.status_code, resp.text)
# 10. Supprimer le téléchargement
delete_url = f'{BASE_URL}/downloads/{download_id}/delete/'
resp = requests.delete(delete_url)
print('Suppression téléchargement:', resp.status_code) 