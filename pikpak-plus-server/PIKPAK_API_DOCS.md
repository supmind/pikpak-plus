# PikPak API Documentation

This document describes the API methods available in the `PikPakApi` class.

## Initialization

```python
pikpak = PikPakApi(
    username="your_username",
    password="your_password",
    # Optional
    encoded_token=None,
    httpx_client_args=None, # e.g. {"timeout": 10, "proxies": ...}
    device_id=None,
    request_max_retries=3,
    request_initial_backoff=3.0,
    token_refresh_callback=None,
    token_refresh_callback_kwargs=None
)
```

## Authentication (`AuthMixin`)

### `login()`
Logs in to PikPak using the provided username and password.
- **Returns**: `None`
- **Updates**: `self.access_token`, `self.refresh_token`, `self.user_id`.

### `refresh_access_token()`
Refreshes the access token using the stored refresh token.
- **Returns**: `None`
- **Updates**: `self.access_token`, `self.refresh_token`.

### `get_user_info()`
Returns a dictionary containing user information.
- **Returns**: `Dict` with keys `username`, `user_id`, `access_token`, `refresh_token`, `encoded_token`.

## File Management (`FileManagerMixin`)

### `file_list(size=100, parent_id=None, next_page_token=None, additional_filters=None)`
Lists files in a directory.
- **Parameters**:
    - `size` (int): Number of items to retrieve (default 100).
    - `parent_id` (str): ID of the parent folder (default None for root).
    - `next_page_token` (str): Token for the next page of results.
    - `additional_filters` (dict): Extra filters for the query.
- **Returns**: `Dict` containing file list data.

### `create_folder(name="新建文件夹", parent_id=None)`
Creates a new folder.
- **Parameters**:
    - `name` (str): Name of the folder.
    - `parent_id` (str): ID of the parent folder.
- **Returns**: `Dict` with the created folder info.

### `delete_to_trash(ids)`
Moves files/folders to trash.
- **Parameters**:
    - `ids` (List[str]): List of file IDs to trash.
- **Returns**: `Dict` response from API.

### `untrash(ids)`
Restores files/folders from trash.
- **Parameters**:
    - `ids` (List[str]): List of file IDs to restore.
- **Returns**: `Dict` response from API.

### `delete_forever(ids)`
Permanently deletes files/folders.
- **Parameters**:
    - `ids` (List[str]): List of file IDs to delete.
- **Returns**: `Dict` response from API.

### `file_batch_move(ids, to_parent_id=None)`
Moves files to a different folder.
- **Parameters**:
    - `ids` (List[str]): IDs of files to move.
    - `to_parent_id` (str): ID of the destination folder.
- **Returns**: `Dict` response.

### `file_batch_copy(ids, to_parent_id=None)`
Copies files to a different folder.
- **Parameters**:
    - `ids` (List[str]): IDs of files to copy.
    - `to_parent_id` (str): ID of the destination folder.
- **Returns**: `Dict` response.

### `file_rename(id, new_file_name)`
Renames a file.
- **Parameters**:
    - `id` (str): ID of the file.
    - `new_file_name` (str): New name for the file.
- **Returns**: `Dict` response.

### `get_download_url(file_id)`
Gets the download URL for a file.
- **Parameters**:
    - `file_id` (str): ID of the file.
- **Returns**: `Dict` containing download URL and other details.

### `path_to_id(path, create=False)`
Resolves a path string (e.g., `/Folder/File`) to file IDs.
- **Parameters**:
    - `path` (str): The path to resolve.
    - `create` (bool): Whether to create folders if they don't exist.
- **Returns**: `List[Dict]` containing ID and name for each path component.

### `file_move_or_copy_by_path(from_path, to_path, move=False, create=False)`
Moves or copies files using paths instead of IDs.
- **Parameters**:
    - `from_path` (List[str]): List of source paths.
    - `to_path` (str): Destination folder path.
    - `move` (bool): True to move, False to copy.
    - `create` (bool): True to create destination folders if missing.
- **Returns**: `Dict` response.

### `file_batch_star(ids)`
Stars (favorites) files.
- **Parameters**:
    - `ids` (List[str]): List of file IDs.
- **Returns**: `Dict` response.

### `file_batch_unstar(ids)`
Unstars files.
- **Parameters**:
    - `ids` (List[str]): List of file IDs.
