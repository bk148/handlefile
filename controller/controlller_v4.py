import os
import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy, logger):
        self.graph_api = ModelGraphTransfer(token_generator, proxy, logger)
        self.console = Console()
        self.logger = logger

    def create_folder(self, site_id, parent_item_id, folder_name):
        return self.graph_api.create_folder(site_id, parent_item_id, folder_name)

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        # Démarrer la mesure du temps et la journalisation
        self.logger.log_general_event(f"Début du transfert pour Group ID: {group_id}, Channel ID: {channel_id}, Site ID: {site_id}")
        start_time = time.time()

        self.console.print("[green]Starting file transfer...[/green]")

        total_initial = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        total_volume = sum([os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file in files])

        self.logger.log_general_event(f"Total des fichiers à transférer: {total_initial}")
        self.logger.log_general_event(f"Volume total des données: {total_volume / (1024 * 1024):.2f} MB")

        size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(group_id, channel_id, site_id, depot_data_directory_path)

        # Calculer et afficher la durée
        end_time = time.time()
        duration = end_time - start_time
        self.logger.log_general_event(f"Durée totale du transfert: {duration:.2f} secondes")

        # Terminer la journalisation
        self.logger.log_general_event(f"Transfert terminé. Fichiers copiés: {total_copied}, Erreurs: {len(self.graph_api.error_logs)}")