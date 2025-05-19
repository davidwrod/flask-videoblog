from celery import Celery
from flask import Flask
from app import create_app  # <-- CORRETO
from app.extensions import db  # opcional, caso use db nas tasks

def make_celery(app: Flask):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND'],
        include=app.config.get('CELERY_INCLUDE', [])
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


flask_app = create_app()
celery = make_celery(flask_app)
