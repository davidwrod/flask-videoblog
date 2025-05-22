import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Geral
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload local (usado apenas temporariamente antes de enviar para o bucket)
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    THUMBNAIL_FOLDER = os.path.join(basedir, 'static', 'thumbnails')

    # Backblaze B2
    B2_KEY_ID = os.environ.get('B2_KEY_ID')
    B2_APPLICATION_KEY = os.environ.get('B2_APPLICATION_KEY')
    B2_BUCKET_NAME = os.environ.get('B2_BUCKET_NAME')
    B2_ENDPOINT = os.environ.get('B2_ENDPOINT')

    # Celery
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERY_INCLUDE = ['app.tasks.video_tasks']
