import logging
import os
import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from concurrent.futures import ThreadPoolExecutor
from model.model_transfer import ModelGraphTransfer
from utilis.logger_v4 import MigrationLogger

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.console = Console()
        self.logger = MigrationLogger()

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        """Orchestre le transfert des données."""
        self.logger.start_log()
        start_time = time.time()

        self.console.print("[green]Starting file transfer...[/green]")
        self.logger.logger.info(f"Starting transfer for group_id: {group_id}, channel_id: {channel_id}, site_id: {site_id}")

        total_initial = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        total_volume = sum(
            [os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file in files])

        self.logger.logger.info(f"Total files to transfer: {total_initial}")
        self.logger.logger.info(f"Total data volume: {total_volume / (1024 * 1024):.2f} MB")

        size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(group_id, channel_id, site_id, depot_data_directory_path)

        # Calculer et afficher la durée
        end_time = time.time()
        duration = end_time - start_time
        self.console.print(f"[blue]Total transfer duration: {duration:.2f} seconds[/blue]")

        # Terminer la journalisation
        self.logger.end_log(size_folder_source=size_folder_source, total_files=total_files, total_folders=total_folders, total_contenu_copied=total_copied, error_logs=self.graph_api.error_logs)