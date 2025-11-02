import os
import io
import json
import shutil
import zipfile
import logging
import requests
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Any, Callable, Dict, List, Tuple, Union
from http.server import HTTPServer, BaseHTTPRequestHandler

import dropbox
from dropbox.files import FolderMetadata, FileMetadata
from dotenv import load_dotenv, set_key
from tkinter import messagebox

from src.core.state import ENV_PATH, CACHE_PATH, INTERNAL_PATH, state

DEFAULT_COLOR = "#000000"
SUCCESS_COLOR = "#228B22"
WARNING_COLOR = "#ffff00"
ERROR_COLOR = "#CE0000"

BASE_FOLDER = "/ORDERS APRIL"
# FILES_FOLDER = "IMAGESTEST"
FILES_FOLDER = "IMAGES"
IMAGES_FOLDER = "ORDERS"
JSON_FOLDER = "JSON"

logger = logging.getLogger(__name__)


class Dropbox:      
    def __init__(self):
        if ENV_PATH.exists():
            load_dotenv(ENV_PATH)
        else:
            with open(ENV_PATH, 'w') as f:
                f.write("DROPBOX_APP_KEY=")

        self.app_key = os.environ.get("DROPBOX_APP_KEY", None)
        self.app_secret = os.environ.get("DROPBOX_APP_SECRET", None)
        self.refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN", None)
        self.token = None

        self._client = None
        self._redirect_uri = "http://127.0.0.1:53682/callback"
        self._port = int(self._redirect_uri.split(":")[-1].split("/")[0])

    def resolve_token(self) -> str:
        if not self.app_key:
            messagebox.showerror("APP KEY", "Please provide APP KEY in _internal/env")
            logger.debug("APP key didn't provide")
            return

        session = {}
        flow = dropbox.DropboxOAuth2Flow(
            consumer_key=self.app_key,
            redirect_uri=self._redirect_uri,
            session=session,
            csrf_token_session_key="csrf",
            use_pkce=True,                
            token_access_type="offline",
            scope=["files.metadata.read", "files.content.read"],
        )

        auth_code_holder = {"params": None}

        class Handler(BaseHTTPRequestHandler):
            REDIRECT_URI = self._redirect_uri
            def do_GET(self):
                if urlparse(self.path).path != urlparse(self.REDIRECT_URI).path:
                    self.send_response(404); self.end_headers(); return
                params = parse_qs(urlparse(self.path).query)
                auth_code_holder["params"] = {k: v[0] for k, v in params.items()}
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"OK. You can close this tab.")

        authorize_url = flow.start()
        webbrowser.open(authorize_url, new=1)
        HTTPServer(("127.0.0.1", self._port), Handler).handle_request()

        oauth_result = flow.finish(auth_code_holder["params"])
        set_key(str(ENV_PATH), "DROPBOX_REFRESH_TOKEN", oauth_result.refresh_token, quote_mode="never")
        self.refresh_token = oauth_result.refresh_token
        logger.debug("Got refresh token=%s", oauth_result.refresh_token)
        return oauth_result.refresh_token

    @property
    def client(self) -> dropbox.Dropbox:
        while not self.refresh_token:
            self.resolve_token()
        
        if not self._client:
            self._client = dropbox.Dropbox(
                app_key=self.app_key,
                oauth2_refresh_token=self.refresh_token,
                timeout=60,
            )

        return self._client

    def get_files_in_folder(self, folder_path: str) -> List[Tuple[str, str, int]]:
        files = []
        try:
            result = self.client.files_list_folder(path=folder_path)

            for entry in result.entries:
                if isinstance(entry, FolderMetadata):
                    files.append(("folder", entry.name, -1))
                elif isinstance(entry, FileMetadata):
                    files.append(("file", entry.name, entry.size))

            while result.has_more:
                result = self._client.files_list_folder_continue(result.cursor)
                for entry in result.entries:
                    if isinstance(entry, FolderMetadata):
                        files.append(("folder", entry.name, -1))
                    elif isinstance(entry, FileMetadata):
                        files.append(("file", entry.name, entry.size))

            return files

        except dropbox.exceptions.ApiError:
            logger.exception("Dropbox API error")
        except requests.exceptions.RequestException:
            logger.exception("Network error")

    def download_file(self, file_path: str, path_to_download: str = "") -> Union[Dict[str, Any], str]:
        try:
            metadata, res = self.client.files_download(file_path)
            full_path = path_to_download + file_path.split('/')[-1]
            with open(full_path, "wb") as f:
                f.write(res.content)
            return metadata, full_path

        except dropbox.exceptions.ApiError:
            logger.exception("Dropbox API error")
        except requests.exceptions.RequestException:
            logger.exception("Network error")

    def download_big_file(self, file_path: str, path_to_download: str = "", raw_data = False) -> Union[Dict[str, Any], Union[str, io.BytesIO]]:
        try:
            metadata, res = self.client.files_download(file_path)
            if raw_data:
                buffer = io.BytesIO()
                for chunk in res.iter_content(chunk_size=8*1024*1024):
                    buffer.write(chunk)
                buffer.seek(0)
                return metadata, buffer
            else:
                full_path = path_to_download + file_path.split('/')[-1]
                with open(full_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8*1024*1024):
                        f.write(chunk)
                return metadata, full_path

        except dropbox.exceptions.ApiError:
            logger.exception("Dropbox API error")
        except requests.exceptions.RequestException:
            logger.exception("Network error")
    
    def download_folder(self, folder_path: str, path_to_download: str = "") -> Union[Dict[str, Any], str]:
        try:
            metadata, res = self.client.files_download_zip(path=folder_path)
            full_path = path_to_download + folder_path.split('/')[-1] + ".zip"
            with open(full_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8*1024*1024):
                    f.write(chunk)
            return metadata, full_path

        except dropbox.exceptions.ApiError:
            logger.exception("Dropbox API error")
        except requests.exceptions.RequestException:
            logger.exception("Network error")

    def read_json(self, file_path: str) -> Dict[str, Any]:
        try:
            metadata, res = self.client.files_download(file_path)
            return json.loads(res.content.decode("utf-8"))

        except dropbox.exceptions.ApiError:
            logger.exception("Dropbox API error")
        except requests.exceptions.RequestException:
            logger.exception("Network error")


