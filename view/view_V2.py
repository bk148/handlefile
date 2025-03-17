from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.live import Live
from rich.panel import Panel

class TransferView:
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        self.live = Live(auto_refresh=False)

    def display_header(self):
        self.console.print(Panel.fit("[bold green]Début du transfert de fichiers[/bold green]"))

    def display_transfer_summary(self, total_files, total_copied, duration):
        table = Table(title="Résumé du Transfert")
        table.add_column("Statistique", justify="right", style="cyan")
        table.add_column("Valeur", style="magenta")

        table.add_row("Fichiers totaux", str(total_files))
        table.add_row("Fichiers copiés", str(total_copied))
        table.add_row("Durée (secondes)", f"{duration:.2f}")

        self.console.print(table)

    def display_error(self, error_message):
        self.console.print(f"[red]Erreur : {error_message}[/red]")

    def start_progress(self, total_files):
        self.task = self.progress.add_task("[cyan]Transfert en cours...", total=total_files)
        self.live.start()

    def update_progress(self, current):
        self.progress.update(self.task, completed=current)
        self.live.update(self.progress)

    def end_progress(self):
        self.live.stop()
        self.console.print("[bold green]Transfert terminé ![/bold green]")