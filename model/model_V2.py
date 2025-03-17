import os
import requests
import logging
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

# Créer le répertoire de logs s'il n'existe pas
if not os.path.exists("transferLogs"):
    os.makedirs("transferLogs")

# Configuration du logging général
logging.basicConfig(
    filename='transferLogs/transfer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration des loggers pour chaque type d'erreur
error_loggers = {}
error_types = [
    "Connection Error", "Authentication Error", "Data Format Error",
    "Access Rights Error", "Network Error", "Quota Error",
    "File Error", "Cyclic Redundancy Error", "Ignored Files"
]

for error_type in error_types:
    logger = logging.getLogger(error_type)
    handler = logging.FileHandler(f"transferLogs/{error_type.replace(' ', '')}.log")
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    error_loggers[error_type] = logger

class ModelGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.token_generator = token_generator
        self.proxy = proxy
        self.access_token = self.token_generator.generate_access_token()['access_token']
        self.headers = {'Authorization': f'Bearer {self.access_token}'}
        self.proxies = {'http': self.proxy, 'https': self.proxy}
        self.error_logs = {error_type: [] for error_type in error_types}
        self.transferred_files = []

    def get_channel_files_folder(self, group_id, channel_id):
        url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            logging.info(f"Répertoire des fichiers du canal récupéré : {group_id}/{channel_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur lors de la récupération du répertoire des fichiers : {e}")
            self.error_logs["Connection Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            error_loggers["Connection Error"].error(f"Group ID: {group_id}, Channel ID: {channel_id} - {e}")
            return None

    def item_exists(self, site_id, parent_item_id, item_name):
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            items = response.json().get('value', [])
            for item in items:
                if item['name'] == item_name:
                    logging.info(f"Item existe déjà : {item_name}")
                    return True
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur lors de la vérification de l'existence de l'item : {e}")
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}")
            error_loggers["Connection Error"].error(f"Site ID: {site_id}, Parent Item ID: {parent_item_id} - {e}")
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
            logging.info(f"Dossier créé : {folder_name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur lors de la création du dossier : {e}")
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            error_loggers["Connection Error"].error(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name} - {e}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            self.transferred_files.append((file_name, "exists"))
            logging.info(f"Fichier déjà existant : {file_name}")
            return file_name, "exists"

        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                self.transferred_files.append((file_name, "success"))
                logging.info(f"Fichier téléversé avec succès : {file_name}")
                return file_name, response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Erreur lors du téléversement du fichier : {e}")
            self.error_logs["File Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            error_loggers["File Error"].error(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path} - {e}")
            self.transferred_files.append((file_name, "error"))
            return file_name, None

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        files_folder_response = self.get_channel_files_folder(group_id, channel_id)

        if 'parentReference' in files_folder_response:
            drive_id = files_folder_response['parentReference']['driveId']
            parent_item_id = files_folder_response['id']
        else:
            logging.error("Erreur : 'parentReference' absent dans la réponse de l'API.")
            self.error_logs["Data Format Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            error_loggers["Data Format Error"].error(f"Group ID: {group_id}, Channel ID: {channel_id}")
            drive_id = None
            parent_item_id = None

        if drive_id and parent_item_id:
            folder_name = os.path.basename(depot_data_directory_path)
            if not self.item_exists(site_id, parent_item_id, folder_name):
                folder_response = self.create_folder(site_id, parent_item_id, folder_name)
                parent_item_id = folder_response['id']
            else:
                parent_item_id = next(item['id'] for item in requests.get(
                    f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children",
                    headers=self.headers, proxies=self.proxies
                ).json()['value'] if item['name'] == folder_name)

            total_files = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
            completed_files = 0

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for root, dirs, files in os.walk(depot_data_directory_path):
                    relative_path = os.path.relpath(root, depot_data_directory_path)
                    current_parent_item_id = parent_item_id

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

                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        futures.append(executor.submit(self.upload_file_to_channel, site_id, current_parent_item_id, file_path))

                for future in as_completed(futures):
                    file_name, status = future.result()
                    if status != "exists":
                        completed_files += 1

            return completed_files, total_files