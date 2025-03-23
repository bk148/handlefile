import os
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential
from logger import TransferLogger

console = Console()

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
        # Initialiser le nouveau logger
        self.logger = TransferLogger()

    def refresh_token(self):
        """Rafraîchit le token et met à jour les en-têtes."""
        self.access_token = self.token_generator.get_valid_token()
        self.headers['Authorization'] = f'Bearer {self.access_token}'

    def get_channel_files_folder(self, group_id, channel_id):
        """Récupère le dossier de fichiers du canal."""
        self.refresh_token()
        url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.log_failure(f"Group ID: {group_id}, Channel ID: {channel_id}", str(e))
            self.error_logs["Connection Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
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
            self.logger.log_failure(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}", str(e))
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
            self.logger.log_success(f"Dossier: {folder_name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.log_failure(f"Dossier: {folder_name}", str(e))
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        """Télécharge un fichier vers le canal Teams."""
        self.refresh_token()
        file_name = os.path.basename(file_path)
        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                self.logger.log_success(file_path)  # Enregistrer le succès
                return file_name, response.status_code
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:  # Token expiré
                self.refresh_token()
                return self.upload_file_to_channel(site_id, parent_item_id, file_path)  # Réessayer
            else:
                self.logger.log_failure(file_path, str(e))  # Enregistrer l'échec
                self.error_logs["File Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
                return file_name, None

    def upload_large_files(self, site_id, parent_item_id, file_path, progress, main_task):
        """Télécharge un fichier volumineux en morceaux avec une barre de progression."""
        self.refresh_token()
        file_name = os.path.basename(file_path)
        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/createUploadSession"

        try:
            # Créer une session d'upload
            response = requests.post(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            upload_url = response.json().get('uploadUrl')

            # Télécharger le fichier en morceaux avec une barre de progression
            chunk_size = 20 * 1024 * 1024  # 20 MB
            file_size = os.path.getsize(file_path)

            # Ajouter une sous-tâche pour le fichier volumineux
            file_task = progress.add_task(f"[cyan]Uploading {file_name}...", total=file_size)

            with open(file_path, 'rb') as file:
                for i in range(0, file_size, chunk_size):
                    chunk_data = file.read(chunk_size)
                    chunk_headers = {
                        'Content-Length': str(len(chunk_data)),
                        'Content-Range': f'bytes {i}-{i + len(chunk_data) - 1}/{file_size}'
                    }
                    chunk_response = requests.put(upload_url, headers=chunk_headers, data=chunk_data,
                                                  proxies=self.proxies)
                    chunk_response.raise_for_status()
                    progress.update(file_task, advance=len(chunk_data))  # Mettre à jour la barre de progression

            progress.remove_task(file_task)  # Supprimer la sous-tâche une fois terminée
            self.logger.log_success(file_path)
            return file_name, "uploaded"
        except requests.exceptions.RequestException as e:
            self.logger.log_failure(file_path, str(e))
            self.error_logs["File Error"].append(
                f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        """Transfère un dossier entier vers le canal Teams."""
        console.print(f"Starting transfer for group_id: {group_id}, channel_id: {channel_id}, site_id: {site_id}")
        files_folder_response = self.get_channel_files_folder(group_id, channel_id)

        if 'parentReference' not in files_folder_response:
            self.logger.log_failure("Dossier racine", "'parentReference' non trouvé dans la réponse de l'API")
            self.error_logs["Data Format Error"].append(f"Group ID: {group_id}, Channel ID: {channel_id}")
            return None, None, None, None

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

        # Compter le nombre total de fichiers
        total_files = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        total_folders = sum([len(dirs) for _, dirs, _ in os.walk(depot_data_directory_path)])
        size_folder_source = sum(
            [os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file
             in files]
        )

        # Barre de progression globale
        with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TextColumn("{task.completed}/{task.total} files"),
                TimeRemainingColumn()
        ) as progress:
            main_task = progress.add_task("[green]Uploading files...", total=total_files)

            # Utiliser ThreadPoolExecutor pour le téléchargement parallèle
            with ThreadPoolExecutor(max_workers=10) as executor:  # 10 threads en parallèle
                futures = []
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

                    # Télécharger les fichiers en parallèle
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        file_size = os.path.getsize(file_path)
                        if file_size >= 1 * 1024 * 1024 * 1024:  # 1 Go
                            console.print(
                                f"[yellow]Fichier volumineux détecté : {file_name} (taille : {file_size / (1024 * 1024):.2f} MB). Utilisation de upload_large_files...[/yellow]")
                            futures.append(
                                executor.submit(self.upload_large_files, site_id, current_parent_item_id, file_path,
                                                progress, main_task))
                        else:
                            futures.append(executor.submit(self.upload_file_to_channel, site_id, current_parent_item_id,
                                                           file_path))
                        progress.update(main_task, advance=1, description=f"Uploading {file_name}")

                # Attendre la fin de tous les téléchargements
                total_copied = 0
                for future in as_completed(futures):
                    result = future.result()
                    if result and result[1] not in [None, "exists"]:
                        total_copied += 1

        console.print("Transfer completed successfully.")
        return size_folder_source, total_files, total_folders, total_copied