# PikPak API 文档

本文档描述了 `PikPakApi` 类中可用的 API 方法。

## 初始化

```python
pikpak = PikPakApi(
    username="your_username",
    password="your_password",
    # 可选参数
    encoded_token=None,
    httpx_client_args=None, # 例如 {"timeout": 10, "proxies": ...}
    device_id=None,
    request_max_retries=3,
    request_initial_backoff=3.0,
    token_refresh_callback=None,
    token_refresh_callback_kwargs=None
)
```

## 认证 (`AuthMixin`)

### `login()`
使用提供的用户名和密码登录 PikPak。
- **返回**: `None`
- **更新**: `self.access_token`, `self.refresh_token`, `self.user_id`。

### `refresh_access_token()`
使用存储的刷新令牌刷新访问令牌。
- **返回**: `None`
- **更新**: `self.access_token`, `self.refresh_token`。

### `get_user_info()`
返回包含用户信息的字典。
- **返回**: `Dict` 包含键 `username`, `user_id`, `access_token`, `refresh_token`, `encoded_token`。

## 文件管理 (`FileManagerMixin`)

### `file_list(size=100, parent_id=None, next_page_token=None, additional_filters=None)`
列出目录中的文件。
- **参数**:
    - `size` (int): 要获取的项目数量（默认 100）。
    - `parent_id` (str): 父文件夹的 ID（默认为 None，即根目录）。
    - `next_page_token` (str): 下一页结果的令牌。
    - `additional_filters` (dict): 查询的额外过滤器。
- **返回**: `Dict` 包含文件列表数据。

### `create_folder(name="新建文件夹", parent_id=None)`
创建一个新文件夹。
- **参数**:
    - `name` (str): 文件夹名称。
    - `parent_id` (str): 父文件夹的 ID。
- **返回**: `Dict` 包含创建的文件夹信息。

### `delete_to_trash(ids)`
将文件/文件夹移至回收站。
- **参数**:
    - `ids` (List[str]): 要移至回收站的文件 ID 列表。
- **返回**: `Dict` API 的响应。

### `untrash(ids)`
从回收站恢复文件/文件夹。
- **参数**:
    - `ids` (List[str]): 要恢复的文件 ID 列表。
- **返回**: `Dict` API 的响应。

### `delete_forever(ids)`
永久删除文件/文件夹。
- **参数**:
    - `ids` (List[str]): 要删除的文件 ID 列表。
- **返回**: `Dict` API 的响应。

### `file_batch_move(ids, to_parent_id=None)`
将文件移动到不同的文件夹。
- **参数**:
    - `ids` (List[str]): 要移动的文件 ID。
    - `to_parent_id` (str): 目标文件夹的 ID。
- **返回**: `Dict` 响应。

### `file_batch_copy(ids, to_parent_id=None)`
将文件复制到不同的文件夹。
- **参数**:
    - `ids` (List[str]): 要复制的文件 ID。
    - `to_parent_id` (str): 目标文件夹的 ID。
- **返回**: `Dict` 响应。

### `file_rename(id, new_file_name)`
重命名文件。
- **参数**:
    - `id` (str): 文件 ID。
    - `new_file_name` (str): 文件的新名称。
- **返回**: `Dict` 响应。

### `get_download_url(file_id)`
获取文件的下载链接。
- **参数**:
    - `file_id` (str): 文件 ID。
- **返回**: `Dict` 包含下载链接和其他详细信息。

### `path_to_id(path, create=False)`
将路径字符串（例如 `/Folder/File`）解析为文件 ID。
- **参数**:
    - `path` (str): 要解析的路径。
    - `create` (bool): 如果文件夹不存在，是否创建。
- **返回**: `List[Dict]` 包含每个路径组件的 ID 和名称。

### `file_move_or_copy_by_path(from_path, to_path, move=False, create=False)`
使用路径而不是 ID 移动或复制文件。
- **参数**:
    - `from_path` (List[str]): 源路径列表。
    - `to_path` (str): 目标文件夹路径。
    - `move` (bool): True 为移动，False 为复制。
    - `create` (bool): 如果目标文件夹缺失，是否创建。
- **返回**: `Dict` 响应。

### `file_batch_star(ids)`
收藏文件。
- **参数**:
    - `ids` (List[str]): 文件 ID 列表。
- **返回**: `Dict` 响应。

### `file_batch_unstar(ids)`
取消收藏文件。
- **参数**:
    - `ids` (List[str]): 文件 ID 列表。