def index_dropbox(log_func: Callable[[str], None], progress_callback: Callable[[int, int], None] = None):
    client = Dropbox()
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, 'r') as f:
                cache = json.load(f)
        except:
            cache = {}
    else:
        cache = {}

    log_func(f"Starting indexing Dropbox from {state.dropbox_from.strftime("%d-%m-%Y")} to {state.dropbox_to.strftime("%d-%m-%Y")}. It may take a while...")

    # Check all folders
    folders = []
    files_info = client.get_files_in_folder(BASE_FOLDER)
    for file in files_info:
        if file[0] == "folder":
            folder_name = file[1]
            if folder_name.count(".") != 2:
                continue

            day, month, year = folder_name.split(".")
            file_date = datetime(day=int(day), month=int(month), year=int(year))

            if not (state.dropbox_from <= file_date <= state.dropbox_to):
                continue

            folders.append(folder_name)

    # Try to resolve FILES_FOLDER folder
    folder_files = {}
    for folder in folders:
        if folder == "17.02.2025":
            continue
        files_info = client.get_files_in_folder(f"{BASE_FOLDER}/{folder}/{FILES_FOLDER}")
        if files_info is None:
            logger.error(f"{FILES_FOLDER} folder not found in {folder} folder")
            continue

        printable_folders = []
        pattern = folder.replace('.', '-')
        for file in files_info:
            if file[0] == "folder":
                if file[1].startswith(pattern):
                    printable_folders.append(file[1])
                
        folder_files[folder] = printable_folders

    total_folders = len([file for files in folder_files.values() for file in files])
    twenty_percent = total_folders // 5
    log_func(f"Found {total_folders} folders to index")

    # Try to download printable folders
    orders = {}
    completed_folders = 0
    for parent_folder, files in folder_files.items():
        orders[parent_folder] = []
        cache[str(parent_folder)] = {}

        for file in files:

            if state.is_cancelled:
                break

            completed_folders += 1
            # report progress (completed_folders, total_folders)
            try:
                if progress_callback:
                    progress_callback(completed_folders, total_folders)
            except Exception:
                pass

            res = client.download_folder(f"{BASE_FOLDER}/{parent_folder}/{FILES_FOLDER}/{file}", str(INTERNAL_PATH) + "/")
            if res is None:
                logger.error(f"Error occurs during downloading file: {BASE_FOLDER}/{parent_folder}/{FILES_FOLDER}/{file}")
                continue

            # Unzip
            file_path = Path(res[1][:-4])
            if file_path.exists():
                shutil.rmtree(file_path, ignore_errors=True)

            with zipfile.ZipFile(str(file_path) + ".zip", 'r') as zip_ref:
                zip_ref.extractall(INTERNAL_PATH)

            cache[str(parent_folder)][str(file)] = []

            file_list = os.listdir(file_path)
            if JSON_FOLDER not in file_list:
                logger.error(f"{JSON_FOLDER} folder not found in {file_path}")

            for json_path in os.listdir(file_path / JSON_FOLDER):
                if not json_path.endswith('.json'):
                    continue
                
                orders[parent_folder].append(file_path / JSON_FOLDER / json_path)
                cache[parent_folder][file].append(str(json_path))

            shutil.rmtree(file_path, ignore_errors=True)
            os.remove(str(file_path) + ".zip")

    if not state.is_cancelled:
        with open(CACHE_PATH, 'w') as f:
            json.dump(cache, f, indent=4)

    # ensure progress reports completion
    try:
        if progress_callback:
            progress_callback(total_folders, total_folders)
    except Exception:
        pass

    log_func(f"Dropbox indexing completed", SUCCESS_COLOR)

