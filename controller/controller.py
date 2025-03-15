import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from model import ModelGraphTransfer


class ControllerGraphTransfer:
    """Contrôleur principal pour gérer le processus de migration"""

    def __init__(self, token_generator, proxy, view):
        self.model = ModelGraphTransfer(token_generator, proxy)
        self.view = view
        self.stats = {
            'total_files': 0,
            'transferred': 0,
            'total_size': 0,
            'errors': 0
        }

    def execute_migration(self, team_id, channel_id, site_id, source_path):
        """Exécuter la migration complète pour une équipe"""
        try:
            # Récupérer le dossier de fichiers du canal
            folder_data = self.model.get_channel_files_folder(team_id, channel_id)
            if not folder_data:
                raise Exception(f"Impossible de récupérer le dossier de fichiers pour l'équipe {team_id}")

            root_folder_id = folder_data['id']

            # Créer la structure de dossiers
            folder_structure = self._map_folder_structure(source_path)
            created_folders = self._create_folders(site_id, root_folder_id, folder_structure)

            # Uploader les fichiers en parallèle
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                for folder_path, local_path in created_folders.items():
                    for file in local_path.iterdir():
                        if file.is_file():
                            self.stats['total_files'] += 1
                            self.stats['total_size'] += file.stat().st_size
                            futures.append(
                                executor.submit(
                                    self._process_file,
                                    site_id,
                                    created_folders[folder_path],
                                    file
                                )
                            )

                # Suivre la progression
                self.view.show_progress_start(self.stats['total_files'], self.stats['total_size'])
                for future in as_completed(futures):
                    result = future.result()
                    self._update_stats(result)
                    self.view.show_progress_update(self.stats)

        except Exception as e:
            self.view.log_error(f"Erreur de migration: {str(e)}")
            raise

    def _map_folder_structure(self, source_path):
        """Mapper la structure des dossiers locaux"""
        structure = {}
        for root, dirs, files in os.walk(source_path):
            relative_path = os.path.relpath(root, source_path)
            structure[relative_path] = Path(root)
        return structure

    def _create_folders(self, site_id, parent_id, folder_structure):
        """Créer la hiérarchie de dossiers sur SharePoint"""
        created = {'': parent_id}  # Dossier racine

        # Parcourir par niveau de profondeur
        for path in sorted(folder_structure.keys(), key=lambda x: x.count(os.sep)):
            if not path:
                continue

            parent_path = os.path.dirname(path)
            folder_name = os.path.basename(path)

            if parent_path not in created:
                continue  # Géré dans une itération précédente

            new_id = self.model.create_folder(site_id, created[parent_path], folder_name)
            if new_id:
                created[path] = new_id

        return created

    def _process_file(self, site_id, folder_id, file_path):
        """Traiter un fichier individuel"""
        try:
            success = self.model.upload_file_to_channel(site_id, folder_id, file_path)
            return {
                'success': success[1] != "exists",  # Ignorer les fichiers existants
                'size': file_path.stat().st_size,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'size': 0,
                'error': str(e)
            }

    def _update_stats(self, result):
        """Mettre à jour les statistiques"""
        if result['success']:
            self.stats['transferred'] += 1
            self.stats['total_size'] -= result['size']
        else:
            self.stats['errors'] += 1

    def get_stats(self):
        """Obtenir les statistiques complètes"""
        return self.stats.copy()