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
        self.proxies = {'http': self.proxy, 'https': self.proxy}  # Définition du proxy
        self._refresh_token()
        self.error_logs = {
            "Connection Error": [],
            "Authentication Error": [],
            "Data Format Error": [],
            "Access Rights Error": [],
            "Network Error": [],
            "Quota Error": [],
            "File Error": [],
            "Cyclic Redundancy Error": [],
            "Ignored Files": []
        }
        self._setup_logging()

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
    def _make_request(self, method, url, **kwargs):
        """Exécuter une requête API avec gestion des erreurs"""
        self._check_token()
        try:
            # Inclure systématiquement le proxy
            kwargs['proxies'] = self.proxies
            response = requests.request(
                method, url,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Erreur API: {str(e)}")
            self.logger.error(f"URL: {url}")
            self.logger.error(f"Method: {method}")
            self.logger.error(f"Proxy utilisé: {self.proxy}")
            raise

    def get_channel_files_folder(self, group_id, channel_id):
        """
        Récupérer le dossier de fichiers associé à un canal Teams.

        Args:
            group_id (str): ID de l'équipe (groupe) Teams.
            channel_id (str): ID du canal Teams.

        Returns:
            dict: Informations sur le dossier de fichiers, ou None en cas d'erreur.
        """
        url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
        try:
            response = self._make_request('GET', url)
            return {
                'id': response.json().get('id'),
                'name': response.json().get('name'),
                'webUrl': response.json().get('webUrl')
            }
        except requests.RequestException as e:
            self.logger.error(f"Erreur récupération dossier de fichiers: {str(e)}")
            self.error_logs["Connection Errors"].append(f"{group_id}/{channel_id}")
            return None

    @lru_cache(maxsize=1024)
    def item_exists(self, site_id, parent_item_id, item_name):
        """Vérifier si un élément existe"""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        try:
            response = self._make_request('GET', url)
            items = response.json().get('value', [])
            return any(item['name'] == item_name for item in items)
        except requests.RequestException:
            return False

    def create_folder(self, site_id, parent_item_id, folder_name):
        """Créer un dossier dans SharePoint"""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'
        }
        try:
            response = self._make_request('POST', url, json=data)
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Erreur création dossier: {str(e)}")
            self.error_logs["Connection Errors"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        """Uploader un fichier dans un canal Teams"""
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            return file_name, "exists"

        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = self._make_request('PUT', url, data=file)
                return file_name, response.status_code
        except requests.RequestException as e:
            self.logger.error(f"Erreur upload fichier: {str(e)}")
            self.error_logs["File Errors"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def upload_large_files(self, site_id, parent_item_id, file_path):
        """Uploader un gros fichier avec upload session"""
        file_name = os.path.basename(file_path)
        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/createUploadSession"
        try:
            # Créer la session d'upload
            response = self._make_request('POST', url)
            upload_url = response.json().get('uploadUrl')

            # Uploader le fichier en chunks
            chunk_size = self._calculate_chunk_size(os.path.getsize(file_path))
            with open(file_path, 'rb') as file:
                file_size = os.path.getsize(file_path)
                for i in range(0, file_size, chunk_size):
                    chunk_data = file.read(chunk_size)
                    chunk_headers = {
                        'Content-Length': str(len(chunk_data)),
                        'Content-Range': f'bytes {i}-{i + len(chunk_data) - 1}/{file_size}'
                    }
                    # Utiliser le proxy pour l'upload des chunks
                    chunk_response = requests.put(
                        upload_url,
                        headers=chunk_headers,
                        data=chunk_data,
                        proxies=self.proxies  # Proxy inclus ici
                    )
                    chunk_response.raise_for_status()

            return file_name, "uploaded"
        except requests.RequestException as e:
            self.logger.error(f"Erreur upload gros fichier: {str(e)}")
            self.error_logs["File Errors"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def _calculate_chunk_size(self, file_size):
        """
        Calculer dynamiquement la taille des chunks pour l'upload de gros fichiers.

        Args:
            file_size (int): Taille du fichier en octets.

        Returns:
            int: Taille du chunk en octets.
        """
        # Taille minimale : 5 Mo, taille maximale : 60 Mo
        return min(max(file_size // 100, 5 * 1024 * 1024), 60 * 1024 * 1024)