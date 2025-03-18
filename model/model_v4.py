import concurrent
import time
import os
import requests
import logging
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from rich.progress import Progress, TextColumn, BarColumn
from utilis.logger import MigrationLogger  # Importer le MigrationLogger


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
        self.logger = MigrationLogger()  # Initialiser le logger

    def get_channel_files_folder(self, group_id, channel_id):
        url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            self.logger.log_info(f"Récupération réussie du dossier de fichiers pour le groupe {group_id}, canal {channel_id}.")
            return response.json()
        except requests.exceptions.RequestException as e:
            error_message = f"Erreur lors de la récupération du dossier de fichiers : {e}"
            self.logger.log_error(error_message)
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
            error_message = f"Erreur lors de la vérification de l'existence de l'élément : {e}"
            self.logger.log_error(error_message)
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
            self.logger.log_info(f"Dossier '{folder_name}' créé avec succès.")
            return response.json()
        except requests.exceptions.RequestException as e:
            error_message = f"Erreur lors de la création du dossier : {e}"
            self.logger.log_error(error_message)
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        if file_size >= 1 * 1024 * 1024 * 1024:  # 1 Go
            return self.upload_large_files(site_id, parent_item_id, file_path)

        if self.item_exists(site_id, parent_item_id, file_name):
            self.logger.log_info(f"Le fichier '{file_name}' existe déjà, il est ignoré.")
            return file_name, "exists"
        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                self.logger.log_info(f"Fichier '{file_name}' uploadé avec succès.")
                return file_name, response.status_code
        except requests.exceptions.RequestException as e:
            error_message = f"Erreur lors de l'upload du fichier '{file_name}' : {e}"
            self.logger.log_error(error_message)
            self.error_logs["File Error"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def upload_large_files(self, site_id, parent_item_id, file_path):
        file_name = os.path.basename(file_path)
        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/createUploadSession"
        try:
            # Créer une session d'upload
            response = requests.post(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            upload_url = response.json().get('uploadUrl')

            # Upload du fichier par chunks
            chunk_size = 20 * 1024 * 1024  # 20 MB
            with open(file_path, 'rb') as file:
                file_size = os.path.getsize(file_path)
                for i in range(0, file_size, chunk_size):
                    chunk_data = file.read(chunk_size)
                    chunk_headers = {
                        'Content-Length': str(len(chunk_data)),
                        'Content-Range': f'bytes {i}-{i + len(chunk_data) - 1}/{file_size}'
                    }
                    chunk_response = requests.put(upload_url, headers=chunk_headers, data=chunk_data,
                                                  proxies=self.proxies)
                    chunk_response.raise_for_status()

            self.logger.log_info(f"Fichier volumineux '{file_name}' uploadé avec succès.")
            return file_name, "uploaded"
        except requests.exceptions.RequestException as e:
            error_message = f"Erreur lors de l'upload du fichier volumineux '{file_name}' : {e}"
            self.logger.log_error(error_message)
            self.error_logs["File Error"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        # Obtenir le dossier de fichiers du canal
        files_folder_response = self.get_channel_files_folder(group_id, channel_id)

        # Vérifier si 'parentReference' existe dans la réponse
        if 'parentReference' in files_folder_response:
            drive_id = files_folder_response['parentReference']['driveId']
            parent_item_id = files_folder_response['id']
        else:
            error_message = "Erreur : 'parentReference' n'existe pas dans la réponse de l'API."
            self.logger.log_error(error_message)
            self.error_logs["Data Format Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            drive_id = None
            parent_item_id = None

        if drive_id and parent_item_id:
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

            # Compter le nombre total de fichiers et dossiers à copier
            total_files = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
            total_folders = sum([len(dirs) for _, dirs, _ in os.walk(depot_data_directory_path)])
            size_folder_source = sum(
                [os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for
                 file in files])

            def process_file(file_path, site_id, current_parent_item_id):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                if file_size >= 1 * 1024 * 1024 * 1024:  # 1 Go
                    return self.upload_large_files(site_id, current_parent_item_id, file_path)

                file_name, status = self.upload_file_to_channel(site_id, current_parent_item_id, file_path)
                if status == "exists":
                    self.logger.log_info(f"Le fichier '{file_name}' existe déjà, il est ignoré.")
                elif status is None:
                    self.logger.log_error(f"Échec de l'upload du fichier '{file_name}'.")
                return file_name, status

            # Parcourir les fichiers et dossiers du partage réseau et les télécharger dans le canal Teams
            with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                    TextColumn("{task.completed}/{task.total} files"),
                    TextColumn("[progress.files]{task.fields[filename]}")
            ) as progress:
                task = progress.add_task("[green]Uploading files...", total=total_files, filename="")

                with ThreadPoolExecutor() as executor:
                    futures = []
                    for root, dirs, files in os.walk(depot_data_directory_path):
                        relative_path = os.path.relpath(root, depot_data_directory_path)
                        current_parent_item_id = parent_item_id

                        # Créer les dossiers dans le canal Teams
                        if relative_path != ".":
                            for folder in relative_path.split(os.sep):
                                if not self.item_exists(site_id, current_parent_item_id, folder):
                                    folder_response = self.create_folder(site_id, current_parent_item_id,
                                                                         folder)
                                    current_parent_item_id = folder_response['id']
                                else:
                                    current_parent_item_id = next(item['id'] for item in requests.get(
                                        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{current_parent_item_id}/children",
                                        headers=self.headers, proxies=self.proxies
                                    ).json()['value'] if item['name'] == folder)
                                progress.update(task, filename=f"Folder: {folder}")

                        # Télécharger les fichiers dans le canal Teams avec une barre de progression
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            futures.append(executor.submit(process_file, file_path, site_id, current_parent_item_id))
                            progress.update(task, filename=f"File: {file_name}")

                    completed_files = 0
                    for future in concurrent.futures.as_completed(futures):
                        file_name, status = future.result()
                        if status != "exists":
                            completed_files += 1
                        progress.update(task, advance=1, filename=f"File: {file_name}")

                    self.logger.log_info(f"Total des fichiers à copier : {total_files}")
                    self.logger.log_info(f"Fichiers copiés : {completed_files}")
                    self.logger.log_info(f"Fichiers restants : {total_files - completed_files}")
                    self.logger.log_info("Tous les fichiers ont été copiés avec succès.")

            return size_folder_source, total_files, total_folders, completed_files