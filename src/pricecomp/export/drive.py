from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]  # drive.file no deja escribir en carpetas ya existentes
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def get_credentials(client_secret_path: Path, token_path: Path) -> Credentials:
    """Login OAuth con la cuenta del usuario; el token queda en `token_path` y se renueva solo."""
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES) if token_path.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not client_secret_path.exists():
            raise FileNotFoundError(f"Falta {client_secret_path} (cliente OAuth de Google Cloud, ver README)")
        creds = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES).run_local_server(port=0)
    token_path.write_text(creds.to_json())
    token_path.chmod(0o600)
    return creds


def upload_to_drive(file_path: Path, folder_id: str, client_secret_path: Path, token_path: Path) -> str:
    """Sube el archivo a la carpeta (o lo actualiza si ya existe con ese nombre). Devuelve el link."""
    if not folder_id:
        raise ValueError("DRIVE_FOLDER_ID no configurado (.env)")
    service = build("drive", "v3", credentials=get_credentials(client_secret_path, token_path), cache_discovery=False)
    media = MediaFileUpload(str(file_path), mimetype=XLSX_MIME)

    query = f"name = '{file_path.name}' and '{folder_id}' in parents and trashed = false"
    existing = service.files().list(q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()["files"]
    if existing:
        f = service.files().update(fileId=existing[0]["id"], media_body=media, fields="webViewLink", supportsAllDrives=True).execute()
    else:
        meta = {"name": file_path.name, "parents": [folder_id]}
        f = service.files().create(body=meta, media_body=media, fields="webViewLink", supportsAllDrives=True).execute()
    return f["webViewLink"]
