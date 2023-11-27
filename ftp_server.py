import ftplib
import os
import base64
from io import BytesIO
from apps.helpers import splitUrlGetFilename
from apps.config import Config

try:
    from PIL import Image
except:    
    pass

default_image = Config.DEFAULT_IMAGE_URL

def testFTPConnection():
    
    try:

        if Config.FTP_SERVER and Config.FTP_USER and Config.FTP_PASSWORD:

            ftp = ftplib.FTP(Config.FTP_SERVER, Config.FTP_USER, Config.FTP_PASSWORD)
            ftp.close()
            return True

        return False

    except Exception as e:
        
        return False     

def uploadImageFTP(IMAGE_NAME, user_image=None): 
    """ Upload files save to ftp server """

    try:

        if Config.FTP_SERVER and Config.FTP_USER and Config.FTP_PASSWORD:

            ftp = ftplib.FTP(Config.FTP_SERVER, Config.FTP_USER, Config.FTP_PASSWORD)

            file_path = f'media/{IMAGE_NAME}'
            file = open(file_path,'rb')
            ftp.storbinary(f'STOR {IMAGE_NAME}', file)
            remove_file(file, file_path)

            status = True
            # if check defualt image
            if default_image in user_image:
                status = False

            if status == True:
                file_name = splitUrlGetFilename(user_image)
                # delete file if user replace
                if file_name in ftp.nlst():
                    ftp.delete(file_name)

            ftp.close()
            # ftp.quit()
            return True

    except Exception as e:
        
        return False   

def remove_file(file, file_path):
    """  removed file into media """
    try:
        os.remove(file_path)
        file.close()
    except Exception as error:
        print("Error removing or closing uploaded file handle", error)
        return False
    return True
