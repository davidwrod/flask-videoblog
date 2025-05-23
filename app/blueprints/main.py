from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Video, Model, Tag, User
from flask_login import login_required, current_user
from .. import db
from app.models import User, Video, Model, Tag, video_models
from app.storage import delete_file

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 30
    pagination = Video.query.order_by(Video.uploaded_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('home.html', videos=pagination.items, pagination=pagination)

@main_bp.route('/search')
def search():
    termo = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 30
    if not termo:
        flash("Digite algo para buscar.", "warning")
        return redirect(url_for('main.home'))
    pagination = Video.query.filter(Video.title.ilike(f"%{termo}%")).order_by(Video.uploaded_at.desc()).paginate(page=page, per_page=per_page)
    modelos = Model.query.filter(Model.name.ilike(f"%{termo}%")).all()
    tags = Tag.query.filter(Tag.name.ilike(f"%{termo}%")).all()
    return render_template('resultados_busca.html', termo=termo, videos=pagination.items, pagination=pagination, modelos=modelos, tags=tags)

@main_bp.route('/recentes')
def recentes():
    videos = Video.query.order_by(Video.uploaded_at.desc()).limit(50).all()
    return render_template('recentes.html', videos=videos)

@main_bp.route('/top-rated')
def top_rated():
    videos = Video.query.order_by(Video.like_count.desc()).limit(50).all()
    return render_template('top-rated.html', videos=videos)

@main_bp.route('/top-view')
def top_view():
    videos = Video.query.order_by(Video.views.desc()).limit(50).all()
    return render_template('top-view.html', videos=videos)

@main_bp.route('/tags')
def tags():
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('tags.html', tags=tags)

@main_bp.route('/tags/<slug>')
def tag_videos(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    videos = tag.videos.order_by(Video.uploaded_at.desc()).paginate(page=page, per_page=15)
    return render_template('tag_videos.html', tag=tag, videos=videos)

@main_bp.route('/modelos')
def modelos():
    modelos = Model.query.filter(Model.name != "Sem Nome").order_by(Model.name.asc()).all()
    return render_template('modelos.html', modelos=modelos)

@main_bp.route('/modelos/<slug>')
def perfil_modelo(slug):
    modelo = Model.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    
    # Query CORRETA para filtrar vídeos da modelo:
    videos = Video.query.join(Video.models)\
                .filter(Model.id == modelo.id)\
                .order_by(Video.uploaded_at.desc())\
                .paginate(page=page, per_page=15)
    
    return render_template('perfil_modelo.html', modelo=modelo, videos=videos)

@main_bp.route('/<username>')
def perfil_publico(username):
    user = User.query.filter_by(username=username).first_or_404()  # Primeiro encontra o usuário
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    # Filtra os vídeos do usuário específico e ordena por data de upload (mais recentes primeiro)
    pagination = Video.query.filter_by(user_id=user.id)\
                          .order_by(Video.uploaded_at.desc())\
                          .paginate(page=page, per_page=per_page)
    
    return render_template('perfil.html', 
                         user=user,  # Passa o usuário para o template
                         videos=pagination.items, 
                         pagination=pagination)

@main_bp.route('/edit_video_title/<int:video_id>', methods=['POST'])
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

def get_video_url(filename):
    from app.storage import get_file_url
    return get_file_url(filename)

def get_thumbnail_url(filename):
    from app.storage import get_file_url
    return get_file_url(f"thumbnails/{filename}")


@main_bp.route('/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)

    #  Verifica permissão
    if video.user_id != current_user.id and current_user.role != 'admin':
        flash("Você não tem permissão para deletar este vídeo.", "error")
        return redirect(url_for('main.home'))

    #  Captura modelos associados antes de deletar o vídeo
    associated_models = list(video.models)

    # Remove arquivo de vídeo do bucket
    if video.filename:
        video_object = f"videos/{video.filename}"
        if delete_file(video_object):
            print(f"[INFO] Vídeo removido do bucket: {video_object}")
        else:
            print(f"[WARNING] Não foi possível remover vídeo: {video_object}")

    # Remove thumbnail do bucket
    if video.thumbnail:
        thumbnail_object = f"thumbnails/{video.thumbnail}"
        if delete_file(thumbnail_object):
            print(f"[INFO] Thumbnail removida do bucket: {thumbnail_object}")
        else:
            print(f"[WARNING] Não foi possível remover thumbnail: {thumbnail_object}")

    # Remove o vídeo do banco
    db.session.delete(video)
    db.session.commit()

    # Verifica e remove modelos órfãos
    for model in associated_models:
        has_remaining_videos = db.session.query(
            db.session.query(Video)
            .join(video_models)
            .filter(video_models.c.model_id == model.id)
            .exists()
        ).scalar()

        if not has_remaining_videos:
            db.session.delete(model)
            print(f"[INFO] Modelo '{model.name}' removido pois ficou órfão.")

    db.session.commit()

    flash("Vídeo deletado com sucesso.", "success")
    return redirect(url_for('main.perfil_publico', username=current_user.username))

@main_bp.route('/autocomplete_modelos')
def autocomplete_modelos():
    termo = request.args.get('q', '')
    resultados = Model.query.filter(Model.name.ilike(f'%{termo}%')).limit(10).all()
    nomes = [modelo.name for modelo in resultados]
    return jsonify(nomes)

