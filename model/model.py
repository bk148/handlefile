import os
import time
import requests
import logging
from urllib.parse import quote
from functools import lru_cache
from tenacity import (
    retry, wait_exponential, stop_after_attempt,
    retry_if_exception_type, before_sleep_log
)


class ModelGraphTransfer:
    """Classe modèle pour gérer les interactions avec Microsoft Graph API"""

    def __init__(self, token_generator, proxy):
        self.token_generator = token_generator
        self.proxy = proxy
        self.proxies = {'http': proxy, 'https': proxy}  # Configuration du proxy
        self._refresh_token()
        self.error_logs = {}
        self._init_error_logs()
        self._setup_logging()
        self.api_call_count = 0

    def _init_error_logs(self):
        """Initialiser les catégories d'erreurs"""
        categories = [
            "Connection", "Authentication", "Data Format",
            "Permissions", "Rate Limit", "File", "Network"
        ]
        self.error_logs = {f"{cat} Errors": [] for cat in categories}

    def _setup_logging(self):
        """Configurer le système de journalisation"""
        logging.basicConfig(
            filename='migration.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('graph_api')

    def _refresh_token(self):
        """Rafraîchir le token d'accès"""
        token_data = self.token_generator.generate_access_token()
        self.access_token = token_data['access_token']
        self.token_expiry = time.time() + token_data.get('expires_in', 3600) - 300
        self.headers = {'Authorization': f'Bearer {self.access_token}'}

    def _check_token(self):
        """Vérifier la validité du token"""
        if time.time() > self.token_expiry:
            self.logger.info("Actualisation du token d'accès")
            self._refresh_token()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(requests.RequestException),
        before_sleep=lambda retry_state: before_sleep_log(self.logger, logging.WARNING)
    )
    def _api_request(self, method, url, **kwargs):
        """Exécuter une requête API avec gestion des erreurs"""
        self._check_token()
        self.api_call_count += 1

        # Gestion du rate limiting
        if self.api_call_count % 10 == 0:
            time.sleep(0.5)

        try:
            # Inclure systématiquement le proxy dans les requêtes
            kwargs['proxies'] = self.proxies
            response = requests.request(
                method, url,
                headers=self.headers,
                **kwargs
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                self.logger.warning(f"Rate limit - Pause de {retry_after}s")
                time.sleep(retry_after)
                return self._api_request(method, url, **kwargs)

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            self.logger.error(f"Erreur API: {str(e)}")
            self.logger.error(f"URL: {url}")
            self.logger.error(f"Method: {method}")
            self.logger.error(f"Proxy utilisé: {self.proxy}")
            raise

    def get_target_folder(self, team_id, channel_id):
        """
        Récupérer le dossier cible pour un canal spécifique

        Args:
            team_id (str): ID de l'équipe
            channel_id (str): ID du canal

        Returns:
            dict: Informations sur le dossier cible
        """
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/filesFolder"
        try:
            response = self._api_request('GET', url)
            return {
                'id': response.json().get('id'),
                'name': response.json().get('name'),
                'webUrl': response.json().get('webUrl')
            }
        except requests.RequestException as e:
            self.logger.error(f"Erreur récupération dossier cible: {str(e)}")
            self.error_logs["Connection Errors"].append(f"{team_id}/{channel_id}")
            return None

    @lru_cache(maxsize=1024)
    def item_exists(self, site_id, parent_id, item_name):
        """Vérifier si un élément existe"""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_id}/children"
        try:
            response = self._api_request('GET', url)
            return any(item['name'] == item_name for item in response.json().get('value', []))
        except requests.RequestException:
            return False

    def create_folder(self, site_id, parent_id, folder_name):
        """Créer un dossier dans SharePoint"""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_id}/children"
        payload = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'rename'
        }
        try:
            response = self._api_request('POST', url, json=payload)
            return response.json()['id']
        except requests.RequestException as e:
            self.error_logs["File Errors"].append(f"{folder_name}: {str(e)}")
            return None

    def upload_file(self, site_id, parent_id, file_path, progress_callback=None):
        """Uploader un fichier"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Vérifier si le fichier existe déjà
        if self.item_exists(site_id, parent_id, file_name):
            self.logger.warning(f"Fichier existant ignoré: {file_name}")
            return False

        try:
            if file_size > 10 * 1024 * 1024:  # 10MB
                return self._upload_large_file(site_id, parent_id, file_path, progress_callback)
            else:
                return self._upload_small_file(site_id, parent_id, file_path, progress_callback)
        except Exception as e:
            self.error_logs["File Errors"].append(f"{file_name}: {str(e)}")
            return False

    def _upload_small_file(self, site_id, parent_id, file_path, callback):
        """Uploader un petit fichier en une seule requête"""
        file_name = quote(os.path.basename(file_path))
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_id}:/{file_name}:/content"

        with open(file_path, 'rb') as f:
            response = self._api_request('PUT', url, data=f)

        if callback:
            callback(os.path.getsize(file_path))

        return response.status_code == 201

    def _upload_large_file(self, site_id, parent_id, file_path, callback):
        """Uploader un gros fichier avec upload session"""
        file_name = quote(os.path.basename(file_path))
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_id}:/{file_name}:/createUploadSession"

        # Créer la session d'upload
        response = self._api_request('POST', url)
        upload_url = response.json()['uploadUrl']

        file_size = os.path.getsize(file_path)
        chunk_size = self._calculate_chunk_size(file_size)
        uploaded = 0

        with open(file_path, 'rb') as f:
            while uploaded < file_size:
                chunk = f.read(chunk_size)
                chunk_start = uploaded
                chunk_end = uploaded + len(chunk) - 1

                headers = {
                    'Content-Length': str(len(chunk)),
                    'Content-Range': f'bytes {chunk_start}-{chunk_end}/{file_size}'
                }

                self._api_request('PUT', upload_url, headers=headers, data=chunk)
                uploaded += len(chunk)

                if callback:
                    callback(len(chunk))

        return True

    def _calculate_chunk_size(self, file_size):
        """Calculer dynamiquement la taille des chunks"""
        return min(max(file_size // 100, 5 * 1024 * 1024), 60 * 1024 * 1024)