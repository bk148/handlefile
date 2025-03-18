import os
import requests
import logging
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, TextColumn, BarColumn

from utilis.logging import MigrationLogger


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
        try:
            url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            self.logger.log_info(f"Récupération réussie du dossier de fichiers pour le groupe {group_id}, canal {channel_id}.")
            return response.json()
        except requests.exceptions.RequestException as e:
            error_message = f"Erreur lors de la récupération du dossier de fichiers : {e}"
            self.logger.log_error(error_message)
            self.error_logs["Connection Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            return None

    # Ajoutez des logs similaires pour les autres méthodes...

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
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        file_name = os.path.basename(file_path)

        if self.item_exists(site_id, parent_item_id, file_name):
            return file_name, "exists"
        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                return file_name, response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading file: {e}")
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

            # Taille du fichier et taille des chunks
            file_size = os.path.getsize(file_path)
            chunk_size = 50 * 1024 * 1024  # 50 MB (augmenté pour optimiser la vitesse)
            buffer_size = 10 * 1024 * 1024  # 10 MB (taille du buffer de lecture)

            # Initialiser la barre de progression
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TextColumn("[blue]{task.completed}/{task.total} MB[/blue]"),
            ) as progress:
                task = progress.add_task(f"[cyan]Uploading {file_name}...", total=file_size // (1024 * 1024))  # Taille en MB

                # Fonction pour uploader un chunk
                def upload_chunk(start, end, chunk_data):
                    chunk_headers = {
                        'Content-Length': str(len(chunk_data)),
                        'Content-Range': f'bytes {start}-{end - 1}/{file_size}'
                    }
                    for _ in range(3):  # 3 tentatives en cas d'échec
                        try:
                            response = requests.put(upload_url, headers=chunk_headers, data=chunk_data,
                                                  proxies=self.proxies)
                            response.raise_for_status()
                            return True
                        except requests.exceptions.RequestException as e:
                            logging.warning(f"Retrying chunk {start}-{end}: {e}")
                    return False

                # Lire et uploader les chunks en parallèle
                with ThreadPoolExecutor(max_workers=4) as executor:  # 4 threads pour l'upload parallèle
                    futures = []
                    with open(file_path, 'rb', buffering=buffer_size) as file:
                        for start in range(0, file_size, chunk_size):
                            end = min(start + chunk_size, file_size)
                            file.seek(start)
                            chunk_data = file.read(end - start)
                            futures.append(executor.submit(upload_chunk, start, end, chunk_data))

                    # Suivre la progression
                    for future in as_completed(futures):
                        if not future.result():
                            raise Exception("Failed to upload a chunk after multiple retries.")
                        progress.update(task, advance=chunk_size // (1024 * 1024))  # Avancer en MB

            logging.info(f"Large file {file_name} uploaded successfully.")
            return file_name, "uploaded"
        except Exception as e:
            logging.error(f"Error uploading large file: {e}")
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
            logging.error("Error: 'parentReference' does not exist in the API response.")
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
                    logging.info(f"File {file_name} already exists, skipping.")
                elif status is None:
                    logging.error(f"Failed to upload file {file_name}.")
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
                    for future in as_completed(futures):
                        file_name, status = future.result()
                        if status != "exists":
                            completed_files += 1
                        progress.update(task, advance=1, filename=f"File: {file_name}")

                    print(f"Total files to copy: {total_files}")
                    print(f"Files copied: {completed_files}")
                    print(f"Remaining files: {total_files - completed_files}")
                    print("Success: All files have been copied successfully!")

            return size_folder_source, total_files, total_folders, completed_files