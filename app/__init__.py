from flask import Flask
from dotenv import load_dotenv
from app.extensions import db, login_manager  # atualizado
from app.blueprints.main import get_thumbnail_url, get_video_url, time_since
from werkzeug.routing import BaseConverter
from flask_wtf import CSRFProtect

class SlugConverter(BaseConverter):
    regex = r'[a-zA-Z0-9_-]+'

load_dotenv()

from flask_login import LoginManager  # Pode remover depois que confirmar que está tudo certo

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Garante que a pasta de upload exista
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    app.url_map.converters['slug'] = SlugConverter

    csrf = CSRFProtect()
    csrf.init_app(app)

    from app.blueprints.main import main_bp
    from app.blueprints.upload import upload_bp
    from app.blueprints.video import video_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    from app.models import User

    app.jinja_env.globals['get_thumbnail_url'] = get_thumbnail_url
    app.jinja_env.globals['get_video_url'] = get_video_url
    app.jinja_env.filters['time_since'] = time_since

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app

    