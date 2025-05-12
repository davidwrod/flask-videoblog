from . import db
from .models import User, Video, Model, Tag
from flask import render_template, request, redirect, url_for, flash, Blueprint, current_app, jsonify

modelos = Blueprint('modelos', __name__, url_prefix='/modelos')

@modelos.route('/<name>')
def perfil_modelo(name):
    modelo = Model.query.filter_by(name=name).first_or_404()
    page = request.args.get('page', 1, type=int)
    
    # Query CORRETA para filtrar vídeos da modelo:
    videos = Video.query.join(Video.models)\
                .filter(Model.id == modelo.id)\
                .order_by(Video.uploaded_at.desc())\
                .paginate(page=page, per_page=15)
    
    return render_template('blueprint_modelos/perfil_modelo.html', modelo=modelo, videos=videos)

