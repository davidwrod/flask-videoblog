from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Video, db, Model, Tag
from sqlalchemy import func

video_bp = Blueprint('video', __name__)

@video_bp.route('/video/<slug:slug>')
def video_view(slug):
    video = Video.query.filter_by(slug=slug).first_or_404()
    video.views += 1
    db.session.commit()

    if video.tags:
        tag_ids = [tag.id for tag in video.tags]
        related_videos = Video.query.filter(
            Video.id != video.id,
            Video.tags.any(Tag.id.in_(tag_ids))
        ).order_by(Video.uploaded_at.desc()).limit(6).all()
    else:
        related_videos = Video.query.filter(Video.id != video.id).order_by(func.random()).limit(12).all()

    return render_template('video_view.html', video=video, related_videos=related_videos)


@video_bp.route('/<int:video_id>/like', methods=['POST'])
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

@video_bp.route('/video/<slug:slug>/suggest_model', methods=['POST'])
@login_required
def suggest_model(slug):
    data = request.get_json()
    suggested_model_name = data.get('model', '').strip()

    if not suggested_model_name:
        return jsonify({'error': 'Nome da modelo é obrigatório'}), 400

    video = Video.query.filter_by(slug=slug).first_or_404()

    # Permissão
    if current_user.role not in ['admin', 'mod'] and current_user.id != video.user_id:
        return jsonify({'error': 'Você não tem permissão para alterar este vídeo'}), 403

    # Busca ou cria o modelo
    model_obj = Model.query.filter_by(name=suggested_model_name).first()
    if not model_obj:
        model_obj = Model(name=suggested_model_name)
        db.session.add(model_obj)
        db.session.commit()  # Para garantir que o model tenha id e slug

    # Verifica se o modelo já está associado
    if model_obj not in video.models:
        video.models.append(model_obj)
        db.session.commit()

    return jsonify({'success': True, 'message': 'Modelo sugerido atualizado com sucesso'})