def _get_cached_orders() -> List[Tuple[str, str, str]]:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, 'r') as f:
                cache = json.load(f)
        except:
            cache = {}
    else:
        cache = {}

    cached_orders = []
    for parent_folder, items in cache.items():
        for child_folder, files in items.items():
            for file in files:
                cached_orders.append((file, child_folder, parent_folder))

    return cached_orders

def get_indexed_orders_path(orders: List[str]) -> List[Tuple[str, str, str]]:
    cached_orders = _get_cached_orders()

    ids = []
    found_orders = []
    for file, child_folder, parent_folder in cached_orders:
        if file.split('_')[0] in orders and file not in ids:
            found_orders.append((file, child_folder, parent_folder))
            ids.append(file)

    return found_orders

def get_orders_info(orders: List[str], log_func: Callable[[str], None], progress_callback: Callable[[int, int], None] = None) -> Dict[str, Dict[str, Any]]:

    def is_filled(orders, found_orders):
        result = []
        found_orders_id = [ord_.split("_")[0] for ord_, _, _ in found_orders]
        for order in orders:
            if order in found_orders_id:
                result.append(True)
            else:
                result.append(False)
        return all(result)

    found_orders = get_indexed_orders_path(orders)
    # if len(found_orders) < len(orders):
    if not found_orders or not is_filled(orders, found_orders):
        log_func("Some orders not found in cache", WARNING_COLOR)
        index_dropbox(log_func, progress_callback=progress_callback)

    found_orders = get_indexed_orders_path(orders)
    not_found_orders = []
    if not found_orders or not set([order_.split('_')[0] for order_, _, _ in found_orders]).issubset(orders):
        for order in orders:
            if order not in [order_.split('_')[0] for order_, _, _ in found_orders]:
                logger.error(f"Order {order} not found in Dropbox")
                not_found_orders.append(order)
        log_func(f"Orders {not_found_orders} not found in Dropbox", ERROR_COLOR)

    orders_info = {}
    client = Dropbox()
    error_orders = []
    for i, (file, child_folder, parent_folder) in enumerate(sorted(found_orders, key=lambda x: int(x[0].split('_')[0]))):
        path = f"{BASE_FOLDER}/{parent_folder}/{FILES_FOLDER}/{child_folder}/{JSON_FOLDER}/{file}"
        log_func(f"Fetching {i+1}/{len(found_orders)}: {file}")
        info = client.read_json(path)
        if info is None:
            logger.error(f"Dropbox return empty json for {path}")
            error_orders.append(file.split('_')[0])
            continue
        
        orders_info[file] = (info, parent_folder, child_folder)

    if error_orders:
        log_func(f"Orders {error_orders} return empty json", ERROR_COLOR)
    return {"status": "success", "orders": orders_info, "error_orders": error_orders + not_found_orders}

if __name__ == "__main__":
    client = Dropbox()
    from pprint import pprint
    _, file_name = client.download_big_file(f"{BASE_FOLDER}/11.09.2025/{FILES_FOLDER}/11-09-2025 DOGTAG/160528_Image1.jpg", str(INTERNAL_PATH) + "/")
    from PIL import Image
    Image.open(file_name).show()
    os.remove(file_name)
    # pprint(get_orders_info(orders))