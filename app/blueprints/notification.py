from flask import Blueprint, jsonify, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app.models import db, Notification

notification_bp = Blueprint('notification', __name__, url_prefix='/notifications')

@notification_bp.route('/list')
@login_required
def list_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    data = [{
        'id': n.id,
        'message': n.message,
        'url': n.url,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d/%m/%Y %H:%M')
    } for n in notifs]
    return jsonify(data)

@notification_bp.route('/count')
@login_required
def count_notifications():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@notification_bp.route('/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_as_read(notification_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@notification_bp.route('/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@notification_bp.route('/')
@login_required
def notification_page():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifs)

def criar_notificacao(user_id, message, url=None):
    n = Notification(user_id=user_id, message=message, url=url)
    db.session.add(n)
    db.session.commit()