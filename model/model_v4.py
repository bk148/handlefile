import os
import requests
from urllib.parse import quote

class ModelGraphTransfer:
    def __init__(self, token_generator, proxy, logger):
        self.token_generator = token_generator
        self.proxy = proxy
        self.access_token = self.token_generator.generate_access_token()['access_token']
        self.headers = {'Authorization': f'Bearer {self.access_token}'}
        self.proxies = {'http': self.proxy, 'https': self.proxy}
        self.logger = logger
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
            self.logger.log_network_success("Dossier de fichiers récupéré avec succès.", status_code=response.status_code, url=url)
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.log_network_error(f"Erreur lors de la récupération du dossier de fichiers: {e}", status_code=response.status_code if 'response' in locals() else None, url=url)
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
                    self.logger.log_general_event(f"L'élément {item_name} existe déjà.")
                    return True
            return False
        except requests.exceptions.RequestException as e:
            self.logger.log_network_error(f"Erreur lors de la vérification de l'existence de l'élément: {e}", status_code=response.status_code if 'response' in locals() else None, url=url)
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
            self.logger.log_success(f"Dossier {folder_name} créé avec succès.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.log_file_error(f"Erreur lors de la création du dossier {folder_name}.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Erreur: {e}")
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        file_name = os.path.basename(file_path)

        if self.item_exists(site_id, parent_item_id, file_name):
            self.logger.log_general_event(f"Le fichier {file_name} existe déjà. Aucune action nécessaire.")
            return file_name, "exists"

        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                self.logger.log_success(f"Fichier {file_name} téléchargé avec succès.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}")
                return file_name, response.status_code
        except requests.exceptions.RequestException as e:
            self.logger.log_file_error(f"Erreur lors du téléchargement du fichier {file_name}.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Erreur: {e}")
            self.error_logs["File Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
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

            self.logger.log_success(f"Fichier volumineux {file_name} téléchargé avec succès.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}")
            return file_name, "uploaded"
        except requests.exceptions.RequestException as e:
            self.logger.log_file_error(f"Erreur lors du téléchargement du fichier volumineux {file_name}.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Erreur: {e}")
            self.error_logs["File Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            return file_name, None

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path, group_name=None,
                                        channel_name=None):
        """
        Transfère un dossier entier vers un canal Teams.
        :param group_id: ID du groupe Teams.
        :param channel_id: ID du canal Teams.
        :param site_id: ID du site SharePoint.
        :param depot_data_directory_path: Chemin du dossier local à transférer.
        :param group_name: Nom du groupe Teams (optionnel).
        :param channel_name: Nom du canal Teams (optionnel).
        :return: Tuple contenant la taille du dossier source, le nombre total de fichiers, le nombre total de dossiers, et le nombre de fichiers copiés.
        """
        self.logger.log_general_event(
            f"Début du transfert du dossier '{depot_data_directory_path}' vers le canal '{channel_name}' (ID: {channel_id}) "
            f"dans le groupe '{group_name}' (ID: {group_id})."
        )

        total_files = 0
        total_folders = 0
        total_copied = 0
        size_folder_source = 0

        try:
            # Récupérer le dossier de fichiers du canal
            folder_info = self.get_channel_files_folder(group_id, channel_id)
            if not folder_info:
                self.logger.log_file_error(
                    "Impossible de récupérer le dossier de fichiers du canal.",
                    context=f"Groupe '{group_name}' (ID: {group_id}), Canal '{channel_name}' (ID: {channel_id})"
                )
                return size_folder_source, total_files, total_folders, total_copied

            parent_item_id = folder_info.get('id')
            if not parent_item_id:
                self.logger.log_file_error(
                    "ID du dossier parent introuvable.",
                    context=f"Groupe '{group_name}' (ID: {group_id}), Canal '{channel_name}' (ID: {channel_id})"
                )
                return size_folder_source, total_files, total_folders, total_copied

            # Parcourir le dossier local
            for root, dirs, files in os.walk(depot_data_directory_path):
                # Créer les dossiers dans le canal
                relative_path = os.path.relpath(root, depot_data_directory_path)
                if relative_path != ".":
                    folder_name = os.path.basename(relative_path)
                    if not self.item_exists(site_id, parent_item_id, folder_name):
                        self.create_folder(site_id, parent_item_id, folder_name)
                        self.logger.log_success(
                            f"Dossier '{folder_name}' créé avec succès.",
                            context=f"Groupe '{group_name}' (ID: {group_id}), Canal '{channel_name}' (ID: {channel_id})"
                        )
                    total_folders += 1

                # Télécharger les fichiers
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    size_folder_source += file_size

                    # Télécharger le fichier
                    result = self.upload_file_to_channel(site_id, parent_item_id, file_path)
                    if result[1] == "exists":
                        self.logger.log_general_event(f"Le fichier '{file}' existe déjà. Ignoré.")
                    elif result[1]:
                        self.logger.log_success(
                            f"Fichier '{file}' téléchargé avec succès.",
                            context=f"Groupe '{group_name}' (ID: {group_id}), Canal '{channel_name}' (ID: {channel_id})"
                        )
                        total_copied += 1
                    else:
                        self.logger.log_file_error(
                            f"Échec du téléchargement du fichier '{file}'.",
                            context=f"Groupe '{group_name}' (ID: {group_id}), Canal '{channel_name}' (ID: {channel_id})"
                        )

                    total_files += 1

            self.logger.log_general_event(
                f"Transfert du dossier '{depot_data_directory_path}' terminé. "
                f"Fichiers copiés: {total_copied}/{total_files}"
            )
            return size_folder_source, total_files, total_folders, total_copied

        except Exception as e:
            self.logger.log_file_error(
                f"Erreur lors du transfert du dossier '{depot_data_directory_path}'.",
                context=f"Groupe '{group_name}' (ID: {group_id}), Canal '{channel_name}' (ID: {channel_id}), Erreur: {e}"
            )
            return size_folder_source, total_files, total_folders, total_copied