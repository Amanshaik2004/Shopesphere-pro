import os
import uuid
from fastapi import UploadFile
from app.core.config import settings
from app.core.exceptions import BadRequestError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".csv", ".xlsx"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

class LocalStorage:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_file(self, file: UploadFile) -> str:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise BadRequestError(f"Unsupported file extension: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

        file_id = uuid.uuid4().hex
        filename = f"{file_id}{ext}"
        destination = os.path.join(self.upload_dir, filename)

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise BadRequestError(f"File size exceeds maximum {settings.MAX_UPLOAD_SIZE_MB}MB limit")

        with open(destination, "wb") as f:
            f.write(content)

        return f"/uploads/{filename}"

local_storage = LocalStorage()
