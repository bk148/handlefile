from rich.console import Console
from rich.progress import (
    Progress, BarColumn, TextColumn,
    TimeRemainingColumn, TransferSpeedColumn
)
from rich.table import Table
from rich.markdown import Markdown
import logging
import time


class TransferView:
    """Classe de vue pour gérer l'affichage et la journalisation"""

    def __init__(self):
        self.console = Console()
        self.progress = None
        self._init_logging()

    def _init_logging(self):
        """Initialiser la journalisation dans des fichiers"""
        self.logger = logging.getLogger('migration_view')
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Fichier de log principal
        file_handler = logging.FileHandler('migration_full.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Fichier d'erreurs
        error_handler = logging.FileHandler('migration_errors.log')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

    def show_section_header(self, title):
        """Afficher un en-tête de section"""
        self.console.print(f"\n[bold cyan]{'=' * 50}")
        self.console.print(f"[bold white]{title.center(50)}")
        self.console.print(f"[cyan]{'=' * 50}\n")

    def show_progress_start(self, total_files, total_size):
        """Démarrer l'affichage de la progression"""
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            TransferSpeedColumn(),
            console=self.console
        )
        self.main_task = self.progress.add_task(
            "[green]Migration en cours...",
            total=total_size
        )
        self.progress.start()

    def show_progress_update(self, stats):
        """Mettre à jour la progression"""
        self.progress.update(
            self.main_task,
            completed=stats['transferred'],
            total=stats['total_size']
        )

    def show_final_report(self, stats):
        """Afficher le rapport final"""
        table = Table(title="Rapport de Migration", show_header=True)
        table.add_column("Fichiers", justify="right")
        table.add_column("Volume", justify="right")
        table.add_column("Succès", justify="right")
        table.add_column("Erreurs", justify="right")

        table.add_row(
            str(stats['total_files']),
            f"{stats['total_size'] / 1024 / 1024:.2f} MB",
            f"[green]{stats['transferred']}",
            f"[red]{stats['errors']}"
        )

        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n[bold]Journal complet disponible dans migration_full.log")

    def log_error(self, message):
        """Journaliser une erreur"""
        self.logger.error(message)
        self.console.print(f"[red]Erreur:[/red] {message}")

    def log_critical_error(self, message):
        """Journaliser une erreur critique"""
        self.logger.critical(message)
        self.console.print(f"[bold red]ERREUR CRITIQUE:[/bold red] {message}")
        self.console.print("Veuillez vérifier les logs pour plus de détails")

    def show_config_summary(self, config):
        """Afficher un résumé de la configuration"""
        md = Markdown(f"""
        ## Configuration de Migration
        - **Équipes à migrer**: {len(config)}
        - **Dossiers sources**: {sum(len(v['folders']) for v in config.values())}
        - **Destination**: SharePoint Online
        """)
        self.console.print(md)