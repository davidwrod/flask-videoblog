from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Video, db

video_bp = Blueprint('video', __name__)

@video_bp.route('/video/<int:video_id>')
def video_view(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
    db.session.commit()
    return render_template('video_view.html', video=video)

@video_bp.route('/edit_video_title', methods=['POST'])
@login_required
def edit_video_title():
    video_id = request.form.get('video_id')
    new_title = request.form.get('new_title', '').strip()
    video = Video.query.get_or_404(video_id)

    if not new_title or len(new_title) > 150:
        flash("Título inválido", "error")
        return redirect(url_for('video.video_view', video_id=video_id))

    if video.user_id != current_user.id:
        flash("Você não tem permissão para editar este vídeo.", "error")
        return redirect(url_for('video.video_view', video_id=video_id))
    if new_title:
        video.title = new_title
        db.session.commit()
        flash("Título atualizado com sucesso!", "success")
    return redirect(url_for('video.video_view', video_id=video_id))

@video_bp.route('/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    if video.user_id != current_user.id:
        flash("Você não tem permissão para deletar este vídeo.", "error")
        return redirect(url_for('video.video_view', video_id=video_id))
    db.session.delete(video)
    db.session.commit()
    flash("Vídeo deletado com sucesso.", "success")
    return redirect(url_for('main.perfil_publico', username=current_user.username))

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