import os
import requests
import logging
from urllib.parse import quote

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
        self.transferred_files = []

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
            self.error_logs["Connection Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, Folder Name: {folder_name}")
            return None

    def upload_file_to_channel(self, site_id, parent_item_id, file_path):
        file_name = os.path.basename(file_path)
        if self.item_exists(site_id, parent_item_id, file_name):
            self.transferred_files.append((file_name, "exists"))
            return file_name, "exists"

        encoded_file_name = quote(file_name, safe='')
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{parent_item_id}:/{encoded_file_name}:/content"
        try:
            with open(file_path, 'rb') as file:
                response = requests.put(url, headers=self.headers, data=file, proxies=self.proxies)
                response.raise_for_status()
                self.transferred_files.append((file_name, "success"))
                return file_name, response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading file: {e}")
            self.error_logs["File Error"].append(f"Site ID: {site_id}, Parent Item ID: {parent_item_id}, File Path: {file_path}")
            self.transferred_files.append((file_name, "error"))
            return file_name, None

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
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
                    file_name, status = self.upload_file_to_channel(site_id, current_parent_item_id, file_path)
                    if status != "exists":
                        completed_files += 1

            return completed_files, total_files