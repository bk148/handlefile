import logging
from datetime import datetime

class MigrationLogger:
    def __init__(self):
        # Configuration de la journalisation
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='transfer_logs.log',
            filemode='a'
        )
        self.logger = logging.getLogger("MigrationLogger")
        self.start_time = None

    def start_log(self):
        """Démarre la journalisation et enregistre l'heure de début."""
        self.start_time = datetime.now()
        self.logger.info("=" * 50)
        self.logger.info(f"Migration started at: {self.start_time}")
        self.logger.info("=" * 50)

    def end_log(self, size_folder_source=None, total_files=None, total_folders=None, total_contenu_copied=None, error_logs=None):
        """Termine la journalisation et enregistre un résumé du transfert."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        self.logger.info("=" * 50)
        self.logger.info(f"Migration completed at: {end_time}")
        self.logger.info(f"Total duration: {duration}")
        self.logger.info(f"Total data volume: {size_folder_source / (1024 * 1024):.2f} MB")
        self.logger.info(f"Total files: {total_files}")
        self.logger.info(f"Total folders: {total_folders}")
        self.logger.info(f"Files copied: {total_contenu_copied}")
        self.logger.info("=" * 50)

        # Enregistrer les erreurs
        if error_logs:
            self.logger.info("Error Summary:")
            for error_type, errors in error_logs.items():
                if errors:
                    self.logger.info(f"{error_type}: {len(errors)} errors")
                    for error in errors:
                        self.logger.info(f" - {error}")
        self.logger.info("=" * 50)