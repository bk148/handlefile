import os
import logging
from urllib.parse import quote
from graph_api_client import GraphAPIClient

class ModelGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = GraphAPIClient(token_generator, proxy)
        self.logger = logging.getLogger(__name__)

    def _validate_ids(self, group_id, channel_id, site_id):
        """Valide les IDs de groupe, canal et site."""
        if not all([group_id, channel_id, site_id]):
            raise ValueError("Les IDs de groupe, canal et site sont requis.")
        # Ajouter d'autres validations si nécessaire (ex : format des IDs)

    def get_channel_files_folder(self, group_id, channel_id):
        """Récupère le dossier de fichiers associé à un canal Teams."""
        self._validate_ids(group_id, channel_id, "dummy_site_id")  # Validation des IDs
        url = f"https://graph.microsoft.com/v1.0/teams/{group_id}/channels/{channel_id}/filesFolder"
        return self.graph_api.get(url)

    def item_exists(self, site_id, parent_item_id, item_name):
        """Vérifie si un fichier ou dossier existe déjà."""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        items = self.graph_api.get(url).get('value', [])
        return any(item['name'] == item_name for item in items)

    def create_folder(self, site_id, parent_item_id, folder_name):
        """Crée un dossier dans un site SharePoint."""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}/children"
        data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'
        }
        return self.graph_api.post(url, data)

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        """Télécharge un fichier dans un canal Teams."""
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            return file_name, "exists"

        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                self.graph_api.put(url, file.read())
                return file_name, "uploaded"
        except Exception as e:
            self.logger.error(f"Error uploading file: {e}")
            raise

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        """Transfère un dossier entier vers un canal Teams."""
        self._validate_ids(group_id, channel_id, site_id)  # Validation des IDs
        files_folder_response = self.get_channel_files_folder(group_id, channel_id)

        if 'parentReference' not in files_folder_response:
            self.logger.error("Error: 'parentReference' does not exist in the API response.")
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

        return completed_files, total_files