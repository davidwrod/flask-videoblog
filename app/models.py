from . import db
from datetime import datetime
from flask_login import UserMixin

# Tabela de associação entre vídeos e tags
video_tags = db.Table('video_tags',
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

# Tabela de associação entre vídeos e modelos (muitos-para-muitos)
video_models = db.Table('video_models',
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id'), primary_key=True),
    db.Column('model_id', db.Integer, db.ForeignKey('models.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    role = db.Column(db.String(20), default='user', nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"

class Model(db.Model):
    __tablename__ = 'models'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=True)

    videos = db.relationship('Video', secondary=video_models, back_populates='models')

class Video(db.Model):
    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    thumbnail = db.Column(db.String(200), nullable=True)  # Nome do arquivo da thumbnail
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='videos')
    tags = db.relationship('Tag', secondary=video_tags, backref=db.backref('videos', lazy='dynamic'))
    models = db.relationship('Model', secondary=video_models, back_populates='videos')
    hash = db.Column(db.String(64), unique=True, nullable=False)
    size = db.Column(db.Integer)
    duration = db.Column(db.Float)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"Tag('{self.name}')"
