import concurrent
import os
import requests
import logging
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from rich.progress import Progress, TextColumn, BarColumn

# Définir un seuil pour les fichiers volumineux (par exemple, 10 Mo)
LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10 Mo


class ModelGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.token_generator = token_generator
        self.proxy = proxy
        self.access_token = self.token_generator.generate_access_token()['access_token']
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

    def get_channel_files_folder(self, group_id, channel_id):
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
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'
        }
        try:
            response = requests.post(url, headers=self.headers, json=data, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error creating folder: {e}")
            self.error_logs["Connection Error"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        """
        Upload un fichier de taille normale.
        """
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            return file_name, "exists"

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                logging.info(f"Uploading file: {file_name} (Size: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB)")
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                return file_name, response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading file: {e}")
            self.error_logs["File Error"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def upload_large_file(self, site_id, parent_item_id, file_path):
        """
        Upload un fichier volumineux en utilisant une méthode optimisée.
        """
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            return file_name, "exists"

        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                logging.info(
                    f"Uploading large file: {file_name} (Size: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB)")
                # Ici, vous pouvez implémenter une logique spécifique pour les gros fichiers,
                # comme le découpage en morceaux (chunking) ou l'utilisation de sessions d'upload.
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                return file_name, response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading large file: {e}")
            self.error_logs["File Error"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path, progress=None,
                                        task=None):
        # Obtenir le dossier de fichiers du canal
        files_folder_response = self.get_channel_files_folder(group_id, channel_id)

        if 'parentReference' in files_folder_response:
            drive_id = files_folder_response['parentReference']['driveId']
            parent_item_id = files_folder_response['id']
        else:
            logging.error("Error: 'parentReference' does not exist in the API response.")
            self.error_logs["Data Format Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            drive_id = None
            parent_item_id = None

        if drive_id and parent_item_id:
            # Créer le dossier parent
            folder_name = os.path.basename(depot_data_directory_path)
            encoded_folder_name = quote(folder_name)
            if not self.item_exists(site_id, parent_item_id, folder_name):
                folder_response = self.create_folder(site_id, parent_item_id, encoded_folder_name)
                parent_item_id = folder_response['id']
            else:
                parent_item_id = next(item['id'] for item in requests.get(
                    f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children",
                    headers=self.headers, proxies=self.proxies
                ).json()['value'] if item['name'] == folder_name)

            # Parcourir les fichiers et dossiers
            total_copied = 0
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

                # Télécharger les fichiers dans le canal Teams
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_name, status = self.upload_file_to_channel(site_id, current_parent_item_id, file_path)
                    if status == "exists":
                        logging.info(f"File {file_name} already exists, skipping.")
                    elif status is not None:
                        total_copied += 1
                    # Mettre à jour la progression si une barre de progression est fournie
                    if progress and task:
                        progress.update(task, advance=1)

            return os.path.getsize(depot_data_directory_path), len(files), len(dirs), total_copied
