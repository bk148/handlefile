import os
import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from concurrent.futures import ThreadPoolExecutor

from apiAuthenfication.msgraphAuth import TokenGenerator
from settings.config import app_id, client_secret, tenant_id, scopes, proxy
from model.model_transfer import ModelGraphTransfer
from utilis.logger import MigrationLogger  # Assure-toi d'importer la classe MigrationLogger


class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.console = Console()
        self.logger = MigrationLogger()

    def create_folder(self, site_id, parent_item_id, folder_name):
        return self.graph_api.create_folder(site_id, parent_item_id, folder_name)

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        # Démarrer la mesure du temps et la journalisation
        self.logger.start_log()
        start_time = time.time()

        self.console.print("[green]Starting file transfer...[/green]")
        total_initial = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        total_volume = sum(
            [os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file in files])

        # Configuration de la barre de progression
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            TextColumn("{task.completed}/{task.total} files"),
            TextColumn("[cyan]{task.fields[filename]}[/cyan]"),
            TextColumn("[yellow]{task.fields[file_type]}[/yellow]"),
            TextColumn("[magenta]{task.fields[file_size]}[/magenta]"),
        ) as progress:
            task = progress.add_task(
                "[green]Uploading files...[/green]",
                total=total_initial,
                filename="",
                file_type="",
                file_size=""
            )

            # Fonction pour intercepter les messages de téléchargement
            def process_file(file_path, site_id, current_parent_item_id):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_size_mb = f"{file_size / (1024 * 1024):.2f} MB"

                # Mettre à jour la barre de progression avec les détails du fichier
                progress.update(
                    task,
                    filename=file_name,
                    file_type="Large File" if file_size > 4 * 1024 * 1024 else "Normal File",
                    file_size=file_size_mb
                )

                # Appeler la méthode de téléchargement de ModelGraphTransfer
                result = self.graph_api.upload_file_to_channel(site_id, current_parent_item_id, file_path)
                return result

            # Appeler la méthode de ModelGraphTransfer avec les paramètres appropriés
            size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(
                group_id, channel_id, site_id, depot_data_directory_path
            )

        # Calculer et afficher la durée
        end_time = time.time()
        duration = end_time - start_time
        self.console.print(f"[blue]Total transfer duration: {duration:.2f} seconds[/blue]")

        # Afficher un résumé final
        self.console.print("\n[bold]Migration Summary:[/bold]")
        self.console.print(f"[green]Total files copied: {total_copied}[/green]")
        self.console.print(f"[yellow]Total files ignored (already exist): {total_files - total_copied}[/yellow]")
        self.console.print(f"[red]Total errors: {sum(len(errors) for errors in self.graph_api.error_logs.values())}[/red]")

        # Terminer la journalisation
        self.logger.end_log(
            size_folder_source=size_folder_source,
            total_files=total_files,
            total_folders=total_folders,
            total_contenu_copied=total_copied,
            error_logs=self.graph_api.error_logs
        )