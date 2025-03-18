# controller.py
import os
import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from concurrent.futures import ThreadPoolExecutor

from apiAuthenfication.msgraphAuth import TokenGenerator
from settings.config import app_id, client_secret, tenant_id, scopes, proxy
from model.model_transfer import ModelGraphTransfer
from utilis.logger import MigrationLogger

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.console = Console()
        self.logger = MigrationLogger()

    def create_folder(self, site_id, parent_item_id, folder_name):
        return self.graph_api.create_folder(site_id, parent_item_id, folder_name)

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        self.logger.start_log()
        start_time = time.time()

        self.console.print("[green]Starting file transfer...[/green]")
        total_initial = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        total_volume = sum(
            [os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file in files])

        size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(group_id, channel_id, site_id, depot_data_directory_path)

        end_time = time.time()
        duration = end_time - start_time
        self.console.print(f"[blue]Total transfer duration: {duration:.2f} seconds[/blue]")

        self.logger.end_log(size_folder_source=size_folder_source, total_files=total_files, total_folders=total_folders, total_contenu_copied=total_copied, error_logs=self.graph_api.error_logs)

        # Affichage des statistiques avec Rich
        table = Table(title="Migration Statistics")
        table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        table.add_row("Total Files", str(total_files))
        table.add_row("Total Folders", str(total_folders))
        table.add_row("Files Copied", str(total_copied))
        table.add_row("Total Volume", f"{total_volume / (1024 * 1024):.2f} MB")
        table.add_row("Duration", f"{duration:.2f} seconds")

        self.console.print(table)