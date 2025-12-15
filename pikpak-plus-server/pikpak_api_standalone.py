# -*- coding: utf-8 -*-
import asyncio
import hashlib
import json
import logging
import os
import re
import time
from base64 import b64decode, b64encode
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

import httpx

# ==============================================================================
# Settings & Constants
# ==============================================================================

IS_DEVELOPMENT = os.getenv("IS_DEVELOPMENT", "false").lower() == "true"
PIKPAK_API_HOST = "api-drive.mypikpak.com"
PIKPAK_USER_HOST = "user.mypikpak.com"
WEBDAV_BASE_URL = "https://api-dav.mypikpak.com"
DEFAULT_TIMEOUT = 30.0

CLIENT_ID = "YNxT9w7GMdWvEOKa"
CLIENT_SECRET = "dbw2OtmVEeuUvIptb1Coyg"
CLIENT_VERSION = "1.47.1"
PACKAGE_NAME = "com.pikcloud.pikpak"
SDK_VERSION = "2.0.4.204000"
APP_NAME = PACKAGE_NAME

SALTS = [
    "Gez0T9ijiI9WCeTsKSg3SMlx",
    "zQdbalsolyb1R/",
    "ftOjr52zt51JD68C3s",
    "yeOBMH0JkbQdEFNNwQ0RI9T3wU/v",
    "BRJrQZiTQ65WtMvwO",
    "je8fqxKPdQVJiy1DM6Bc9Nb1",
    "niV",
    "9hFCW2R1",
    "sHKHpe2i96",
    "p7c5E6AcXQ/IJUuAEC9W6",
    "",
    "aRv9hjc9P+Pbn+u3krN6",
    "BzStcgE8qVdqjEH16l4",
    "SqgeZvL5j9zoHP95xWHt",
    "zVof5yaJkPe3VFpadPof",
]

# ==============================================================================
# Enums
# ==============================================================================

class DownloadStatus(Enum):
    not_downloading = "not_downloading"
    downloading = "downloading"
    done = "done"
    error = "error"
    not_found = "not_found"

# ==============================================================================
# Exceptions
# ==============================================================================

class PikpakException(Exception):
    def __init__(self, message):
        super().__init__(message)

class PikpakRetryException(PikpakException):
    pass

# ==============================================================================
# Utils
# ==============================================================================

def get_timestamp() -> int:
    """Get current timestamp."""
    return int(time.time() * 1000)

def device_id_generator() -> str:
    """Generate a random device id."""
    return str(uuid4()).replace("-", "")

def captcha_sign(device_id: str, timestamp: str) -> str:
    """Generate a captcha sign."""
    sign = CLIENT_ID + CLIENT_VERSION + PACKAGE_NAME + device_id + timestamp
    for salt in SALTS:
        sign = hashlib.md5((sign + salt).encode()).hexdigest()
    return f"1.{sign}"

def generate_device_sign(device_id, package_name):
    signature_base = f"{device_id}{package_name}1appkey"
    sha1_hash = hashlib.sha1()
    sha1_hash.update(signature_base.encode("utf-8"))
    sha1_result = sha1_hash.hexdigest()
    md5_hash = hashlib.md5()
    md5_hash.update(sha1_result.encode("utf-8"))
    md5_result = md5_hash.hexdigest()
    return f"div101.{device_id}{md5_result}"

def build_custom_user_agent(device_id, user_id):
    device_sign = generate_device_sign(device_id, PACKAGE_NAME)
    user_agent_parts = [
        f"ANDROID-{APP_NAME}/{CLIENT_VERSION}",
        "protocolVersion/200",
        "accesstype/",
        f"clientid/{CLIENT_ID}",
        f"clientversion/{CLIENT_VERSION}",
        "action_type/",
        "networktype/WIFI",
        "sessionid/",
        f"deviceid/{device_id}",
        "providername/NONE",
        f"devicesign/{device_sign}",
        "refresh_token/",
        f"sdkversion/{SDK_VERSION}",
        f"datetime/{get_timestamp()}",
        f"usrno/{user_id}",
        f"appname/{APP_NAME}",
        "session_origin/",
        "grant_type/",
        "appid/",
        "clientip/",
        "devicename/Xiaomi_M2004j7ac",
        "osversion/13",
        "platformversion/10",
        "accessmode/",
        "devicemodel/M2004J7AC",
    ]
    return " ".join(user_agent_parts)

