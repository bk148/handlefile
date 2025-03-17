from model.model_transfer import ModelGraphTransfer

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy, view):
        self.graph_api = ModelGraphTransfer(token_generator, proxy)
        self.view = view

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        self.view.show_message(f"Starting transfer for folder: {depot_data_directory_path}")
        try:
            completed_files, total_files = self.graph_api.transfer_data_folder_to_channel(
                group_id, channel_id, site_id, depot_data_directory_path
            )
            self.view.show_success(f"Transfer completed: {completed_files}/{total_files} files copied.")
        except Exception as e:
            self.view.show_error(f"Error during transfer: {e}")