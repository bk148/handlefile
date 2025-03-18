from rich.console import Console
from rich.table import Table
from rich import box
import time

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.console = Console()
        self.logger = MigrationLogger()

    def format_duration(self, duration_seconds):
        """Formate la durée en secondes en heures, minutes et secondes (HH:MM:SS)."""
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        # Démarrer la journalisation
        self.logger.start_log()
        start_time = time.time()

        self.console.print("[green]Début du transfert de fichiers...[/green]")
        self.logger.log_info("Début du transfert de fichiers.")

        # Appeler la méthode de transfert de données
        size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(
            group_id, channel_id, site_id, depot_data_directory_path
        )

        # Calculer et afficher la durée
        end_time = time.time()
        duration_seconds = end_time - start_time
        formatted_duration = self.format_duration(duration_seconds)
        self.console.print(f"[blue]Durée totale du transfert : {formatted_duration}[/blue]")
        self.logger.log_info(f"Durée totale du transfert : {formatted_duration}.")

        # Calculer le nombre de fichiers en erreur et ignorés
        total_errors = sum(len(errors) for errors in self.graph_api.error_logs.values())
        total_ignored = len(self.graph_api.error_logs["Ignored Files"])

        # Afficher un tableau récapitulatif
        table = Table(title="Récapitulatif du Transfert", box=box.ROUNDED)
        table.add_column("Statistique", justify="left", style="cyan")
        table.add_column("Valeur", justify="right", style="magenta")

        table.add_row("Durée totale du transfert", formatted_duration)
        table.add_row("Nombre total de fichiers", str(total_files))
        table.add_row("Fichiers copiés avec succès", str(total_copied))
        table.add_row("Fichiers en erreur", str(total_errors))
        table.add_row("Fichiers ignorés (déjà existants)", str(total_ignored))
        table.add_row("Taille totale des fichiers", f"{size_folder_source / (1024 * 1024):.2f} Mo")

        self.console.print(table)

        # Terminer la journalisation
        self.logger.end_log(
            size_folder_source=size_folder_source,
            total_files=total_files,
            total_folders=total_folders,
            total_contenu_copied=total_copied,
            error_logs=self.graph_api.error_logs
        )