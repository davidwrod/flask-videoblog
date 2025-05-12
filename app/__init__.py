from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask_login import LoginManager


load_dotenv()

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app():
    app = Flask(__name__)

    app.config.from_object('config.Config')

    # Garante que a pasta exista
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    from .auth import auth
    app.register_blueprint(auth)

    from .routes import main
    app.register_blueprint(main)

    from .admin import admin
    app.register_blueprint(admin)

    from .modelos import modelos
    app.register_blueprint(modelos)

    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app

    