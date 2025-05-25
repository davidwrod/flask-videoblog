from flask import Blueprint, request, redirect, url_for, flash, current_app, render_template, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Video, Model, Tag, Notification
from app.forms import EmptyForm
import os, subprocess, hashlib, uuid
import ffmpeg
import tempfile

upload_bp = Blueprint('upload', __name__)

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

def compress_video_if_needed(filepath, width, height, timeout=1200):
    try:
        probe = ffmpeg.probe(filepath)
        format_info = probe.get('format', {})
        bit_rate = int(format_info.get('bit_rate', 0)) or 0
    except Exception as e:
        current_app.logger.error(f"Erro ao obter bitrate para compressão: {str(e)}")
        bit_rate = 0

    resolution = min(width, height)

    # Limites baseados na resolução
    if resolution <= 480:
        limit_bps = 2_000_000
        crf = "27"
    elif resolution <= 720:
        limit_bps = 4_000_000
        crf = "24"
    elif resolution <= 1080:
        limit_bps = 8_000_000
        crf = "23"
    elif resolution <= 1440:  # 2K
        limit_bps = 15_000_000
        crf = "21"
    else:  # 4K ou maior
        limit_bps = 25_000_000
        crf = "20"

    current_app.logger.info(f"Arquivo: {filepath}")
    current_app.logger.info(f"Resolução detectada: {width}x{height} (avaliando {resolution}p)")
    current_app.logger.info(f"Bitrate detectado: {bit_rate} bps")
    current_app.logger.info(f"Limite para essa resolução: {limit_bps} bps")

    if bit_rate == 0:
        current_app.logger.warning("Bitrate não detectado, optando por NÃO comprimir por segurança.")
        return

    needs_compression = bit_rate > limit_bps

    if needs_compression:
        tmp_dir = os.path.join(current_app.root_path, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        temp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex[:12]}.mp4")

        cmd = [
            "ffmpeg", "-i", filepath,
            "-c:v", "libx264", "-preset", "slow", "-crf", crf,
            "-c:a", "aac", "-b:a", "128k",
            "-y", temp_path
        ]

        current_app.logger.info(f"Iniciando compressão: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, timeout=timeout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            current_app.logger.error(f"Compressão excedeu o tempo limite ({timeout}s) para {filepath}")
            raise

        if os.path.exists(temp_path):
            os.replace(temp_path, filepath)
            current_app.logger.info(f"Compressão concluída e arquivo substituído: {filepath}")
        else:
            current_app.logger.error(f"Falha na compressão, arquivo temporário não encontrado: {temp_path}")
            raise Exception("Compressão falhou.")
    else:
        current_app.logger.info("Compressão não necessária para este vídeo.")



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

    MAX_FILE_SIZE = 1.2 * 1024 * 1024 * 1024  # 1.2 GB
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    files = request.files.getlist('videos')
    model_names = request.form.getlist('models[]')

    if not files:
        msg = "Faltam vídeos para upload."
        if is_ajax:
            return jsonify({"status": "error", "message": msg}), 400
        flash(msg, "error")
        return redirect(url_for('main.upload_form'))

    if not model_names:
        model_names = ["Sem Nome"]

    unique_model_names = list({name.strip() for name in model_names if name.strip()})

    # Models
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
            msg = f'O arquivo "{file.filename}" tem uma extensão inválida.'
            if is_ajax:
                return jsonify({"status": "error", "message": msg}), 400
            flash(msg, 'error')
            return redirect(url_for('main.upload_form'))

        # 🔥 Verificar tamanho
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            url = url_for('main.perfil_publico', username=current_user.username)
            noti = Notification(
                user_id=current_user.id,
                message=f"O vídeo '{file.filename}' não foi enviado. Excede o limite de 1.2GB.",
                url=url
            )
            db.session.add(noti)
            db.session.commit()

            msg = f"O vídeo '{file.filename}' excede o limite de 1.2GB."

            if is_ajax:
                return jsonify({
                    "status": "error",
                    "message": msg,
                    "redirect_url": url
                }), 413

            flash(msg, 'error')
            continue

        filename = secure_filename(file.filename)

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_filepath = tmp_file.name

        file_hash = calculate_file_hash(tmp_filepath)
        video_existente = Video.query.filter_by(hash=file_hash).first()

        if video_existente:
            slug = video_existente.slug
            url = url_for('video.video_view', slug=slug)

            noti = Notification(
                user_id=current_user.id,
                message="O vídeo que você tentou enviar já existe. Clique aqui para ser redirecionado",
                url=url
            )
            db.session.add(noti)
            db.session.commit()

            if is_ajax:
                return jsonify({
                    "status": "duplicado",
                    "message": f"O vídeo '{filename}' já existe no sistema.",
                }), 409

            flash(f"O vídeo '{filename}' já existe. Verifique suas notificações.", "warning")
            os.remove(tmp_filepath)
            continue

        tags_ids = []
        for key in request.form.keys():
            if key.startswith(f'tags_{idx}_'):
                try:
                    tag_id = int(key.split('_')[-1])
                    tags_ids.append(tag_id)
                except ValueError:
                    continue

        title = request.form.get(f'title_{idx}', filename)

        process_video_task.delay(
            filepath=tmp_filepath,
            filename=filename,
            user_id=current_user.id,
            model_names=unique_model_names,
            tags_ids=tags_ids,
            title=title
        )

        videos_uploaded += 1

    msg = f"{videos_uploaded} vídeo{'s' if videos_uploaded > 1 else ''} enviado{'s' if videos_uploaded > 1 else ''} com sucesso. Seus vídeos estão sendo processados e serão publicados em breve."

#  Cria notificação
    n = Notification(
        user_id=current_user.id,
        message=msg,
        url=url_for('main.perfil_publico', username=current_user.username)
    )
    db.session.add(n)
    db.session.commit()

    #  Detecta se é requisição via AJAX (JS) ou formulário normal
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        return jsonify({
            "status": "success",
            "message": msg,
            "redirect_url": url_for('main.perfil_publico', username=current_user.username)
        }), 200

    #  Se for formulário tradicional (não XHR)
    flash(msg, "success")
    return redirect(url_for('main.perfil_publico', username=current_user.username))
