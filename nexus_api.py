import requests
import json
import os

class NexusAPI:
    def __init__(self, port=5555):
        self.port = port
        self.base_url = f"http://localhost:{port}/api"

    def get_config(self):
        try:
            response = requests.get(f"{self.base_url}/get-config", timeout=5)
            if response.status_code == 200:
                return True, response.json()
            return False, f"Error {response.status_code}"
        except Exception as e:
            return False, str(e)

    def set_config(self, gta_path=None, output_dir=None, enable_mods=False):
        payload = {
            "GTAPath": gta_path,
            "CodewalkerOutputDir": output_dir,
            "EnableMods": enable_mods
        }
        try:
            response = requests.post(f"{self.base_url}/set-config", json=payload, timeout=10)
            if response.status_code == 200:
                return True, "Config synced"
            return False, f"Error {response.status_code}"
        except Exception as e:
            return False, str(e)

    def search_file(self, filename):
        try:
            response = requests.get(f"{self.base_url}/search-file", params={"filename": filename}, timeout=10)
            if response.status_code == 200:
                return True, response.json()
            return False, []
        except Exception as e:
            return False, []

    def download_files(self, full_paths, output_dir, xml=True):
        if isinstance(full_paths, list):
            full_paths = ",".join(full_paths)
            
        params = {
            "fullPaths": full_paths,
            "xml": str(xml).lower(),
            "textures": "true",
            "outputFolderPath": output_dir
        }
        try:
            # CodeWalker.API uses GET for download-files
            response = requests.get(f"{self.base_url}/download-files", params=params, timeout=60)
            if response.status_code == 200:
                return True, "Download successful"
            return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

    def import_to_rpf(self, file_paths, rpf_path, output_folder=None):
        payload = {
            "xml": "true",
            "filePaths": file_paths,
            "rpfArchivePath": rpf_path,
            "outputFolder": output_folder or ""
        }
        try:
            response = requests.post(f"{self.base_url}/import", data=payload, timeout=30)
            if response.status_code == 200:
                return True, "Import successful"
            return False, f"Error {response.status_code}"
        except Exception as e:
            return False, str(e)
            
    def get_all_assets(self):
        """Used for building the cache."""
        try:
            # CodeWalker.API search uses .Contains()
            all_results = []
            # Exhaustive search for all common GTA file types and characters
            search_terms = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
            
            for term in search_terms:
                print(f"[WUABO Nexus] Indexing batch {term}...")
                ok, results = self.search_file(term)
                if ok:
                    all_results.extend(results)
            
            final_list = list(set(all_results))
            return True, final_list
        except Exception as e:
            return False, str(e)
    def shutdown(self):
        try:
            response = requests.post(f"{self.base_url}/shutdown", timeout=2)
            return response.status_code == 200, "Shutdown requested"
        except Exception as e:
            return False, str(e)
