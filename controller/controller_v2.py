import time
from model.model_transfer import ModelGraphTransfer
from view import TransferView

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.view = TransferView()

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        self.view.display_header()

        start_time = time.time()
        total_files = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        self.view.start_progress(total_files)

        completed_files, total_files = self.graph_api.transfer_data_folder_to_channel(group_id, channel_id, site_id, depot_data_directory_path)

        # Mettre à jour la barre de progression en temps réel
        for current in range(1, total_files + 1):
            self.view.update_progress(current)
            time.sleep(0.1)  # Simuler un délai pour la démonstration

        end_time = time.time()
        duration = end_time - start_time

        self.view.end_progress()
        self.view.display_transfer_summary(total_files, completed_files, duration)

        for error_type, errors in self.graph_api.error_logs.items():
            for error in errors:
                self.view.display_error(f"{error_type}: {error}")