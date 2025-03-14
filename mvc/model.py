def upload_file_to_channel(self, site_id, parent_item_id, file_path):
    file_name = os.path.basename(file_path)
    if self.item_exists(site_id, parent_item_id, file_name):
        return file_name, "exists"

    file_size = os.path.getsize(file_path)
    if file_size > 4 * 1024 * 1024:  # Si le fichier est supérieur à 4 Mo
        return self.upload_large_file(site_id, parent_item_id, file_path, file_name)

    # Encodage du nom de fichier pour l'URL
    encoded_file_name = quote(file_name)
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
        total_folders = sum([len(dirs) for _, dirs, _ in os.walk(depot_data_directory_path)])
        size_folder_source = sum(
            [os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file
             in files])

        def process_file(file_path, site_id, current_parent_item_id):
            # Appel unique à upload_file_to_channel, qui gère la logique de taille de fichier
            return self.upload_file_to_channel(site_id, current_parent_item_id, file_path)

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
                            progress.update(task, filename=f"Folder: {folder}")

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

                print(f"Total files to copy: {total_files}")
                print(f"Files copied: {completed_files}")
                print(f"Remaining files: {total_files - completed_files}")
                print("Success: All files have been copied successfully!")

        return size_folder_source, total_files, total_folders, completed_files