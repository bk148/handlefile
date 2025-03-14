import os
import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.style import Style

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.console = Console()

    def create_folder(self, site_id, parent_item_id, folder_name):
        return self.graph_api.create_folder(site_id, parent_item_id, folder_name)

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        start_time = time.time()
        self.console.print("[bold green]Début du transfert de fichiers...[/bold green]")

        # Calcul du volume total et du nombre de fichiers
        total_files = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        total_volume = sum(
            [os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file in files]
        )

        # Affichage des informations initiales
        self.console.print(f"[bold]Nombre total de fichiers à transférer :[/bold] {total_files}")
        self.console.print(f"[bold]Volume total à transférer :[/bold] {total_volume / (1024 * 1024):.2f} MB")

        # Initialisation de la barre de progression
        with Progress(
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Transfert en cours...", total=total_files)

            # Appel de la méthode de transfert
            size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(
                group_id, channel_id, site_id, depot_data_directory_path
            )

            # Mise à jour de la barre de progression
            progress.update(task, completed=total_copied)

        # Calcul de la durée totale
        end_time = time.time()
        duration = end_time - start_time

        # Affichage des résultats
        self.console.print("\n[bold green]Transfert terminé ![/bold green]")
        self.console.print(f"[bold]Durée totale du transfert :[/bold] {duration:.2f} secondes")
        self.console.print(f"[bold]Fichiers transférés :[/bold] {total_copied}/{total_files}")

        # Affichage des erreurs (si elles existent)
        if any(self.graph_api.error_logs.values()):
            self.console.print("\n[bold red]Erreurs rencontrées :[/bold red]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Type d'erreur", style="dim")
            table.add_column("Détails")

            for error_type, errors in self.graph_api.error_logs.items():
                if errors:
                    table.add_row(error_type, "\n".join(errors))

            self.console.print(table)
        else:
            self.console.print("\n[bold green]Aucune erreur rencontrée.[/bold green]")

        return size_folder_source, total_files, total_folders, total_copied