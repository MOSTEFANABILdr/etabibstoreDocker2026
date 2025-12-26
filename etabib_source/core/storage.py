import httplib2
from gdstorage.storage import GoogleDriveStorage, _ANYONE_CAN_READ_PERMISSION_, GoogleDriveFilePermission
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache
from oauth2client.service_account import ServiceAccountCredentials

from etabibWebsite import settings


class MemoryCache(Cache):
    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content


class CustomGoogleDriveStorage(GoogleDriveStorage):
    def __init__(self, json_keyfile_path=None,
                 permissions=None):
        """
        Handles credentials and builds the google service.

        :param _json_keyfile_path: Path
        :param user_email: String
        :raise ValueError:
        """
        self._json_keyfile_path = json_keyfile_path or settings.GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE

        credentials = ServiceAccountCredentials.from_json_keyfile_name(self._json_keyfile_path,
                                                                       scopes=["https://www.googleapis.com/auth/drive"])

        http = httplib2.Http()
        http = credentials.authorize(http)

        self._permissions = None
        if permissions is None:
            self._permissions = (_ANYONE_CAN_READ_PERMISSION_,)
        else:
            if not isinstance(permissions, (tuple, list,)):
                raise ValueError("Permissions should be a list or a tuple of GoogleDriveFilePermission instances")
            else:
                for p in permissions:
                    if not isinstance(p, GoogleDriveFilePermission):
                        raise ValueError(
                            "Permissions should be a list or a tuple of GoogleDriveFilePermission instances")
                # Ok, permissions are good
                self._permissions = permissions
        try:
            self._drive_service = build('drive', 'v2', http=http, cache=MemoryCache())
        except Exception as e:
            print(e)
            pass