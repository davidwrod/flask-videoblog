from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, Tag, Model

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/tags', methods=['GET', 'POST'])
@login_required
def manage_tags():
    if current_user.role != 'admin':
        return "Acesso negado. Apenas administradores."

    if request.method == 'POST':
        tag_name = request.form.get('name', '').strip()
        if tag_name and not Tag.query.filter_by(name=tag_name).first():
            new_tag = Tag(name=tag_name)
            db.session.add(new_tag)
            db.session.commit()
        return redirect(url_for('admin.manage_tags'))

    tags = Tag.query.order_by(Tag.name).all()
    return render_template('admin/manage_tags.html', tags=tags)

@login_required
@admin.route('/delete_tag/<int:tag_id>', methods=['POST'])
def delete_tag(tag_id):
    if current_user.role != 'admin':
        return "Acesso negado. Apenas administradores."

    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash(f"Tag '{tag.name}' excluída com sucesso.", 'success')
    return redirect(url_for('admin.manage_tags'))

@login_required
@admin.route('/unificar-modelos', methods=['GET', 'POST'])
def unificar_modelos():

    if current_user.role != 'admin':
        return "Acesso negado. Apenas administradores."

    modelos = Model.query.order_by(Model.name).all()

    if request.method == 'POST':
        modelo_origem_id = request.form.get('modelo_origem')
        modelo_destino_id = request.form.get('modelo_destino')

        if modelo_origem_id == modelo_destino_id:
            flash('Selecione modelos diferentes.', 'warning')
            return redirect(url_for('admin.unificar_modelos'))

        modelo_origem = Model.query.get(modelo_origem_id)
        modelo_destino = Model.query.get(modelo_destino_id)

        if not modelo_origem or not modelo_destino:
            flash('Modelos inválidos.', 'danger')
            return redirect(url_for('admin.unificar_modelos'))

        try:
            # Atualiza vídeos
            for video in modelo_destino.videos:
                video.models.append(modelo_origem)
                video.models.remove(modelo_destino)
                if not video.models:
                    video.models.append(modelo_origem)

            db.session.delete(modelo_destino)
            db.session.commit()
            flash(f'Unificação concluída! {len(modelo_destino.videos)} vídeos migrados.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'danger')

        return redirect(url_for('admin.unificar_modelos'))

    return render_template('admin/unificar_modelos.html', modelos=modelos)


