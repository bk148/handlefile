# logger.py
import logging
import json
from datetime import datetime

class MigrationLogger:
    def __init__(self, log_file="migration_log.json"):
        self.log_file = log_file
        self.log_data = {
            "start_time": None,
            "end_time": None,
            "size_folder_source": None,
            "total_files": None,
            "total_folders": None,
            "total_contenu_copied": None,
            "error_logs": None
        }

    def start_log(self):
        self.log_data["start_time"] = datetime.now().isoformat()
        logging.info("Migration started.")

    def end_log(self, size_folder_source, total_files, total_folders, total_contenu_copied, error_logs):
        self.log_data["end_time"] = datetime.now().isoformat()
        self.log_data["size_folder_source"] = size_folder_source
        self.log_data["total_files"] = total_files
        self.log_data["total_folders"] = total_folders
        self.log_data["total_contenu_copied"] = total_contenu_copied
        self.log_data["error_logs"] = error_logs

        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=4)
        logging.info("Migration ended. Logs saved to {}".format(self.log_file))