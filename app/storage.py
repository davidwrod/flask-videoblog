import os
import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

# Configurações
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
B2_ENDPOINT = os.getenv("B2_ENDPOINT")

# Conectar ao Backblaze
session = boto3.session.Session()

config = Config(
    signature_version='s3v4',
    retries={'max_attempts': 5, 'mode': 'standard'},
    s3={'use_checksums': False}  # <- ESSENCIAL pro B2
)

s3 = session.client(
    service_name='s3',
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APPLICATION_KEY,
    endpoint_url=B2_ENDPOINT,
    config=config
)

# Upload
def upload_file(file_path, object_name):
    try:
        with open(file_path, "rb") as f:
            s3.upload_fileobj(f, B2_BUCKET_NAME, object_name)
        print(f"[UPLOAD] {object_name} enviado com sucesso!")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao enviar {object_name}: {e}")
        return False


# Gerar URL pública (se o bucket for público)
def get_file_url(object_name):
    return f"{B2_ENDPOINT}/{B2_BUCKET_NAME}/{object_name}"


# Deletar
def delete_file(object_name):
    try:
        s3.delete_object(Bucket=B2_BUCKET_NAME, Key=object_name)
        print(f"[DELETE] {object_name} deletado do bucket.")
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao deletar {object_name}: {e}")
        return False


# Gerar URL temporária (se bucket for privado)
def generate_presigned_url(object_name, expiration=3600):
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': B2_BUCKET_NAME, 'Key': object_name},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f"[ERRO] Não foi possível gerar URL assinada: {e}")
        return None
