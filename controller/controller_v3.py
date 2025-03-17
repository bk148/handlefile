from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table
from model.model_transfer import ModelGraphTransfer

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.console = Console()

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        # Démarrer la barre de progression
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )

        # Compter le nombre total de fichiers
        total_files = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])

        # Démarrer la progression
        with progress:
            task = progress.add_task("[cyan]Transferring files...", total=total_files)

            # Logique de transfert
            completed_files = 0
            for root, dirs, files in os.walk(depot_data_directory_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        file_name, status = self.graph_api.upload_file_to_channel(site_id, parent_item_id, file_path)
                        if status != "exists":
                            completed_files += 1
                            progress.update(task, advance=1, description=f"Copying {file_name}")
                    except Exception as e:
                        self.console.print(f"[red]Error copying {file_name}: {e}[/red]")

        # Afficher un tableau récapitulatif
        self.console.print("\n[bold green]Transfer Summary[/bold green]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Statistic", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Total Files", str(total_files))
        table.add_row("Files Copied", str(completed_files))
        table.add_row("Files Ignored", str(total_files - completed_files))

        self.console.print(table)