- **返回**: `Dict` 响应。

### `file_star_list(size=100, next_page_token=None)`
列出已收藏的文件。
- **参数**:
    - `size` (int): 页面大小。
    - `next_page_token` (str): 下一页令牌。
- **返回**: `Dict` 响应。

### `get_quota_info()`
获取存储配额信息。
- **返回**: `Dict` 响应。

### `vip_info()`
获取 VIP 状态信息。
- **返回**: `Dict` 响应。

### `get_transfer_quota()`
获取传输配额信息。
- **返回**: `Dict` 响应。

### `file_batch_share(ids, need_password=False, expiration_days=-1)`
分享文件。
- **参数**:
    - `ids` (List[str]): 文件 ID。
    - `need_password` (bool): 是否需要密码。
    - `expiration_days` (int): 过期天数（-1 表示永不过期）。
- **返回**: `Dict` 响应。

### `get_share_info(share_link, pass_code=None)`
获取关于分享链接的信息。
- **参数**:
    - `share_link` (str): 分享链接。
    - `pass_code` (str): 密码/提取码。
- **返回**: `Dict` 响应。

### `get_share_folder(share_id, pass_code_token, parent_id=None)`
列出分享文件夹中的文件。
- **参数**:
    - `share_id` (str): 分享 ID。
    - `pass_code_token` (str): 来自 `get_share_info` 的令牌。
    - `parent_id` (str): 父文件夹 ID。
- **返回**: `Dict` 响应。

### `restore(share_id, pass_code_token, file_ids)`
保存分享的文件到你的云盘。
- **参数**:
    - `share_id` (str): 分享 ID。
    - `pass_code_token` (str): 令牌。
    - `file_ids` (List[str]): 要保存的文件 ID。
- **返回**: `Dict` 响应。

## 离线下载 (`OfflineDownloadMixin`)

### `offline_download(file_url, parent_id=None, name=None)`
添加离线下载任务（云下载）。
- **参数**:
    - `file_url` (str): 下载链接 (magnet, http 等)。
    - `parent_id` (str): 目标文件夹 ID。
    - `name` (str): 文件的自定义名称。
- **返回**: `Dict` 响应。

### `offline_list(size=10000, next_page_token=None, phase=None)`
列出离线下载任务。
- **参数**:
    - `size` (int): 页面大小。
    - `next_page_token` (str): 下一页令牌。
    - `phase` (List[str]): 状态过滤器（默认 RUNNING, ERROR）。
- **返回**: `Dict` 响应。

### `offline_file_info(file_id)`
获取离线文件信息。
- **参数**:
    - `file_id` (str): 文件 ID。
- **返回**: `Dict` 响应。

### `offline_task_retry(task_id)`
重试失败的离线任务。
- **参数**:
    - `task_id` (str): 任务 ID。
- **返回**: `Dict` 响应。

### `delete_tasks(task_ids, delete_files=False)`
删除离线任务。
- **参数**:
    - `task_ids` (List[str]): 任务 ID 列表。
    - `delete_files` (bool): 是否同时删除已下载的文件。
- **返回**: `None`。

### `get_task_status(task_id, file_id)`
获取特定任务的状态。
- **参数**:
    - `task_id` (str): 任务 ID。
    - `file_id` (str): 文件 ID。
- **返回**: `DownloadStatus` 枚举。

## WebDAV (`WebDavMixin`)

### `get_webdav_applications()`
获取 WebDAV 配置和应用列表。
- **返回**: `Dict` 响应。

### `toggle_webdav(enable)`
启用或禁用 WebDAV。
- **参数**:
    - `enable` (bool): True 为启用，False 为禁用。
- **返回**: `Dict` 响应。

### `create_webdav_application(application_name)`
创建一个新的 WebDAV 应用凭证。
- **参数**:
    - `application_name` (str): 应用名称。
- **返回**: `Dict` 响应。

### `delete_webdav_application(username, password)`
删除一个 WebDAV 应用。
- **参数**:
    - `username` (str): WebDAV 用户名。
    - `password` (str): WebDAV 密码。
- **返回**: `Dict` 响应。

### `modify_webdav_application(username, password, modify_props)`
修改 WebDAV 应用。
- **参数**:
    - `username` (str): WebDAV 用户名。
    - `password` (str): WebDAV 密码。
    - `modify_props` (Dict): 要更改的属性 (例如 `{"read_only": True}`)。
- **返回**: `Dict` 响应。
