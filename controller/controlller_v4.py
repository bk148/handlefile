import logging
import os
import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from concurrent.futures import ThreadPoolExecutor
from model.model_transfer import ModelGraphTransfer
from utilis.logger_v4 import MigrationLogger
from datetime import timedelta

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.console = Console()
        self.logger = MigrationLogger()

    def format_duration(self, duration_seconds):
        """Formate la durée en heures:minutes:secondes."""
        return str(timedelta(seconds=int(duration_seconds)))

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        """Orchestre le transfert des données."""
        self.logger.start_log()
        start_time = time.time()

        self.console.print("[green]Starting file transfer...[/green]")
        self.logger.logger.info(f"Starting transfer for group_id: {group_id}, channel_id: {channel_id}, site_id: {site_id}")

        # Appeler la méthode de transfert
        size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(
            group_id, channel_id, site_id, depot_data_directory_path
        )

        # Vérifier si le transfert a réussi
        if size_folder_source is None:
            self.console.print("[red]Transfer failed. Check logs for details.[/red]")
            self.logger.logger.error("Transfer failed due to an error in the API response.")
            return

        # Calculer et afficher la durée
        end_time = time.time()
        duration_seconds = end_time - start_time
        duration_formatted = self.format_duration(duration_seconds)

        # Afficher un récapitulatif
        self.console.print("\n[bold cyan]Transfer Summary:[/bold cyan]")
        self.console.print(f"  - Total files to transfer: [bold]{total_files}[/bold]")
        self.console.print(f"  - Files successfully transferred: [bold]{total_copied}[/bold]")
        self.console.print(f"  - Total folders: [bold]{total_folders}[/bold]")
        self.console.print(f"  - Total data volume: [bold]{size_folder_source / (1024 * 1024):.2f} MB[/bold]")
        self.console.print(f"  - Transfer duration: [bold]{duration_formatted}[/bold]")

        # Terminer la journalisation
        self.logger.end_log(
            size_folder_source=size_folder_source,
            total_files=total_files,
            total_folders=total_folders,
            total_contenu_copied=total_copied,
            error_logs=self.graph_api.error_logs
        )