# ==============================================================================
# Main Class
# ==============================================================================

class PikPakApi:
    """
    PikPakApi Unified Class
    Combines Auth, File Management, Offline Download, and WebDAV functionality.
    """
    PIKPAK_API_HOST = PIKPAK_API_HOST
    PIKPAK_USER_HOST = PIKPAK_USER_HOST

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        encoded_token: Optional[str] = None,
        httpx_client_args: Optional[Dict[str, Any]] = None,
        device_id: Optional[str] = None,
        request_max_retries: int = 3,
        request_initial_backoff: float = 3.0,
        token_refresh_callback: Optional[Callable] = None,
        token_refresh_callback_kwargs: Optional[Dict[str, Any]] = None,
    ):
        # Auth Mixin Init
        self.username = username
        self.password = password
        self.encoded_token = encoded_token
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.device_id = device_id or hashlib.md5(f"{self.username}{self.password}".encode()).hexdigest()
        self.captcha_token = None
        self.captcha_expires_at = None
        self.captcha_tokens = {}
        self.token_refresh_callback = token_refresh_callback
        self.token_refresh_callback_kwargs = token_refresh_callback_kwargs or {}

        # FileManager Mixin Init
        self._path_id_cache: Dict[str, Any] = {}

        # Core Init
        self.max_retries = request_max_retries
        self.initial_backoff = request_initial_backoff

        # Save client args to recreate client if needed (e.g. for WebDAV if we wanted separate clients,
        # but here we'll try to reuse or use consistent config)
        self.httpx_client_args = httpx_client_args or {"timeout": 10}
        self.httpx_client = httpx.AsyncClient(**self.httpx_client_args)
        self.user_agent: Optional[str] = None

        if self.encoded_token:
            self.decode_token()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PikPakApi":
        """Create PikPakApi object from a dictionary"""
        import inspect
        params = inspect.signature(cls).parameters
        filtered_data = {key: data[key] for key in params if key in data}
        client = cls(**filtered_data)
        client.__dict__.update(data)
        return client

    def to_dict(self) -> Dict[str, Any]:
        """Returns the PikPakApi object as a dictionary"""
        data = self.__dict__.copy()
        # Filter non-serializable types. Compatible with Python < 3.10
        keys_to_delete = [
            k for k, v in data.items()
            if not type(v) in [str, int, float, bool, list, dict, type(None)]
        ]
        for k in keys_to_delete:
            del data[k]
        return data

    def build_custom_user_agent(self) -> str:
        self.user_agent = build_custom_user_agent(
            device_id=self.device_id,
            user_id=self.user_id if self.user_id else "",
        )
        return self.user_agent

    def get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": (
                self.build_custom_user_agent()
                if self.captcha_token
                else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/json; charset=utf-8",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if self.captcha_token:
            headers["X-Captcha-Token"] = self.captcha_token
        if self.device_id:
            headers["X-Device-Id"] = self.device_id
        return headers

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:

        if IS_DEVELOPMENT:
            return await self._mock_request(method, url, data, params)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self._send_request(method, url, data, params, headers)
                return await self._handle_response(response)
            except PikpakRetryException as error:
                logging.info(f"Retry attempt {attempt + 1}/{self.max_retries}")
                last_error = error
            except PikpakException:
                raise
            except httpx.HTTPError as error:
                logging.error(f"HTTP Error on attempt {attempt + 1}/{self.max_retries}: {str(error)}")
                last_error = error
            except Exception as error:
                logging.error(f"Unexpected error on attempt {attempt + 1}/{self.max_retries}: {str(error)}")
                last_error = error
            await asyncio.sleep(self.initial_backoff * (2**attempt))
        raise PikpakException(f"Max retries reached. Last error: {str(last_error)}")

    async def _send_request(self, method, url, data, params, headers):
        req_headers = headers or self.get_headers()
        return await self.httpx_client.request(
            method,
            url,
            json=data,
            params=params,
            headers=req_headers,
        )

    async def _handle_response(self, response) -> Dict[str, Any]:
        try:
            json_data = response.json()
        except ValueError:
            if response.status_code == 200:
                return {}
            raise PikpakRetryException("Empty JSON data")

        if not json_data:
            if response.status_code == 200:
                return {}
            raise PikpakRetryException("Empty JSON data")

        if "error" not in json_data:
            return json_data

        if json_data["error"] == "invalid_account_or_password":
            raise PikpakException("Invalid username or password")

        if json_data.get("error_code") == 16:
            await self.refresh_access_token()
            raise PikpakRetryException("Token refreshed, please retry")

        raise PikpakException(json_data.get("error_description", "Unknown Error"))

    async def _request_get(self, url: str, params: dict = None):
        return await self._make_request("get", url, params=params)

    async def _request_post(self, url: str, data: dict = None, headers: dict = None):
        return await self._make_request("post", url, data=data, headers=headers)

    async def _request_patch(self, url: str, data: dict = None):
        return await self._make_request("patch", url, data=data)

    async def _request_delete(self, url: str, params: dict = None, data: dict = None):
        return await self._make_request("delete", url, params=params, data=data)

    async def _mock_request(self, method: str, url: str, data: Any, params: Any) -> Dict[str, Any]:
        # Minimal mock implementation
        return {"success": True, "mock": True}

    # ==============================================================================
    # Auth Methods
    # ==============================================================================

    def decode_token(self):
        try:
            decoded_data = json.loads(b64decode(self.encoded_token).decode())
        except Exception:
            raise PikpakException("Invalid encoded token")
        if not decoded_data.get("access_token") or not decoded_data.get("refresh_token"):
            raise PikpakException("Invalid encoded token")
        self.access_token = decoded_data.get("access_token")
        self.refresh_token = decoded_data.get("refresh_token")

    def encode_token(self):
        token_data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }
        self.encoded_token = b64encode(json.dumps(token_data).encode()).decode()

    async def captcha_init(self, action: str, meta: dict = None) -> Dict[str, Any]:
        url = f"https://{PIKPAK_USER_HOST}/v1/shield/captcha/init"
        if not meta:
            t = f"{get_timestamp()}"
            meta = {
                "captcha_sign": captcha_sign(self.device_id, t),
                "client_version": CLIENT_VERSION,
                "package_name": PACKAGE_NAME,
                "user_id": self.user_id,
                "timestamp": t,
            }
        params = {
            "client_id": CLIENT_ID,
            "action": action,
            "device_id": self.device_id,
            "meta": meta,
        }
        return await self._request_post(url, data=params)

    async def _get_valid_captcha_token(self, action: str, meta: dict = None) -> str:
        if action in self.captcha_tokens:
            captcha_info = self.captcha_tokens[action]
            if captcha_info['expires_at'] and time.time() < (captcha_info['expires_at'] - 10):
                return captcha_info['token']

        result = await self.captcha_init(action=action, meta=meta)
        captcha_token = result.get("captcha_token", "")
        expires_in = result.get("expires_in", 300)

        if not captcha_token:
            raise PikpakException("captcha_token get failed")

        self.captcha_tokens[action] = {
            'token': captcha_token,
            'expires_at': time.time() + expires_in
        }
        self.captcha_token = captcha_token
        self.captcha_expires_at = time.time() + expires_in
        return captcha_token

    async def login(self) -> None:
        login_url = f"https://{PIKPAK_USER_HOST}/v1/auth/signin"
        metas = {}
        if not self.username or not self.password:
            raise PikpakException("username and password are required")
        if re.match(r"\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*", self.username):
            metas["email"] = self.username
        elif re.match(r"\d{11,18}", self.username):
            metas["phone_number"] = self.username
        else:
            metas["username"] = self.username

        try:
            captcha_token = await self._get_valid_captcha_token(
                action=f"POST:{login_url}",
                meta=metas,
            )
            login_data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "password": self.password,
                "username": self.username,
                "captcha_token": captcha_token,
            }
            user_info = await self._request_post(
                login_url,
                login_data,
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
            self.access_token = user_info["access_token"]
            self.refresh_token = user_info["refresh_token"]
            self.user_id = user_info["sub"]
            self.encode_token()
        except Exception as e:
            error_msg = str(e).lower()
            if "too frequent" in error_msg or "captcha" in error_msg:
                self.captcha_token = None
                self.captcha_expires_at = None
                self.captcha_tokens = {}
            raise e

    async def refresh_access_token(self) -> None:
        refresh_url = f"https://{PIKPAK_USER_HOST}/v1/auth/token"
        refresh_data = {
            "client_id": CLIENT_ID,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        user_info = await self._request_post(refresh_url, refresh_data)
        self.access_token = user_info["access_token"]
        self.refresh_token = user_info["refresh_token"]
        self.user_id = user_info["sub"]
        self.encode_token()
        if self.token_refresh_callback:
            await self.token_refresh_callback(self, **self.token_refresh_callback_kwargs)

    def get_user_info(self) -> Dict[str, Optional[str]]:
        return {
            "username": self.username,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "encoded_token": self.encoded_token,
        }

    # ==============================================================================
    # File Manager Methods
    # ==============================================================================

    async def create_folder(self, name: str = "新建文件夹", parent_id: Optional[str] = None) -> Dict[str, Any]:
        url = f"https://{PIKPAK_API_HOST}/drive/v1/files"
        data = {"kind": "drive#folder", "name": name, "parent_id": parent_id}
        return await self._request_post(url, data)

    async def delete_to_trash(self, ids: List[str]) -> Dict[str, Any]:
        url = f"https://{PIKPAK_API_HOST}/drive/v1/files:batchTrash"
        return await self._request_post(url, {"ids": ids})

    async def untrash(self, ids: List[str]) -> Dict[str, Any]:
        url = f"https://{PIKPAK_API_HOST}/drive/v1/files:batchUntrash"
        return await self._request_post(url, {"ids": ids})

    async def delete_forever(self, ids: List[str]) -> Dict[str, Any]:
        url = f"https://{PIKPAK_API_HOST}/drive/v1/files:batchDelete"
        return await self._request_post(url, {"ids": ids})

    async def file_list(
        self,
        size: int = 100,
        parent_id: Optional[str] = None,
        next_page_token: Optional[str] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        default_filters = {"trashed": {"eq": False}, "phase": {"eq": "PHASE_TYPE_COMPLETE"}}
        if additional_filters:
            default_filters.update(additional_filters)
        list_url = f"https://{PIKPAK_API_HOST}/drive/v1/files"
        list_data = {
            "parent_id": parent_id,
            "thumbnail_size": "SIZE_MEDIUM",
            "limit": size,
            "with_audit": "true",
            "page_token": next_page_token,
            "filters": json.dumps(default_filters),
        }
        return await self._request_get(list_url, list_data)

    async def events(self, size: int = 100, next_page_token: Optional[str] = None) -> Dict[str, Any]:
        list_url = f"https://{PIKPAK_API_HOST}/drive/v1/events"
        list_data = {"thumbnail_size": "SIZE_MEDIUM", "limit": size, "next_page_token": next_page_token}
        return await self._request_get(list_url, list_data)

    async def path_to_id(self, path: str, create: bool = False) -> List[Dict[str, str]]:
        if not path or len(path) <= 0:
            return []
        paths = path.split("/")
        paths = [p.strip() for p in paths if len(p) > 0]
        multi_level_paths = ["/" + "/".join(paths[: i + 1]) for i in range(len(paths))]
        path_ids = [self._path_id_cache[p] for p in multi_level_paths if p in self._path_id_cache]

        hit_cnt = len(path_ids)
        if hit_cnt == len(paths):
            return path_ids
        elif hit_cnt == 0:
            count = 0
            parent_id = None
        else:
            count = hit_cnt
            parent_id = path_ids[-1]["id"]

        next_page_token = None
        while count < len(paths):
            data = await self.file_list(parent_id=parent_id, next_page_token=next_page_token)
            record_of_target_path = None
            for f in data.get("files", []):
                current_path = "/" + "/".join(paths[:count] + [f.get("name")])
                file_type = "folder" if f.get("kind", "").find("folder") != -1 else "file"
                record = {"id": f.get("id"), "name": f.get("name"), "file_type": file_type}
                self._path_id_cache[current_path] = record
                if f.get("name") == paths[count]:
                    record_of_target_path = record
            if record_of_target_path is not None:
                path_ids.append(record_of_target_path)
                count += 1
                parent_id = record_of_target_path["id"]
            elif data.get("next_page_token") and (not next_page_token or next_page_token != data.get("next_page_token")):
                next_page_token = data.get("next_page_token")
            elif create:
                data = await self.create_folder(name=paths[count], parent_id=parent_id)
                file_id = data.get("file").get("id")
                record = {"id": file_id, "name": paths[count], "file_type": "folder"}
                path_ids.append(record)
                current_path = "/" + "/".join(paths[: count + 1])
                self._path_id_cache[current_path] = record
                count += 1
                parent_id = file_id
            else:
                break
        return path_ids

    async def file_batch_move(self, ids: List[str], to_parent_id: Optional[str] = None) -> Dict[str, Any]:
        to = {"parent_id": to_parent_id} if to_parent_id else {}
        return await self._request_post(
            url=f"https://{PIKPAK_API_HOST}/drive/v1/files:batchMove",
            data={"ids": ids, "to": to},
        )

    async def file_batch_copy(self, ids: List[str], to_parent_id: Optional[str] = None) -> Dict[str, Any]:
        to = {"parent_id": to_parent_id} if to_parent_id else {}
        return await self._request_post(
            url=f"https://{PIKPAK_API_HOST}/drive/v1/files:batchCopy",
            data={"ids": ids, "to": to},
        )

    async def file_move_or_copy_by_path(
        self, from_path: List[str], to_path: str, move: bool = False, create: bool = False
    ) -> Dict[str, Any]:
        from_ids: List[str] = []
        for path in from_path:
            if path_ids := await self.path_to_id(path):
                if file_id := path_ids[-1].get("id"):
                    from_ids.append(file_id)
        if not from_ids:
            raise PikpakException("Source files not found")
        to_path_ids = await self.path_to_id(to_path, create=create)
        to_parent_id = to_path_ids[-1].get("id") if to_path_ids else None

        if move:
            return await self.file_batch_move(ids=from_ids, to_parent_id=to_parent_id)
        else:
            return await self.file_batch_copy(ids=from_ids, to_parent_id=to_parent_id)

    async def get_download_url(self, file_id: str) -> Dict[str, Any]:
        result = await self.captcha_init(action=f"GET:/drive/v1/files/{file_id}")
        self.captcha_token = result.get("captcha_token")
        result = await self._request_get(url=f"https://{PIKPAK_API_HOST}/drive/v1/files/{file_id}?")
        self.captcha_token = None
        return result

    async def file_rename(self, id: str, new_file_name: str) -> Dict[str, Any]:
        return await self._request_patch(
            url=f"https://{PIKPAK_API_HOST}/drive/v1/files/{id}",
            data={"name": new_file_name},
        )

    async def file_batch_star(self, ids: List[str]) -> Dict[str, Any]:
        return await self._request_post(
            url=f"https://{PIKPAK_API_HOST}/drive/v1/files:star",
            data={"ids": ids},
        )

    async def file_batch_unstar(self, ids: List[str]) -> Dict[str, Any]:
        return await self._request_post(
            url=f"https://{PIKPAK_API_HOST}/drive/v1/files:unstar",
            data={"ids": ids},
        )

    async def file_star_list(self, size: int = 100, next_page_token: Optional[str] = None) -> Dict[str, Any]:
        additional_filters = {"system_tag": {"in": "STAR"}}
        return await self.file_list(
            size=size,
            parent_id="*",
            next_page_token=next_page_token,
            additional_filters=additional_filters,
        )

    async def file_batch_share(
        self, ids: List[str], need_password: Optional[bool] = False, expiration_days: Optional[int] = -1
    ) -> Dict[str, Any]:
        data = {
            "file_ids": ids,
            "share_to": "encryptedlink" if need_password else "publiclink",
            "expiration_days": expiration_days,
            "pass_code_option": "REQUIRED" if need_password else "NOT_REQUIRED",
        }
        return await self._request_post(url=f"https://{PIKPAK_API_HOST}/drive/v1/share", data=data)

    async def get_quota_info(self) -> Dict[str, Any]:
        return await self._request_get(url=f"https://{PIKPAK_API_HOST}/drive/v1/about")

    async def get_invite_code(self):
        result = await self._request_get(url=f"https://{PIKPAK_API_HOST}/vip/v1/activity/inviteCode")
        return result["code"]

    async def vip_info(self):
        return await self._request_get(url=f"https://{PIKPAK_API_HOST}/drive/v1/privilege/vip")

    async def get_transfer_quota(self) -> Dict[str, Any]:
        return await self._request_get(url=f"https://{PIKPAK_API_HOST}/vip/v1/quantity/list?type=transfer")

    async def get_share_folder(self, share_id: str, pass_code_token: str, parent_id: str = None) -> Dict[str, Any]:
        data = {
            "limit": "100",
            "thumbnail_size": "SIZE_LARGE",
            "order": "6",
            "share_id": share_id,
            "parent_id": parent_id,
            "pass_code_token": pass_code_token,
        }
        return await self._request_get(url=f"https://{PIKPAK_API_HOST}/drive/v1/share/detail", params=data)

    async def get_share_info(self, share_link: str, pass_code: str = None) -> Dict[str, Any]:
        match = re.search(r"/s/([^/]+)(?:.*/([^/]+))?$", share_link)
        if match:
            share_id = match.group(1)
            parent_id = match.group(2) if match.group(2) else None
        else:
            raise ValueError("Share Link Is Not Right")
        data = {
            "limit": "100",
            "thumbnail_size": "SIZE_LARGE",
            "order": "3",
            "share_id": share_id,
            "parent_id": parent_id,
            "pass_code": pass_code,
        }
        return await self._request_get(url=f"https://{PIKPAK_API_HOST}/drive/v1/share", params=data)

    async def restore(self, share_id: str, pass_code_token: str, file_ids: List[str]) -> Dict[str, Any]:
        data = {"share_id": share_id, "pass_code_token": pass_code_token, "file_ids": file_ids}
        return await self._request_post(url=f"https://{PIKPAK_API_HOST}/drive/v1/share/restore", data=data)

    # ==============================================================================
    # Offline Download Methods
    # ==============================================================================

    async def offline_download(self, file_url: str, parent_id: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        result = await self.captcha_init(action="POST:/drive/v1/files")
        self.captcha_token = result.get("captcha_token")
        download_data = {
            "kind": "drive#file",
            "name": name,
            "upload_type": "UPLOAD_TYPE_URL",
            "url": {"url": file_url},
            "folder_type": "DOWNLOAD" if not parent_id else "",
            "parent_id": parent_id,
        }
        result = await self._request_post(f"https://{PIKPAK_API_HOST}/drive/v1/files", download_data)
        self.captcha_token = None
        return result

    async def offline_list(
        self, size: int = 10000, next_page_token: Optional[str] = None, phase: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if phase is None:
            phase = ["PHASE_TYPE_RUNNING", "PHASE_TYPE_ERROR"]
        list_data = {
            "type": "offline",
            "thumbnail_size": "SIZE_SMALL",
            "limit": size,
            "page_token": next_page_token,
            "filters": json.dumps({"phase": {"in": ",".join(phase)}}),
            "with": "reference_resource",
        }
        return await self._request_get(f"https://{PIKPAK_API_HOST}/drive/v1/tasks", list_data)

    async def offline_file_info(self, file_id: str) -> Dict[str, Any]:
        return await self._request_get(
            f"https://{PIKPAK_API_HOST}/drive/v1/files/{file_id}",
            {"thumbnail_size": "SIZE_LARGE"}
        )

    async def offline_task_retry(self, task_id: str) -> Dict[str, Any]:
        list_data = {"type": "offline", "create_type": "RETRY", "id": task_id}
        try:
            return await self._request_post(f"https://{PIKPAK_API_HOST}/drive/v1/task", list_data)
        except Exception as e:
            raise PikpakException(f"Retry offline task failed: {task_id}. {e}")

    async def delete_tasks(self, task_ids: List[str], delete_files: bool = False) -> None:
        params = {"task_ids": task_ids, "delete_files": delete_files}
        try:
            await self._request_delete(f"https://{PIKPAK_API_HOST}/drive/v1/tasks", params=params)
        except Exception as e:
            raise PikpakException(f"Failing to delete tasks: {task_ids}. {e}")

    async def get_task_status(self, task_id: str, file_id: str) -> DownloadStatus:
        try:
            infos = await self.offline_list()
            if infos and infos.get("tasks", []):
                for task in infos.get("tasks", []):
                    if task_id == task.get("id"):
                        return DownloadStatus.downloading
            file_info = await self.offline_file_info(file_id=file_id)
            if file_info:
                return DownloadStatus.done
            else:
                return DownloadStatus.not_found
        except PikpakException:
            return DownloadStatus.error

    # ==============================================================================
    # WebDAV Methods
    # ==============================================================================

    def _get_webdav_headers(self) -> Dict[str, str]:
        return {
            "accept": "*/*",
            "authorization": f"Bearer {self.access_token}",
            "content-type": "application/json",
            "origin": "https://mypikpak.com",
            "referer": "https://mypikpak.com/",
        }

    async def get_webdav_applications(self) -> Dict[str, Any]:
        url = f"{WEBDAV_BASE_URL}/webdav/v1/applications"
        headers = self._get_webdav_headers()
        # Use a new client but with the same args (e.g. proxies) as the main client
        async with httpx.AsyncClient(**self.httpx_client_args) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def toggle_webdav(self, enable: bool) -> Dict[str, Any]:
        url = f"{WEBDAV_BASE_URL}/webdav/v1/toggle-enable"
        headers = self._get_webdav_headers()
        data = {"enable": enable}
        async with httpx.AsyncClient(**self.httpx_client_args) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

    async def create_webdav_application(self, application_name: str) -> Dict[str, Any]:
        url = f"{WEBDAV_BASE_URL}/webdav/v1/application"
        headers = self._get_webdav_headers()
        data = {"application_name": application_name}
        async with httpx.AsyncClient(**self.httpx_client_args) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

    async def delete_webdav_application(self, username: str, password: str) -> Dict[str, Any]:
        url = f"{WEBDAV_BASE_URL}/webdav/v1/application"
        headers = self._get_webdav_headers()
        data = {"username": username, "password": password}
        async with httpx.AsyncClient(**self.httpx_client_args) as client:
            response = await client.request("DELETE", url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

    async def modify_webdav_application(self, username: str, password: str, modify_props: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{WEBDAV_BASE_URL}/webdav/v1/application"
        headers = self._get_webdav_headers()
        data = {"username": username, "password": password, "modify_props": modify_props}
        async with httpx.AsyncClient(**self.httpx_client_args) as client:
            response = await client.patch(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
