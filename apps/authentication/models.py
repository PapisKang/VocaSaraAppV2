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
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column,DateTime, Integer, String, Date, Boolean, ForeignKey, LargeBinary
from datetime import datetime
from sqlalchemy import LargeBinary
from sqlalchemy.dialects.mysql import LONGTEXT


RoleType = Config.USERS_ROLES
Status   = Config.USERS_STATUS
VERIFIED_EMAIL = Config.VERIFIED_EMAIL

class Users(db.Model, UserMixin):

    __tablename__ = 'users'
    
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(64), unique=True)
    email           = db.Column(db.String(100), unique=True)
    password        = db.Column(db.LargeBinary)
    reset_token     = db.Column(db.String(100), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)
    role            = db.Column(db.Integer(),
                        default=RoleType['USER'], nullable=False)
    status          = db.Column(db.Integer(),
                        default=Status['ACTIVE'], nullable=False)
    failed_logins   = db.Column(db.Integer(), default=0)

    api_token       = db.Column(db.String(100))
    api_token_ts    = db.Column(db.String(100))
    
    verified_email  = db.Column(db.Integer(),   default=VERIFIED_EMAIL['not-verified'], nullable=False)
    
    
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
    service       = db.Column(db.String(100),  nullable=True, default='')
    image          = db.Column(LONGTEXT, nullable=True)
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


class InspectionOperateur(db.Model):
    __tablename__ = 'InspectionOperateur'
    id = Column(Integer, primary_key=True)
    Inspection = Column(Integer, ForeignKey('RapportGenere.id'))
    Users = Column(Integer, ForeignKey('users.id'))
    EstResponsable = Column(Boolean)



class Defaut(db.Model):
    __tablename__ = 'Defaut'
    id = Column(Integer, primary_key=True)
    Nom = Column(String(255))
    TypeDefaut = Column(Integer, ForeignKey('TypeDefaut.id'))

class TypeDefaut(db.Model):
    __tablename__ = 'TypeDefaut'
    id = Column(Integer, primary_key=True)
    Libelle = Column(String(255))


class StatutImageInspection(db.Model):
    __tablename__ = 'StatutImageInspection'
    id = Column(Integer, primary_key=True)
    Libelle = Column(String(255))

class StatutInspection(db.Model):
    __tablename__ = 'StatutInspection'
    id = Column(Integer, primary_key=True)
    Libelle = Column(String(255))

class Feeder(db.Model):
    __tablename__ = 'Feeder'
    id = db.Column(db.Integer, primary_key=True)
    Nom = db.Column(db.String(255), nullable=False)  # Retirez l'option unique=True

class Troncon(db.Model):
    __tablename__ = 'Troncon'
    id = db.Column(db.Integer, primary_key=True)
    Nom = db.Column(db.String(255), nullable=False)  # Retirez l'option unique=True


# Définition du modèle RapportGenere
class RapportGenere(db.Model):
    __tablename__ = 'RapportGenere'

    id = db.Column(db.Integer, primary_key=True)
    nom_operateur = db.Column(db.String(64), nullable=False, default=None)
    feeder = db.Column(db.String(255), nullable=False)
    troncon = db.Column(db.String(255), nullable=False)
    date_debut = db.Column(db.DateTime, nullable=False)
    date_fin = db.Column(db.DateTime, nullable=False)
    zone = db.Column(db.String(255), nullable=False)
    groupement_troncon = db.Column(db.String(255))

    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relations avec les images visibles et invisibles
    images_upload_visible = db.relationship('ImageUploadVisible', back_populates='rapport_genere', cascade='all, delete-orphan')
    images_upload_invisible = db.relationship('ImageUploadInvisible', back_populates='rapport_genere', cascade='all, delete-orphan')


class ImageUploadVisible(db.Model):
    __tablename__ = 'ImageUploadVisible'
    id = db.Column(db.Integer, primary_key=True)
    nom_operateur = db.Column(db.String(64), nullable=False, default=None)
    filename = db.Column(db.String(255))
    original_size = db.Column(db.String(20)) 
    compressed_size = db.Column(db.String(20)) 
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(LONGTEXT)
    
    # Nouvelles colonnes pour la longueur, la largeur et le type de défaut
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    type_defaut = db.Column(db.String(255))
    
    feeder = db.Column(db.String(255), nullable=False)
    troncon = db.Column(db.String(255), nullable=False)
    zone = db.Column(db.String(255), nullable=False)
    type_image = db.Column(db.String(20), default='Visible')
    #Relation avec RapportGenere
    rapport_genere_id = db.Column(db.Integer, db.ForeignKey('RapportGenere.id'))
    rapport_genere = db.relationship('RapportGenere', back_populates='images_upload_visible')  # Modifier ici


# Définition du modèle ImageUploadInvisible
class ImageUploadInvisible(db.Model):
    __tablename__ = 'ImageUploadInvisible'
    id = db.Column(db.Integer, primary_key=True)
    nom_operateur = db.Column(db.String(64), nullable=False, default=None)
    filename = db.Column(db.String(255))
    original_size = db.Column(db.String(20)) 
    compressed_size = db.Column(db.String(20)) 
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(LONGTEXT)
    
    feeder = db.Column(db.String(255), nullable=False)
    troncon = db.Column(db.String(255), nullable=False)
    zone = db.Column(db.String(255), nullable=False)
    type_image = db.Column(db.String(20), default='Invsible')
    #Relation avec RapportGenere
    rapport_genere_id = db.Column(db.Integer, db.ForeignKey('RapportGenere.id'))
    rapport_genere = db.relationship('RapportGenere', back_populates='images_upload_invisible')
    



