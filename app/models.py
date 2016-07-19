from datetime import datetime
from flask.ext.moment import Moment
import hashlib
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from flask.ext.login import UserMixin, AnonymousUserMixin
from app.exceptions import ValidationError
from . import db, login_manager
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

class Permission:
    LOOKUP = 0x01
    ALTER = 0x10
    ADMINISTER = 0xff


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.LOOKUP |
                     Permission.ALTER, True),
            'Administrator': (Permission.ADMINISTER, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    branchname = db.Column(db.String(128), unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow())
    recharges = db.relationship('Recharge', backref='changer', lazy='dynamic')
    consumes = db.relationship('Consume', backref='changer', lazy='dynamic')
    cards = db.relationship('Card', backref='owner', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.username == 'admin':
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    @property
    def password(self):
        raise AttributeError('密码属性不可读')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def insert_admin():
        admin_user = User(username='admin', password='root', branchname='head')
        db.session.add(admin_user)
        db.session.commit()

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Card(db.Model):
    __tablename__ = 'cards'
    id = db.Column(db.Integer, primary_key=True)
    cardnumber = db.Column(db.String(32), index=True, unique=True)
    remaining = db.Column(db.Float, default=0.0)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recharges = db.relationship('Recharge', backref='cards', lazy='dynamic')
    consumes = db.relationship('Consume', backref='cards', lazy='dynamic')

class Recharge(db.Model):
    __tablename__ = 'recharges'
    id = db.Column(db.Integer, primary_key=True)
    changer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'))
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'))
    consumer_pay = db.Column(db.Float, nullable=False)
    into_card = db.Column(db.Float, nullable=False)
    change_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Recharge, self).__init__(**kwargs)
        card = Card.query.filter_by(id=self.card_id).one()
        if card:
            card.remaining = card.remaining + self.into_card
            db.session.commit()


class Consume(db.Model):
    __tablename__ = 'consumes'
    id = db.Column(db.Integer, primary_key=True)
    changer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'))
    expense = db.Column(db.Float, nullable=False)
    change_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Consume, self).__init__(**kwargs)
        card = Card.query.filter_by(id=self.card_id).one()
        if card.remaining:
            card.remaining = card.remaining - self.expense
            db.session.commit()


class Campaign(db.Model):
    __tablename__ = 'campaigns'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    consumer_pay = db.Column(db.Integer)
    into_card = db.Column(db.Integer)
    recharges = db.relationship('Recharge', backref='campaigns', lazy='dynamic')