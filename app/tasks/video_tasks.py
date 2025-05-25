# app/tasks/video_tasks.py

import os
from app import db
from app.models import Video, Model, Tag, User
from app.celery import celery
from flask import current_app
import ffmpeg
from app.blueprints.upload import (
    compress_video_if_needed,
    calculate_file_hash,
    generate_thumbnail
)

from app.storage import upload_file  # importa seu método do storage.py

@celery.task(name='app.tasks.video_tasks.process_video_task')
def process_video_task(filepath, filename, user_id, model_names, tags_ids, title):
    from app import create_app
    app = create_app()
    with app.app_context():
        try:
            user = User.query.get(user_id)
            if not user:
                current_app.logger.error(f'Usuário {user_id} não encontrado para vídeo {filename}')
                return

            models = []
            for name in model_names:
                model = Model.query.filter_by(name=name).first()
                if not model:
                    model = Model(name=name)
                    db.session.add(model)
                    db.session.flush()
                models.append(model)

            probe = ffmpeg.probe(filepath)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                duration = float(video_stream.get('duration', 0))
                width = int(video_stream.get('width', 0))
                height = int(video_stream.get('height', 0))
            else:
                duration = width = height = 0

            compress_video_if_needed(filepath, width, height)

            file_hash = calculate_file_hash(filepath)
            size = os.path.getsize(filepath)

            thumbnail_filename = generate_thumbnail(filepath, filename, duration)
            thumbnail_path = os.path.join(current_app.root_path, 'static', 'thumbnails', thumbnail_filename)

            # Upload vídeo
            success_video = upload_file(filepath, filename)
            if not success_video:
                current_app.logger.error(f"Falha ao enviar vídeo '{filename}' para o bucket B2.")
                return

            # Upload thumbnail
            success_thumb = upload_file(thumbnail_path, f"thumbnails/{thumbnail_filename}")
            if not success_thumb:
                current_app.logger.error(f"Falha ao enviar thumbnail '{thumbnail_filename}' para o bucket B2.")
                return

            # Remove arquivos locais
            try:
                os.remove(filepath)
            except Exception as e:
                current_app.logger.warning(f"Não foi possível remover o vídeo local {filepath}: {e}")

            try:
                os.remove(thumbnail_path)
            except Exception as e:
                current_app.logger.warning(f"Não foi possível remover a thumbnail local {thumbnail_path}: {e}")

            video = Video(
                title=title,
                filename=filename,
                thumbnail=thumbnail_filename,
                user_id=user_id,
                hash=file_hash,
                size=size,
                duration=duration,
                width=width,
                height=height
            )
            video.models.extend(models)

            for tag_id in tags_ids:
                tag = Tag.query.get(tag_id)
                if tag:
                    video.tags.append(tag)

            db.session.add(video)
            db.session.commit()

            current_app.logger.info(f"Vídeo '{filename}' processado e enviado com sucesso.")
        except Exception as e:
            current_app.logger.error(f"Erro no processamento do vídeo '{filename}': {str(e)}")
