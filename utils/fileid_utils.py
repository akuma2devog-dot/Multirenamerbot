import os
import shutil
import uuid

def force_new_file(path: str):
    """
    Touch metadata to force new file_id
    """
    new_path = f"{uuid.uuid4()}_{os.path.basename(path)}"
    shutil.copy(path, new_path)
    return new_path
