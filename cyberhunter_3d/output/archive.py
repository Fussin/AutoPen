import os
import pyzipper

def create_archive(output_dir: str, archive_path: str, encryption_key: str = None):
    """
    Creates a zip archive of the output files.
    If an encryption_key is provided, the archive will be encrypted.
    """
    if not os.path.exists(output_dir):
        print(f"Error: Output directory not found at {output_dir}")
        return

    if encryption_key:
        with pyzipper.AESZipFile(archive_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(encryption_key.encode())
            for root, _, files in os.walk(output_dir):
                for file in files:
                    zf.write(os.path.join(root, file),
                               os.path.relpath(os.path.join(root, file),
                                               os.path.join(output_dir, '..')))
    else:
        import zipfile
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    zipf.write(os.path.join(root, file),
                               os.path.relpath(os.path.join(root, file),
                                               os.path.join(output_dir, '..')))
