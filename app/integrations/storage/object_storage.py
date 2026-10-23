# Object storage abstraction (e.g. S3 / GCS)
from app.integrations.storage.local import local_storage

class ObjectStorage(type(local_storage)):
    pass

object_storage = local_storage
