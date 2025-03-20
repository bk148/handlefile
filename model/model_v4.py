import os
import requests
import logging
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from rich.progress import Progress, TextColumn, BarColumn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ModelGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.token_generator = token_generator
        self.proxy = proxy
        self.access_token = self.token_generator.get_valid_token()
        self.headers = {'Authorization': f'Bearer {self.access_token}'}
        self.proxies = {'http': self.proxy, 'https': self.proxy}
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

    def refresh_token(self):
        """Rafraîchit le token et met à jour les en-têtes."""
        self.access_token = self.token_generator.get_valid_token()
        self.headers['Authorization'] = f'Bearer {self.access_token}'
        logging.info("Token refreshed.")

    def get_channel_files_folder(self, group_id, channel_id):
        """Récupère le dossier de fichiers du canal."""
        self.refresh_token()
        url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error retrieving channel files folder: {e}")
            self.error_logs["Connection Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            return None

    def item_exists(self, site_id, parent_item_id, item_name):
        """Vérifie si un fichier ou dossier existe déjà."""
        self.refresh_token()
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            items = response.json().get('value', [])
            for item in items:
                if item['name'] == item_name:
                    return True
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking item existence: {e}")
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}")
            return False

    def create_folder(self, site_id, parent_item_id, folder_name):
        """Crée un dossier dans le canal Teams."""
        self.refresh_token()
        encoded_folder_name = quote(folder_name)
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'
        }
        try:
            response = requests.post(url, headers=self.headers, json=data, proxies=self.proxies)
            response.raise_for_status()
            logging.info(f"Folder '{folder_name}' created successfully.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error creating folder: {e}")
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        """Télécharge un fichier vers le canal Teams."""
        self.refresh_token()
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            logging.info(f"File '{file_name}' already exists, skipping.")
            return file_name, "exists"

        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                logging.info(f"File '{file_name}' uploaded successfully.")
                return file_name, response.status_code
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:  # Token expiré
                self.refresh_token()
                return self.upload_file_to_channel(site_id, parent_item_id, file_path)  # Réessayer
            else:
                logging.error(f"Error uploading file '{file_name}': {e}")
                self.error_logs["File Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
                return file_name, None

    def upload_large_files(self, site_id, parent_item_id, file_path):
        """Télécharge un fichier volumineux en morceaux."""
        self.refresh_token()
        file_name = os.path.basename(file_path)
        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/createUploadSession"
        try:
            # Créer une session d'upload
            response = requests.post(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            upload_url = response.json().get('uploadUrl')

            # Télécharger le fichier en morceaux
            chunk_size = 20 * 1024 * 1024  # 20 MB
            with open(file_path, 'rb') as file:
                file_size = os.path.getsize(file_path)
                for i in range(0, file_size, chunk_size):
                    chunk_data = file.read(chunk_size)
                    chunk_headers = {
                        'Content-Length': str(len(chunk_data)),
                        'Content-Range': f'bytes {i}-{i + len(chunk_data) - 1}/{file_size}'
                    }
                    chunk_response = requests.put(upload_url, headers=chunk_headers, data=chunk_data, proxies=self.proxies)
                    chunk_response.raise_for_status()

            logging.info(f"Large file '{file_name}' uploaded successfully.")
            return file_name, "uploaded"
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading large file '{file_name}': {e}")
            self.error_logs["File Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        """Transfère un dossier entier vers le canal Teams."""
        logging.info(f"Starting transfer for group_id: {group_id}, channel_id: {channel_id}, site_id: {site_id}")
        files_folder_response = self.get_channel_files_folder(group_id, channel_id)

        if 'parentReference' not in files_folder_response:
            logging.error("Error: 'parentReference' does not exist in the API response.")
            self.error_logs["Data Format Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            return

        drive_id = files_folder_response['parentReference']['driveId']
        parent_item_id = files_folder_response['id']

        # Créer le dossier parent
        folder_name = os.path.basename(depot_data_directory_path)
        if not self.item_exists(site_id, parent_item_id, folder_name):
            folder_response = self.create_folder(site_id, parent_item_id, folder_name)
            parent_item_id = folder_response['id']
        else:
            parent_item_id = next(item['id'] for item in requests.get(
                f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children",
                headers=self.headers, proxies=self.proxies
            ).json()['value'] if item['name'] == folder_name)

        # Parcourir les fichiers et dossiers
        for root, dirs, files in os.walk(depot_data_directory_path):
            relative_path = os.path.relpath(root, depot_data_directory_path)
            current_parent_item_id = parent_item_id

            # Créer les dossiers dans le canal Teams
            if relative_path != ".":
                for folder in relative_path.split(os.sep):
                    if not self.item_exists(site_id, current_parent_item_id, folder):
                        folder_response = self.create_folder(site_id, current_parent_item_id, folder)
                        current_parent_item_id = folder_response['id']
                    else:
                        current_parent_item_id = next(item['id'] for item in requests.get(
                            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{current_parent_item_id}/children",
                            headers=self.headers, proxies=self.proxies
                        ).json()['value'] if item['name'] == folder)

            # Télécharger les fichiers
            for file_name in files:
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                if file_size >= 1 * 1024 * 1024 * 1024:  # 1 Go
                    logging.info(f"Large file detected: {file_name}. Using upload_large_files.")
                    self.upload_large_files(site_id, current_parent_item_id, file_path)
                else:
                    self.upload_file_to_channel(site_id, current_parent_item_id, file_path)

        logging.info("Transfer completed successfully.")