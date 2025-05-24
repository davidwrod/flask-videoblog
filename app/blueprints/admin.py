from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import db, Tag, Model

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/tags', methods=['GET', 'POST'])
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
@admin_bp.route('/delete_tag/<int:tag_id>', methods=['POST'])
def delete_tag(tag_id):
    if current_user.role != 'admin':
        return "Acesso negado. Apenas administradores."

    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash(f"Tag '{tag.name}' excluída com sucesso.", 'success')
    return redirect(url_for('admin.manage_tags'))

@login_required
@admin_bp.route('/unificar-modelos', methods=['GET', 'POST'])
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

@admin_bp.route('/adminpanel')
@login_required
def admin_panel():
    # Aqui você pode checar se o usuário tem permissão de admin
    if current_user.role != 'admin':
        return "Acesso negado", 403
    
    # Renderize o template da página do painel admin
    return render_template('admin/adminpanel.html')

@admin_bp.route('/modelos', methods=['GET', 'POST'])
@login_required
def manage_modelos():
    if current_user.role != 'admin':
        return "Acesso negado. Apenas administradores.", 403

    if request.method == 'POST':
        modelo_name = request.form.get('name', '').strip()

        if modelo_name and not Model.query.filter_by(name=modelo_name).first():
            new_modelo = Model(name=modelo_name)
            db.session.add(new_modelo)
            db.session.commit()
            flash(f"Modelo '{modelo_name}' criado com sucesso.", 'success')
        return redirect(url_for('admin.manage_modelos'))

    modelos = Model.query.order_by(Model.name).all()
    return render_template('admin/manage_modelos.html', modelos=modelos)


@admin_bp.route('/edit_modelo/<int:modelo_id>', methods=['POST'])
@login_required
def edit_modelo(modelo_id):
    if current_user.role != 'admin':
        return "Acesso negado. Apenas administradores.", 403

    modelo = Model.query.get_or_404(modelo_id)
    new_name = request.form.get('new_name', '').strip()

    if new_name:
        modelo.name = new_name
        db.session.commit()
        flash(f"Modelo atualizado para '{new_name}'.", 'success')

    return redirect(url_for('admin.manage_modelos'))


@admin_bp.route('/delete_modelo/<int:modelo_id>', methods=['POST'])
@login_required
def delete_modelo(modelo_id):
    if current_user.role != 'admin':
        return "Acesso negado. Apenas administradores.", 403

    modelo = Model.query.get_or_404(modelo_id)

    # Remove a associação dos vídeos antes de excluir
    for video in modelo.videos:
        video.models.remove(modelo)

    db.session.delete(modelo)
    db.session.commit()
    flash(f"Modelo '{modelo.name}' excluído com sucesso.", 'success')

    return redirect(url_for('admin.manage_modelos'))
