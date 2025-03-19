def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path, group_name=None, channel_name=None):
    """
    Transfère un dossier entier vers un canal Teams.
    :param group_id: ID du groupe Teams.
    :param channel_id: ID du canal Teams.
    :param site_id: ID du site SharePoint.
    :param depot_data_directory_path: Chemin du dossier local à transférer.
    :param group_name: Nom du groupe Teams (optionnel).
    :param channel_name: Nom du canal Teams (optionnel).
    """
    # Démarrer la mesure du temps et la journalisation
    self.logger.log_general_event(
        f"Début du transfert pour le groupe '{group_name}' (ID: {group_id}), "
        f"canal '{channel_name}' (ID: {channel_id}), site ID: {site_id}."
    )
    start_time = time.time()

    self.console.print(f"[green]Début du transfert pour le groupe '{group_name}'...[/green]")

    # Calculer le nombre total de fichiers et le volume des données
    total_initial = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
    total_volume = sum([os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file in files])

    self.logger.log_general_event(f"Total des fichiers à transférer: {total_initial}")
    self.logger.log_general_event(f"Volume total des données: {total_volume / (1024 * 1024):.2f} MB")

    # Démarrer le transfert
    size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(
        group_id, channel_id, site_id, depot_data_directory_path, group_name, channel_name
    )

    # Calculer et afficher la durée
    end_time = time.time()
    duration = end_time - start_time
    self.console.print(f"[blue]Durée totale du transfert: {duration:.2f} secondes[/blue]")
    self.logger.log_general_event(f"Durée totale du transfert: {duration:.2f} secondes")

    # Terminer la journalisation
    self.logger.log_general_event(
        f"Transfert terminé pour le groupe '{group_name}' (ID: {group_id}), "
        f"canal '{channel_name}' (ID: {channel_id}). "
        f"Fichiers copiés: {total_copied}, Erreurs: {len(self.graph_api.error_logs)}"
    )
    self.logger.log_general_event(f"Taille du dossier source: {size_folder_source / (1024 * 1024):.2f} MB")
    self.logger.log_general_event(f"Total des fichiers: {total_files}")
    self.logger.log_general_event(f"Total des dossiers: {total_folders}")