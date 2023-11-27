# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import datetime

from apps.config                 import Config
from apps.authentication.models  import Users
from apps.authentication.signals import user_saved_signals
from apps.helpers                import createAccessToken, emailValidate, password_validate, errorColor, get_ts
import getpass
       
class CreateAdmin:
    """ create admin command  """

    def create_admin():
        """ create admin """
        while True:
            try:
                # Check usename exists
                username =  input("Enter Username : ")
                user = Users.find_by_username(username)
                if user:
                    errorColor('username already exists')
                    continue
                
                while True:
                    try:
                        # Check email exists
                        email = input("Enter Email: ")
                        user = Users.find_by_email(email)
                        if user:
                            errorColor('email already eisxt')
                            continue
                        
                        valid_email = emailValidate(email)
                        
                        if valid_email != True:
                            errorColor(f'please enter valid email {email}')
                            continue
                        
                        while True:
                            try:
                                password =  getpass.getpass()
                                valid_pwd = password_validate(password)
                                
                                if valid_pwd != True:
                                    errorColor('please enter valid Password ')
                                    continue
                                
                                user = Users(
                                    username = username,
                                    email        = email,
                                    password     = password,
                                    api_token    = createAccessToken(),
                                    api_token_ts = get_ts(),
                                    role         = Config.USERS_ROLES['ADMIN'])

                                user.save()

                                # send signal for create profile
                                user_saved_signals.send({"user_id":user.id, "email": user.email})
                                print('Super User created successfully.')
                                
                                break
                            except Exception as e:
                                print('server error', e)

                    except Exception as e:
                        print('server error', e)
                    break

            except Exception as e:
                print('server error', e)
            break