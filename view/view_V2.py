from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.live import Live
from rich.panel import Panel

class TransferView:
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn()
        )
        self.live = Live(self.progress, refresh_per_second=10)  # Rafraîchissement toutes les 100 ms

    def display_header(self):
        """Affiche un en-tête pour le transfert."""
        self.console.print(Panel.fit("[bold green]Début du transfert de fichiers[/bold green]"))

    def display_transfer_summary(self, total_files, total_copied, duration):
        """Affiche un résumé du transfert."""
        table = Table(title="Résumé du Transfert")
        table.add_column("Statistique", justify="right", style="cyan")
        table.add_column("Valeur", style="magenta")

        table.add_row("Fichiers totaux", str(total_files))
        table.add_row("Fichiers copiés", str(total_copied))
        table.add_row("Durée (secondes)", f"{duration:.2f}")

        self.console.print(table)

    def display_error(self, error_message):
        """Affiche une erreur."""
        self.console.print(f"[red]Erreur : {error_message}[/red]")

    def start_progress(self, total_files):
        """Initialise la barre de progression."""
        self.task = self.progress.add_task("[cyan]Transfert en cours...", total=total_files)
        self.live.start()

    def update_progress(self, current):
        """Met à jour la barre de progression."""
        self.progress.update(self.task, completed=current)

    def end_progress(self):
        """Termine la barre de progression."""
        self.live.stop()
        self.console.print("[bold green]Transfert terminé ![/bold green]")