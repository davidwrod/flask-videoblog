from flask import Blueprint, request, redirect, url_for, flash, current_app, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Video, Model, Tag
from app.forms import EmptyForm
import os, subprocess, hashlib, uuid
import ffmpeg
import tempfile

upload_bp = Blueprint('upload', __name__)

COMPRESS_PROFILES = {
    "480p": {
        "max_bitrate": 2_000_000,  # 2 Mbps
        "crf": 27,
        "timeout": 300  # 5 minutos
    },
    "720p": {
        "max_bitrate": 4_000_000,  # 4 Mbps
        "crf": 24,
        "timeout": 600  # 10 minutos
    },
    "1080p": {
        "max_bitrate": 8_000_000,  # 8 Mbps
        "crf": 23,
        "timeout": 1200  # 20 minutos
    },
    "4K": {
        "max_bitrate": 16_000_000,  # 16 Mbps
        "crf": 21,
        "timeout": 3600  # 1 hora
    }
}

def calculate_file_hash(filepath):
    BUF_SIZE = 65536
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def verificar_extensao_arquivo(arquivo):
    EXTENSOES_PERMITIDAS = {'mp4', 'webm', 'mkv', 'mov', 'avi'}
    if '.' in arquivo.filename:
        extensao = arquivo.filename.rsplit('.', 1)[1].lower()
        if extensao in EXTENSOES_PERMITIDAS:
            return True
    return False

def generate_thumbnail(video_path, video_filename, duration):
    base_name = os.path.splitext(video_filename)[0]
    thumbnail_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.jpg"
    thumbnails_dir = os.path.join(current_app.root_path, 'static', 'thumbnails')
    if not os.path.exists(thumbnails_dir):
        os.makedirs(thumbnails_dir)
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
    try:
        time_position = duration * 0.3 if duration > 0 else 1.0
        subprocess.run([
            'ffmpeg', '-ss', str(time_position), '-i', video_path,
            '-vframes', '1', '-q:v', '2', '-vf', 'scale=320:-1', thumbnail_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return thumbnail_filename
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar thumbnail para {video_filename}: {str(e)}")
        return None

def compress_video_if_needed(filepath, width, height):
    try:
        probe = ffmpeg.probe(filepath)
        format_info = probe.get('format', {})
        bit_rate = int(format_info.get('bit_rate', 0))
    except Exception as e:
        current_app.logger.error(f"Erro ao obter bitrate para compressão: {str(e)}")
        bit_rate = 0

    resolution = max(width, height)
    if resolution <= 480:
        limit_bps = 2_000_000
        crf = "27"
    elif resolution <= 720:
        limit_bps = 4_000_000
        crf = "24"
    elif resolution <= 1080:
        limit_bps = 8_000_000
        crf = "23"
    else:
        limit_bps = float('inf')
        crf = "21"

    if bit_rate > limit_bps or resolution > 1080:
        tmp_dir = os.path.join(current_app.root_path, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        temp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex[:12]}.mp4")
        cmd = ["ffmpeg", "-i", filepath, "-c:v", "libx264", "-preset", "slow", "-crf", crf,
               "-c:a", "aac", "-b:a", "128k", "-y", temp_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_path):
            os.replace(temp_path, filepath)

@upload_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_form():
    form = EmptyForm()
    if form.validate_on_submit():
        # Se o POST for válido (incluindo CSRF), chama upload_video
        return upload_video()

    # Se for GET ou form inválido, renderiza o formulário
    models = Model.query.all()
    tags = Tag.query.all()
    serialized_tags = [{'id': tag.id, 'name': tag.name} for tag in tags]

    return render_template(
        'upload_form.html',
        form=form,
        models=models,
        tags=serialized_tags,
        current_user=current_user
    )

def verificar_extensao_arquivo(arquivo):
    EXTENSOES_PERMITIDAS = {'mp4', 'webm', 'mkv', 'mov', 'avi'}
    if '.' in arquivo.filename:
        extensao = arquivo.filename.rsplit('.', 1)[1].lower()
        if extensao in EXTENSOES_PERMITIDAS:
            return True
    return False

@upload_bp.route('/upload/process', methods=['POST'])
@login_required
def upload_video():
    from app.tasks.video_tasks import process_video_task

    files = request.files.getlist('videos')
    model_names = request.form.getlist('models[]')

    if not files:
        flash("Faltam vídeos para upload.", "error")
        return redirect(url_for('main.upload_form'))

    if not model_names:
        model_names = ["Sem Nome"]

    unique_model_names = []
    for name in model_names:
        name = name.strip()
        if name and name not in unique_model_names:
            unique_model_names.append(name)

    # Garante que os models existem no banco
    models = []
    for name in unique_model_names:
        model = Model.query.filter_by(name=name).first()
        if not model:
            model = Model(name=name)
            db.session.add(model)
            db.session.flush()
        models.append(model)
    db.session.commit()

    videos_uploaded = 0
    for idx, file in enumerate(files):
        if not verificar_extensao_arquivo(file):
            flash(f'O arquivo "{file.filename}" tem uma extensão inválida.', 'error')
            return redirect(url_for('main.upload_form'))

        filename = secure_filename(file.filename)

        # Salva temporariamente para processar
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_filepath = tmp_file.name

        # Coleta IDs das tags associadas a esse vídeo (índice idx)
        tags_ids = []
        for key in request.form.keys():
            if key.startswith(f'tags_{idx}_'):
                try:
                    tag_id = int(key.split('_')[-1])
                    tags_ids.append(tag_id)
                except ValueError:
                    continue

        title = request.form.get(f'title_{idx}', filename)

        # Chama tarefa celery para processar, compressão, thumbnail etc.
        process_video_task.delay(
            filepath=tmp_filepath,
            filename=filename,
            user_id=current_user.id,
            model_names=unique_model_names,
            tags_ids=tags_ids,
            title=title
        )

        videos_uploaded += 1

    if videos_uploaded == 1:
        flash("1 vídeo foi enviado com sucesso!", "success")
    elif videos_uploaded > 1:
        flash(f"{videos_uploaded} vídeos foram enviados com sucesso!", "success")

    return redirect(url_for('main.perfil_publico', username=current_user.username))

