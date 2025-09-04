import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def upload_to_r2(logger, file_path=None, directory_path=None):
    """
    Uploads a file or a directory of files to a Cloudflare R2 bucket.
    """
    account_id = os.getenv('CF_R2_ACCOUNT_ID')
    access_key_id = os.getenv('CF_R2_ACCESS_KEY_ID')
    secret_access_key = os.getenv('CF_R2_SECRET_ACCESS_KEY')
    bucket_name = os.getenv('CF_R2_BUCKET')

    if not all([account_id, access_key_id, secret_access_key, bucket_name]):
        logger.info("Cloudflare R2 environment variables not set. Skipping upload.")
        return

    logger.info(f"Connecting to Cloudflare R2 bucket: {bucket_name}")

    s3_client = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name='auto' # R2 specific
    )

    # Upload a single file
    if file_path:
        try:
            object_name = os.path.basename(file_path)
            s3_client.upload_file(file_path, bucket_name, object_name)
            logger.info(f"Successfully uploaded {file_path} to {bucket_name}/{object_name}")
        except FileNotFoundError:
            logger.error(f"The file {file_path} was not found.")
        except NoCredentialsError:
            logger.error("Credentials not available for R2 upload.")
        except ClientError as e:
            logger.error(f"Failed to upload {file_path} to R2: {e}")

    # Upload all files in a directory
    if directory_path:
        if not os.path.isdir(directory_path):
            logger.error(f"The directory {directory_path} does not exist.")
            return

        for root, _, files in os.walk(directory_path):
            for filename in files:
                local_path = os.path.join(root, filename)
                # Create a relative path to be used as the object key in R2
                relative_path = os.path.relpath(local_path, directory_path)
                r2_object_key = f"{os.path.basename(directory_path)}/{relative_path}"

                try:
                    s3_client.upload_file(local_path, bucket_name, r2_object_key)
                    logger.info(f"Successfully uploaded {local_path} to {bucket_name}/{r2_object_key}")
                except FileNotFoundError:
                    logger.error(f"The file {local_path} was not found during directory walk.")
                except NoCredentialsError:
                    logger.error("Credentials not available for R2 upload.")
                    break # No need to try other files
                except ClientError as e:
                    logger.error(f"Failed to upload {local_path} to R2: {e}")
