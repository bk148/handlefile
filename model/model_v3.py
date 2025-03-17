import os
import logging
from urllib.parse import quote
from graph_api_client import GraphAPIClient

class ModelGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = GraphAPIClient(token_generator, proxy)
        self.logger = logging.getLogger(__name__)
        self.error_loggers = {
            "Connection Error": logging.getLogger("Connection Error"),
            "Authentication Error": logging.getLogger("Authentication Error"),
            "Data Format Error": logging.getLogger("Data Format Error"),
            "Access Rights Error": logging.getLogger("Access Rights Error"),
            "Network Error": logging.getLogger("Network Error"),
            "Quota Error": logging.getLogger("Quota Error"),
            "File Error": logging.getLogger("File Error"),
            "Cyclic Redundancy Error": logging.getLogger("Cyclic Redundancy Error"),
            "Ignored Files": logging.getLogger("Ignored Files")
        }

    def _log_error(self, category, message):
        """Log une erreur dans la catégorie spécifiée."""
        if category in self.error_loggers:
            self.error_loggers[category].error(message)
        else:
            self.logger.error(f"Catégorie d'erreur inconnue : {category}. Message : {message}")

    def get_channel_files_folder(self, group_id, channel_id):
        """Récupère le dossier de fichiers associé à un canal Teams."""
        url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
        try:
            response = self.graph_api.get(url)
            self.logger.info(f"Récupération du dossier de fichiers pour group_id={group_id}, channel_id={channel_id}")
            return response
        except requests.exceptions.RequestException as e:
            self._log_error("Connection Error", f"Erreur de connexion : {e}")
            raise

    def item_exists(self, site_id, parent_item_id, item_name):
        """Vérifie si un fichier ou dossier existe déjà."""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        try:
            items = self.graph_api.get(url).get('value', [])
            return any(item['name'] == item_name for item in items)
        except requests.exceptions.RequestException as e:
            self._log_error("Connection Error", f"Erreur de connexion : {e}")
            raise

    def create_folder(self, site_id, parent_item_id, folder_name):
        """Crée un dossier dans un site SharePoint."""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'
        }
        try:
            response = self.graph_api.post(url, data)
            self.logger.info(f"Création du dossier : site_id={site_id}, parent_item_id={parent_item_id}, folder_name={folder_name}")
            return response
        except requests.exceptions.RequestException as e:
            self._log_error("File Error", f"Erreur lors de la création du dossier : {e}")
            raise

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        """Télécharge un fichier dans un canal Teams."""
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            self._log_error("Ignored Files", f"Le fichier existe déjà : {file_name}")
            return file_name, "exists"

        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                self.logger.info(f"Téléversement du fichier : {file_name}")
                self.graph_api.put(url, file.read())
                return file_name, "uploaded"
        except Exception as e:
            self._log_error("File Error", f"Erreur lors du téléversement du fichier {file_name}: {e}")
            raise

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        """Transfère un dossier entier vers un canal Teams."""
        try:
            files_folder_response = self.get_channel_files_folder(group_id, channel_id)
            if 'parentReference' not in files_folder_response:
                self._log_error("Data Format Error", "Erreur : 'parentReference' absent dans la réponse de l'API.")
                raise ValueError("Invalid API response")

            drive_id = files_folder_response['parentReference']['driveId']
            parent_item_id = files_folder_response['id']

            folder_name = os.path.basename(depot_data_directory_path)
            if not self.item_exists(site_id, parent_item_id, folder_name):
                folder_response = self.create_folder(site_id, parent_item_id, folder_name)
                parent_item_id = folder_response['id']

            total_files = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
            completed_files = 0

            for root, dirs, files in os.walk(depot_data_directory_path):
                relative_path = os.path.relpath(root, depot_data_directory_path)
                current_parent_item_id = parent_item_id

                if relative_path != ".":
                    for folder in relative_path.split(os.sep):
                        if not self.item_exists(site_id, current_parent_item_id, folder):
                            folder_response = self.create_folder(site_id, current_parent_item_id, folder)
                            current_parent_item_id = folder_response['id']

                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_name, status = self.upload_file_to_channel(site_id, current_parent_item_id, file_path)
                    if status != "exists":
                        completed_files += 1

            self.logger.info(f"Transfert terminé : {completed_files}/{total_files} fichiers copiés.")
            return completed_files, total_files
        except Exception as e:
            self._log_error("Network Error", f"Erreur réseau lors du transfert : {e}")
            raise