from flask import Flask
from dotenv import load_dotenv
from app.extensions import db, login_manager  # atualizado
from app.storage import get_file_url

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

    # Torna get_file_url disponível globalmente para todos os templates
    app.jinja_env.globals['get_thumbnail_url'] = get_file_url
    app.jinja_env.globals['get_video_url'] = get_file_url

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app

    