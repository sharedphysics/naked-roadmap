from datetime import datetime, timezone, date
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from colorama import Fore, Style
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    def __repr__(self):
        return '<User {}>'.format(self.username)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    created: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    content: so.Mapped[str] = so.mapped_column(sa.TEXT())
    title: so.Mapped[str] = so.mapped_column(sa.TEXT())
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return '<Post {}>'.format(self.body)

class Project(db.Model):
    __tablename__ = "project"
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.TEXT())
    created: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    dri: so.Mapped[str] = so.mapped_column(sa.TEXT())
    team: so.Mapped[str] = so.mapped_column(sa.TEXT())
    context: so.Mapped[str] = so.mapped_column(sa.TEXT())
    why: so.Mapped[str] = so.mapped_column(sa.TEXT())
    requirements: so.Mapped[str] = so.mapped_column(sa.TEXT())
    launch: so.Mapped[str] = so.mapped_column(sa.TEXT())
    location: so.Mapped[str] = so.mapped_column(sa.TEXT(),  nullable=True, default="discussion")
    type: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    status: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True, default="Active")
    # Foreign keys
    objective_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=True)
    # Relationships
    objective = db.relationship('Goal', backref=db.backref('projects', lazy='dynamic'))
    
    def __repr__(self):
        return '<Project {}>'.format(self.name)
        
# TODO: Rename to be Objectives
class Goal(db.Model):
    __tablename__ = "goal"
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    created: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    title: so.Mapped[str] = so.mapped_column(sa.TEXT())
    requested_by: so.Mapped[str] = so.mapped_column(sa.TEXT())
    details: so.Mapped[str] = so.mapped_column(sa.TEXT())
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    status: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True, default="Active")
    completed: so.Mapped[datetime] = so.mapped_column(nullable=True)
    
    def __repr__(self):
        return '<Goal {}>'.format(self.title)
    
    def __repr__(self):
        return '<Request {}>'.format(self.body)

class Sprint(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    created: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    title: so.Mapped[str] = so.mapped_column(sa.TEXT())
    date_start: so.Mapped[date] = so.mapped_column(index=True)
    date_end: so.Mapped[date] = so.mapped_column(index=True)
    goals: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    status: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    
    def __repr__(self):
        return '<Sprint {}>'.format(self.body)

# TODO: Rename to be commitments
# https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.rename_table
class SprintProjectMap(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    added: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    sprint_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Sprint.id), index=True)
    project_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Project.id), index=True)
    goal: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    status: so.Mapped[str] = so.mapped_column(sa.TEXT(), default="Planned")
    order: so.Mapped[int] = so.mapped_column(nullable=True, autoincrement=True)
    project = db.relationship("Project", backref="sprint_mappings")
    sprint = db.relationship("Sprint", backref="project_mappings")
    critical: so.Mapped[bool] = so.mapped_column(default=False, nullable=True)
    
    def __repr__(self):
        return '<Sprint/Project Map {}>'.format(self.body)

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('comments', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Comment {self.id} by User {self.user_id} on Project {self.project_id}>'

class Changelog(db.Model):
    __tablename__ = 'changelogs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    change_type = db.Column(db.String(50), nullable=False)  # 'create', 'edit', 'sprint_assignment', etc.
    content = db.Column(db.Text, nullable=False)  # Description of what changed
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('changelogs', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('changelogs', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Changelog {self.id}: {self.change_type} by User {self.user_id} on Project {self.project_id}>'
        
        
class AppConfig(db.Model):
    """
    Configuration settings for the application stored as key-value pairs
    """
    __tablename__ = 'app_config'
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    key: so.Mapped[str] = so.mapped_column(sa.String(100), index=True, unique=True)
    value: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    description: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    created: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    updated: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc), 
                                                   onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<AppConfig {self.key}>'
    
# Helper functions to get and set configuration values
def get_config(key, default=None):
    """Get a configuration value by key"""
    config = db.session.query(AppConfig).filter(AppConfig.key == key).first()
    return config.value if config else default

def set_config(key, value, description=None):
    """Set a configuration value"""
    config = db.session.query(AppConfig).filter(AppConfig.key == key).first()
    if config:
        config.value = value
        config.updated = datetime.now(timezone.utc)
        if description and not config.description:
            config.description = description
    else:
        config = AppConfig(key=key, value=value, description=description)
        db.session.add(config)
    db.session.commit()
    return config