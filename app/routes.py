from flask import render_template, request, redirect, url_for, flash, Blueprint, current_app, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from . import db
from .models import User, Video, Model, Tag, video_models
from .forms import CadastroForm, LoginForm
from sqlalchemy.exc import IntegrityError
from flask_login import login_required, current_user
import os
import hashlib
import ffmpeg
import subprocess
import uuid

main = Blueprint('main', __name__)

@main.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 30  # vídeos por página
    pagination = Video.query.order_by(Video.uploaded_at.desc()).paginate(page=page, per_page=per_page)
    videos = pagination.items
    return render_template('home.html', videos=videos, pagination=pagination)

@main.route('/search')
def search():
    termo = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 30

    if not termo:
        flash("Digite algo para buscar.", "warning")
        return redirect(url_for('main.home'))

    pagination = Video.query.filter(Video.title.ilike(f"%{termo}%")) \
        .order_by(Video.uploaded_at.desc()) \
        .paginate(page=page, per_page=per_page)
    
    videos = pagination.items

    modelos = Model.query.filter(Model.name.ilike(f"%{termo}%")).all()
    tags = Tag.query.filter(Tag.name.ilike(f"%{termo}%")).all()

    return render_template('resultados_busca.html', termo=termo, videos=videos, pagination=pagination, modelos=modelos, tags=tags)

@main.route('/edit_video_title/<int:video_id>', methods=['POST'])
@login_required
def edit_video_title(video_id):
    video = Video.query.get_or_404(video_id)

    if video.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Sem permissão'}), 403

    data = request.get_json()
    new_title = data.get('new_title', '').strip()

    if not new_title:
        return jsonify({'error': 'Título vazio'}), 400

    video.title = new_title
    db.session.commit()
    return jsonify({'message': 'Título atualizado'})


