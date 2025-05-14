from flask import render_template, request, redirect, url_for, flash, Blueprint, current_app, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from . import db
from .models import User, Video, Model, Tag
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

    if video.user_id != current_user.id:
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

    if video.user_id != current_user.id:
        flash("Você não tem permissão para deletar este vídeo.", "error")
        return redirect(url_for('main.home'))

# remover arquivo físico se estiver local
    filepath = os.path.join(current_app.root_path, 'static', 'uploads', video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(video)
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

@main.route('/upload/process', methods=['POST'])
@login_required
def upload_video():
    files = request.files.getlist('videos')
    model_names = request.form.getlist('models[]')  # Lista de modelos selecionadas/criadas

    if not files:
        flash("Faltam vídeos para upload.", "error")
        return redirect(url_for('main.upload_form'))

    # Se não veio nenhuma modelo, adiciona "Sem Nome"
    if not model_names:
        model_names = ["Sem Nome"]

    # Remover duplicatas preservando a ordem
    unique_model_names = []
    for name in model_names:
        name = name.strip()
        if name and name not in unique_model_names:
            unique_model_names.append(name)

    # Verificar ou criar os modelos
    models = []
    for name in unique_model_names:
        # Procurar a modelo no banco de dados
        model = Model.query.filter_by(name=name).first()
        if not model:
            # Criar nova modelo se não existir
            model = Model(name=name)
            db.session.add(model)
            db.session.flush()  # Não faz commit ainda
        models.append(model)

    db.session.commit()  # Confirma criação de modelos (se houver)

    videos_uploaded = 0
    for idx, file in enumerate(files):
        if not verificar_extensao_arquivo(file):
            flash(f'O arquivo "{file.filename}" tem uma extensão inválida.', 'error')
            return redirect(url_for('main.upload_form'))

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        file.save(filepath)

        # Extrair metadados do vídeo
        file_hash = calculate_file_hash(filepath)
        size = os.path.getsize(filepath)  # Tamanho em bytes
        
        # Gerar thumbnail do vídeo
        thumbnail_filename = generate_thumbnail(filepath, filename)
        
        try:
            # Usar ffmpeg para extrair propriedades do vídeo
            probe = ffmpeg.probe(filepath)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                # Extrair duração, largura e altura
                duration = float(video_stream.get('duration', 0))
                width = int(video_stream.get('width', 0))
                height = int(video_stream.get('height', 0))
            if not video_stream:
                # Se não encontrar stream de vídeo
                duration = 0
                width = 0
                height = 0
        except Exception as e:
            # Em caso de falha ao processar o vídeo, definir valores padrão
            current_app.logger.error(f"Erro ao processar vídeo {filename}: {str(e)}")
            duration = 0
            width = 0
            height = 0

        # Título por índice
        title = request.form.get(f'title_{idx}', filename)

        # Cria o vídeo e associa modelos (Muitos-para-Muitos)
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
        
        video.models.extend(models)  # Associa múltiplos modelos ao vídeo
        db.session.add(video)
        db.session.flush()  # Permite associar tags logo após

        # Coleta tags do vídeo atual
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

def calculate_file_hash(filepath):
    """Calcula o hash SHA-256 de um arquivo"""
    BUF_SIZE = 65536  # Ler em chunks de 64kb
    sha256 = hashlib.sha256()
    
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    
    return sha256.hexdigest()

def generate_thumbnail(video_path, video_filename):
    """Gera uma thumbnail para o vídeo e retorna o nome do arquivo"""
    # Criar um nome único para a thumbnail
    base_name = os.path.splitext(video_filename)[0]
    thumbnail_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.jpg"
    
    # Caminho para salvar a thumbnail
    thumbnails_dir = os.path.join(current_app.root_path, 'static', 'thumbnails')
    
    # Criar o diretório de thumbnails se não existir
    if not os.path.exists(thumbnails_dir):
        os.makedirs(thumbnails_dir)
    
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
    
    try:
        # Extrair o frame do meio do vídeo (cerca de 30% da duração)
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if video_stream and 'duration' in video_stream:
            duration = float(video_stream['duration'])
            time_position = duration * 0.3  # 30% do vídeo
        else:
            time_position = 1.0  # Se não conseguir ler a duração, usa 1 segundo
        
        # Usar o comando ffmpeg para extrair o frame e salvar como thumbnail
        subprocess.run([
            'ffmpeg', 
            '-ss', str(time_position),  # Tempo de início
            '-i', video_path,  # Arquivo de entrada
            '-vframes', '1',  # Extrair apenas 1 frame
            '-q:v', '2',  # Qualidade (2 é alta, sendo 1 o máximo)
            '-vf', 'scale=320:-1',  # Redimensionar para 320px de largura, altura proporcional
            thumbnail_path  # Caminho de saída
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return thumbnail_filename
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar thumbnail para {video_filename}: {str(e)}")
        return None  # Retorna None em caso de erro

@main.route('/autocomplete_modelos')
def autocomplete_modelos():
    termo = request.args.get('q', '')
    resultados = Model.query.filter(Model.name.ilike(f'%{termo}%')).limit(10).all()
    nomes = [modelo.name for modelo in resultados]
    return jsonify(nomes)