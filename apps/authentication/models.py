# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import abort
from flask_login import UserMixin, current_user
from apps import db, login_manager
from flask_admin.contrib.sqla import ModelView
from apps.authentication.util import hash_pass
from sqlalchemy.exc import SQLAlchemyError
from apps.exceptions.exception import InvalidUsage
import datetime as dt
from sqlalchemy.orm import relationship
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from apps.config import Config

RoleType = Config.USERS_ROLES
Status   = Config.USERS_STATUS
VERIFIED_EMAIL = Config.VERIFIED_EMAIL

class Users(db.Model, UserMixin):

    __tablename__ = 'users'
    
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(64), unique=True)
    email           = db.Column(db.String(100), unique=True)
    password        = db.Column(db.LargeBinary)
    
    role            = db.Column(db.Integer(),
                        default=RoleType['USER'], nullable=False)
    status          = db.Column(db.Integer(),
                        default=Status['ACTIVE'], nullable=False)
    failed_logins   = db.Column(db.Integer(), default=0)

    api_token       = db.Column(db.String(100))
    api_token_ts    = db.Column(db.String(100))
    
    verified_email  = db.Column(db.Integer(),   default=VERIFIED_EMAIL['not-verified'], nullable=False)
    
    oauth_twitter   = db.Column(db.String(100), nullable=True)
    oauth_github    = db.Column(db.String(100), nullable=True)
    
    date_created    = db.Column(db.DateTime, default=dt.datetime.utcnow())
    date_modified   = db.Column(db.DateTime, default=db.func.current_timestamp(),
                                               onupdate=db.func.current_timestamp())
    

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)

    @classmethod
    def find_by_email(cls, email: str) -> "Users":
        return cls.query.filter_by(email=email).first()

    @classmethod
    def find_by_username(cls, username: str) -> "Users":
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def find_by_id(cls, _id: int) -> "Users":
        return cls.query.filter_by(id=_id).first()
    
    @classmethod
    def find_by_api_token(cls, _id: int) -> "Users":
        return cls.query.filter_by(api_token=_id).first()
    
    def save(self) -> None:
        try:
            db.session.add(self)
            db.session.commit()
          
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise InvalidUsage(error, 422)
    
    def delete_from_db(self) -> None:
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise InvalidUsage(error, 422)
        return


class Controller(ModelView):

    def is_accessible(self):
        if current_user.is_admin == True:
            return current_user.is_authenticated
        else:
            return abort(404)

    def not_auth(self):
        return "you are not authorize to use the admin dashboard"

    def __init__(self):
        super(Controller, self).__init__(Users, db.session)


class UserProfile(db.Model):

    __tablename__ = 'user_profiles'

    id            = db.Column(db.Integer,      primary_key=True)
    full_name     = db.Column(db.String(64),   nullable=True, default='')
    bio           = db.Column(db.String(800),  nullable=True, default='')
    address       = db.Column(db.String(500),  nullable=True, default='')
    zipcode       = db.Column(db.String(6),    nullable=True, default='')
    phone         = db.Column(db.String(50),   nullable=True, default='')
    email         = db.Column(db.String(100),  unique=True,   nullable=True)
    website       = db.Column(db.String(100),  nullable=True, default='')
    image         = db.Column(db.String(1000), nullable=True, default= Config.ASSETS_ROOT + "/img/user/avatar-5.jpg")
    user          = db.Column(db.Integer, db.ForeignKey("users.id",ondelete="cascade"), nullable=False)
    user_id       = relationship(Users, uselist=False, backref="profile")
    date_created  = db.Column(db.DateTime, default=dt.datetime.utcnow())
    date_modified = db.Column(db.DateTime,  default=db.func.current_timestamp(),
                                               onupdate=db.func.current_timestamp())

    @classmethod
    def find_by_id(cls, _id: int) -> "UserProfile":
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_by_user_id(cls, _id: int):
        return cls.query.filter_by(user=_id).first()
    
    def save(self) -> None:
        try:
            db.session.add(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise InvalidUsage(error, 422)

    def delete_from_db(self) -> None:
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise InvalidUsage(error, 422)
        return


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None


class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="cascade"), nullable=False)
    user = db.relationship(Users)
