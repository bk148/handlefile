import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    # Créer le dossier de logs s'il n'existe pas
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configuration du logging
    log_file = os.path.join(log_dir, "transfer.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2),  # 5 Mo par fichier, 2 backups
            logging.StreamHandler()  # Afficher les logs dans la console
        ]
    )

    # Logger de démarrage
    logging.info("Logging configuration is set up.")