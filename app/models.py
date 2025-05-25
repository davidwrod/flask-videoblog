from . import db
from datetime import datetime
from flask_login import UserMixin
from slugify import slugify
from sqlalchemy.orm import validates
from sqlalchemy import event

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

video_likes = db.Table('video_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id'), primary_key=True),
    db.Column('liked_at', db.DateTime, default=datetime.utcnow)
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

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255))  # Link opcional
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))


class Model(db.Model):
    __tablename__ = 'models'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=True)
    slug = db.Column(db.String(100), unique=True, nullable=True)

    videos = db.relationship('Video', secondary=video_models, back_populates='models')

    def generate_unique_slug(self, base_slug=None):
        """Gera um slug único, adicionando número se necessário"""
        if base_slug is None:
            base_slug = slugify(self.name) if self.name else ''
        
        if not base_slug:
            return None
            
        # Verifica se o slug já existe
        existing = Model.query.filter_by(slug=base_slug).first()
        if not existing or existing.id == self.id:
            return base_slug
        
        # Se existe, adiciona número
        counter = 1
        while True:
            new_slug = f"{base_slug}-{counter}"
            existing = Model.query.filter_by(slug=new_slug).first()
            if not existing:
                return new_slug
            counter += 1

    @validates('name')
    def generate_slug(self, key, value):
        if value:
            self.slug = self.generate_unique_slug(slugify(value))
        return value

    def __repr__(self):
        return f"Model('{self.name}', '{self.slug}')"


class Video(db.Model):
    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    thumbnail = db.Column(db.String(200), nullable=True)
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
    views = db.Column(db.Integer, default=0)
    likes = db.relationship('User', secondary=video_likes, backref='liked_videos')
    like_count = db.Column(db.Integer, default=0)

    def generate_unique_slug(self, base_slug=None):
        """Gera um slug único, adicionando número se necessário"""
        if base_slug is None:
            base_slug = slugify(self.title)
        
        # Verifica se o slug já existe
        existing = Video.query.filter_by(slug=base_slug).first()
        if not existing or existing.id == self.id:
            return base_slug
        
        # Se existe, adiciona número
        counter = 1
        while True:
            new_slug = f"{base_slug}-{counter}"
            existing = Video.query.filter_by(slug=new_slug).first()
            if not existing:
                return new_slug
            counter += 1

    @validates('title')
    def generate_slug(self, key, value):
        self.slug = self.generate_unique_slug(slugify(value))
        return value

    def get_absolute_url(self):
        """Retorna a URL completa do vídeo"""
        return f"/video/{self.slug}"
    
    def increment_views(self):
        """Incrementa o contador de visualizações"""
        self.views += 1
        db.session.commit()

    def __repr__(self):
        return f"Video('{self.title}', '{self.slug}')"


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)

    def generate_unique_slug(self, base_slug=None):
        """Gera um slug único, adicionando número se necessário"""
        if base_slug is None:
            base_slug = slugify(self.name)
        
        # Verifica se o slug já existe
        existing = Tag.query.filter_by(slug=base_slug).first()
        if not existing or existing.id == self.id:
            return base_slug
        
        # Se existe, adiciona número
        counter = 1
        while True:
            new_slug = f"{base_slug}-{counter}"
            existing = Tag.query.filter_by(slug=new_slug).first()
            if not existing:
                return new_slug
            counter += 1

    @validates('name')
    def generate_slug(self, key, value):
        self.slug = self.generate_unique_slug(slugify(value))
        return value

    def get_absolute_url(self):
        """Retorna a URL completa da tag"""
        return f"/tag/{self.slug}"

    def __repr__(self):
        return f"Tag('{self.name}', '{self.slug}')"


# Event listeners para garantir que os slugs sejam sempre únicos
@event.listens_for(Video, 'before_insert')
@event.listens_for(Video, 'before_update')
def ensure_video_slug(mapper, connection, target):
    if not target.slug and target.title:
        target.slug = target.generate_unique_slug()

@event.listens_for(Tag, 'before_insert')
@event.listens_for(Tag, 'before_update')
def ensure_tag_slug(mapper, connection, target):
    if not target.slug and target.name:
        target.slug = target.generate_unique_slug()

@event.listens_for(Model, 'before_insert')
@event.listens_for(Model, 'before_update')
def ensure_model_slug(mapper, connection, target):
    if not target.slug and target.name:
        target.slug = target.generate_unique_slug()