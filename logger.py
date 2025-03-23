import logging

class TransferLogger:
    def __init__(self, success_log_file: str = 'transfer_success.log', error_log_file: str = 'transfer_errors.log'):
        # Créer un logger unique
        self.logger = logging.getLogger('TransferLogger')
        self.logger.setLevel(logging.INFO)  # Niveau de log global

        # Formatter commun pour les deux fichiers
        formatter = logging.Formatter('%(asctime)s - %(message)s')

        # Handler pour les succès (niveau INFO)
        success_handler = logging.FileHandler(success_log_file, mode='a')
        success_handler.setLevel(logging.INFO)
        success_handler.setFormatter(formatter)
        success_handler.addFilter(lambda record: record.levelno == logging.INFO)  # Filtrer uniquement les INFO

        # Handler pour les erreurs (niveau ERROR)
        error_handler = logging.FileHandler(error_log_file, mode='a')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(lambda record: record.levelno == logging.ERROR)  # Filtrer uniquement les ERROR

        # Ajouter les handlers au logger
        self.logger.addHandler(success_handler)
        self.logger.addHandler(error_handler)

    def log_success(self, item_path: str):
        """Enregistre un succès dans le fichier des succès."""
        self.logger.info(f"SUCCÈS: {item_path}")

    def log_failure(self, item_path: str, reason: str):
        """Enregistre un échec dans le fichier des erreurs."""
        self.logger.error(f"ÉCHEC: {item_path} - Raison: {reason}")