- **Returns**: `Dict` response.

### `file_star_list(size=100, next_page_token=None)`
Lists starred files.
- **Parameters**:
    - `size` (int): Page size.
    - `next_page_token` (str): Next page token.
- **Returns**: `Dict` response.

### `get_quota_info()`
Gets storage quota information.
- **Returns**: `Dict` response.

### `vip_info()`
Gets VIP status information.
- **Returns**: `Dict` response.

### `get_transfer_quota()`
Gets transfer quota information.
- **Returns**: `Dict` response.

### `file_batch_share(ids, need_password=False, expiration_days=-1)`
Shares files.
- **Parameters**:
    - `ids` (List[str]): File IDs.
    - `need_password` (bool): Whether a password is required.
    - `expiration_days` (int): Days until expiration (-1 for never).
- **Returns**: `Dict` response.

### `get_share_info(share_link, pass_code=None)`
Gets info about a shared link.
- **Parameters**:
    - `share_link` (str): The share link.
    - `pass_code` (str): The password/code.
- **Returns**: `Dict` response.

### `get_share_folder(share_id, pass_code_token, parent_id=None)`
Lists files in a shared folder.
- **Parameters**:
    - `share_id` (str): Share ID.
    - `pass_code_token` (str): Token from `get_share_info`.
    - `parent_id` (str): Parent folder ID.
- **Returns**: `Dict` response.

### `restore(share_id, pass_code_token, file_ids)`
Saves shared files to your drive.
- **Parameters**:
    - `share_id` (str): Share ID.
    - `pass_code_token` (str): Token.
    - `file_ids` (List[str]): IDs of files to save.
- **Returns**: `Dict` response.

## Offline Download (`OfflineDownloadMixin`)

### `offline_download(file_url, parent_id=None, name=None)`
Adds an offline download task (cloud download).
- **Parameters**:
    - `file_url` (str): URL to download (magnet, http, etc.).
    - `parent_id` (str): Destination folder ID.
    - `name` (str): Custom name for the file.
- **Returns**: `Dict` response.

### `offline_list(size=10000, next_page_token=None, phase=None)`
Lists offline download tasks.
- **Parameters**:
    - `size` (int): Page size.
    - `next_page_token` (str): Next page token.
    - `phase` (List[str]): Status filters (default RUNNING, ERROR).
- **Returns**: `Dict` response.

### `offline_file_info(file_id)`
Gets info for an offline file.
- **Parameters**:
    - `file_id` (str): File ID.
- **Returns**: `Dict` response.

### `offline_task_retry(task_id)`
Retries a failed offline task.
- **Parameters**:
    - `task_id` (str): Task ID.
- **Returns**: `Dict` response.

### `delete_tasks(task_ids, delete_files=False)`
Deletes offline tasks.
- **Parameters**:
    - `task_ids` (List[str]): List of task IDs.
    - `delete_files` (bool): Whether to also delete downloaded files.
- **Returns**: `None`.

### `get_task_status(task_id, file_id)`
Gets the status of a specific task.
- **Parameters**:
    - `task_id` (str): Task ID.
    - `file_id` (str): File ID.
- **Returns**: `DownloadStatus` enum.

## WebDAV (`WebDavMixin`)

### `get_webdav_applications()`
Gets WebDAV configuration and applications.
- **Returns**: `Dict` response.

### `toggle_webdav(enable)`
Enables or disables WebDAV.
- **Parameters**:
    - `enable` (bool): True to enable, False to disable.
- **Returns**: `Dict` response.

### `create_webdav_application(application_name)`
Creates a new WebDAV application credential.
- **Parameters**:
    - `application_name` (str): Name for the app.
- **Returns**: `Dict` response.

### `delete_webdav_application(username, password)`
Deletes a WebDAV application.
- **Parameters**:
    - `username` (str): WebDAV username.
    - `password` (str): WebDAV password.
- **Returns**: `Dict` response.

### `modify_webdav_application(username, password, modify_props)`
Modifies a WebDAV application.
- **Parameters**:
    - `username` (str): WebDAV username.
    - `password` (str): WebDAV password.
    - `modify_props` (Dict): Properties to change (e.g. `{"read_only": True}`).
- **Returns**: `Dict` response.