@main.route('/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)

    # Verifica permissão
    if video.user_id != current_user.id and current_user.role != 'admin':
        flash("Você não tem permissão para deletar este vídeo.", "error")
        return redirect(url_for('main.home'))

    # Captura os modelos associados ANTES de deletar o vídeo
    associated_models = list(video.models)  # Faz uma cópia da lista

    # Remove arquivo físico (se aplicável)
    if video.filename:
        filepath = os.path.join(current_app.root_path, 'static', 'uploads', video.filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                flash(f"Erro ao remover arquivo: {str(e)}", "warning")

    # Deleta o vídeo
    db.session.delete(video)
    db.session.commit()

    # Verifica modelos órfãos
    for model in associated_models:
        # Verifica se a modelo ainda tem vídeos associados
        has_remaining_videos = db.session.query(
            db.session.query(Video)
            .join(video_models)
            .filter(video_models.c.model_id == model.id)
            .exists()
        ).scalar()

        if not has_remaining_videos:
            db.session.delete(model)
    
    db.session.commit()

    flash("Vídeo deletado com sucesso.", "success")
    return redirect(url_for('main.perfil_publico', username=current_user.username))

@main.route('/video/<int:video_id>')
def video_view(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
    db.session.commit()
    return render_template('video_view.html', video=video)

@main.route('/<username>')
def perfil_publico(username):
    user = User.query.filter_by(username=username).first_or_404()
    videos = user.videos
    return render_template('perfil.html', user=user, videos=videos)

@main.route('/login')
def login():
    form = LoginForm()
    return render_template('login.html', form=form, current_user = current_user)

@main.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    form = CadastroForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
        )
        try:
            db.session.add(user)
            db.session.commit()
            flash('Cadastro realizado com sucesso!', 'success')
            return redirect(url_for('main.home'))
        except IntegrityError:
            db.session.rollback()
            flash('Esse nome de usuário ou e-mail já está em uso. Escolha outro.', 'danger')
            return redirect(url_for('main.cadastro'))  # ou o nome da rota com o formulário

    return render_template('form_cadastro.html', form=form, current_user = current_user)

@main.route('/tags')
def tags():
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('tags.html', tags=tags)

@main.route('/tags/<tag_name>')
def tag_videos(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    page = request.args.get('page', 1, type=int)
    videos = tag.videos.order_by(Video.uploaded_at.desc()).paginate(page=page, per_page=15)
    return render_template('tag_videos.html', tag=tag, videos=videos)

@main.route('/modelos')
def modelos():
    modelos = Model.query.filter(Model.name != "Sem Nome").order_by(Model.name.asc()).all()
    return render_template('modelos.html', modelos=modelos)

@main.route('/video/<int:video_id>/like', methods=['POST'])
@login_required
def like_video(video_id):
    video = Video.query.get_or_404(video_id)
    action = None

    if current_user in video.likes:
        video.likes.remove(current_user)
        video.like_count -= 1
        action = 'unliked'
    else:
        video.likes.append(current_user)
        video.like_count += 1
        action = 'liked'
    
    db.session.commit()
    return jsonify({
        'status': action,
        'likes': video.like_count  # Agora usa o campo otimizado
    })

@main.route('/top-rated')
def top_rated():
    videos = Video.query.order_by(Video.like_count.desc()).limit(50).all()
    return render_template('top-rated.html', videos=videos)

@main.route('/top-view')
def top_view():
    videos = Video.query.order_by(Video.views.desc()).limit(50).all()
    return render_template('top-view.html', videos=videos)

@main.route('/recentes')
def recentes():
    # Buscar vídeos mais recentes (últimos 50)
    videos = Video.query.order_by(Video.uploaded_at.desc()).limit(50).all()
    return render_template('recentes.html', videos=videos)

@main.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_form():
    if request.method == 'POST':  # Quando for POST, chama o upload_video
        return upload_video()
    
    # Quando for GET, renderiza o formulário
    models = Model.query.all()
    tags = Tag.query.all()  # Carregar todas as tags existentes

    serialized_tags = [{'id': tag.id, 'name': tag.name} for tag in tags]

    return render_template('upload_form.html', models=models, tags=serialized_tags, current_user = current_user)

def verificar_extensao_arquivo(arquivo):
    EXTENSOES_PERMITIDAS = {'mp4', 'webm', 'mkv', 'mov', 'avi'}
    if '.' in arquivo.filename:
        extensao = arquivo.filename.rsplit('.', 1)[1].lower()
        if extensao in EXTENSOES_PERMITIDAS:
            return True
    return False

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

def generate_thumbnail(video_path, video_filename, duration):
    base_name = os.path.splitext(video_filename)[0]
    thumbnail_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.jpg"
    thumbnails_dir = os.path.join(current_app.root_path, 'static', 'thumbnails')
    if not os.path.exists(thumbnails_dir):
        os.makedirs(thumbnails_dir)
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
    try:
        if duration > 0:
            time_position = duration * 0.3
        else:
            time_position = 1.0
        subprocess.run([
            'ffmpeg', '-ss', str(time_position), '-i', video_path,
            '-vframes', '1', '-q:v', '2', '-vf', 'scale=320:-1', thumbnail_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return thumbnail_filename
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar thumbnail para {video_filename}: {str(e)}")
        return None

def compress_video_if_needed(filepath, width, height):
    original_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    # Pega bitrate médio diretamente do ffprobe
    try:
        probe = ffmpeg.probe(filepath)
        format_info = probe.get('format', {})
        bit_rate = int(format_info.get('bit_rate', 0))
    except Exception as e:
        current_app.logger.error(f"Erro ao obter bitrate para compressão: {str(e)}")
        bit_rate = 0

    resolution = max(width, height)
    # Limites em bits por segundo (bps)
    if resolution <= 480:
        limit_bps = 2 * 1024 * 1024  # 2 Mbps
        crf = "27"
    elif resolution <= 720:
        limit_bps = 4 * 1024 * 1024  # 4 Mbps
        crf = "24"
    elif resolution <= 1080:
        limit_bps = 8 * 1024 * 1024  # 8 Mbps
        crf = "23"
    else:
        limit_bps = float('inf')
        crf = "21"

    # Se bitrate maior que limite, ou resolução > 1080p, comprimir
    if bit_rate > limit_bps or resolution > 1080:
        tmp_dir = os.path.join(current_app.root_path, 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        temp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex[:12]}.mp4")
        cmd = [
            "ffmpeg", "-i", filepath,
            "-c:v", "libx264", "-preset", "slow", "-crf", crf,
            "-c:a", "aac", "-b:a", "128k",
            "-y", temp_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_path):
            os.replace(temp_path, filepath)


@main.route('/upload/process', methods=['POST'])
@login_required
def upload_video():
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
        filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        file.save(filepath)
        try:
            probe = ffmpeg.probe(filepath)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                duration = float(video_stream.get('duration', 0))
                width = int(video_stream.get('width', 0))
                height = int(video_stream.get('height', 0))
            else:
                duration = width = height = 0
        except Exception as e:
            current_app.logger.error(f"Erro ao processar vídeo {filename}: {str(e)}")
            duration = width = height = 0

        # Agora só passa largura e altura para compressão
        compress_video_if_needed(filepath, width, height)

        file_hash = calculate_file_hash(filepath)
        size = os.path.getsize(filepath)
        thumbnail_filename = generate_thumbnail(filepath, filename, duration)  # Passa duração para miniatura

        title = request.form.get(f'title_{idx}', filename)
        video = Video(
            title=title,
            filename=filename,
            thumbnail=thumbnail_filename,
            user_id=current_user.id,
            hash=file_hash,
            size=size,
            duration=duration,
            width=width,
            height=height
        )
        video.models.extend(models)
        db.session.add(video)
        db.session.flush()

        video_tags = []
        for key in request.form.keys():
            if key.startswith(f'tags_{idx}_'):
                try:
                    tag_id = int(key.split('_')[-1])
                    tag = Tag.query.get(tag_id)
                    if tag:
                        video_tags.append(tag)
                except ValueError:
                    continue
        for tag in video_tags:
            video.tags.append(tag)
        videos_uploaded += 1

    db.session.commit()
    if videos_uploaded == 1:
        flash("1 vídeo foi enviado com sucesso!", "success")
    if videos_uploaded > 1:
        flash(f"{videos_uploaded} vídeos foram enviados com sucesso!", "success")
    return redirect(url_for('main.perfil_publico', username=current_user.username))


@main.route('/autocomplete_modelos')
def autocomplete_modelos():
    termo = request.args.get('q', '')
    resultados = Model.query.filter(Model.name.ilike(f'%{termo}%')).limit(10).all()
    nomes = [modelo.name for modelo in resultados]
    return jsonify(nomes)