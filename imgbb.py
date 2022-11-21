import os
import requests


def imgbb(file_name: str):
    files = {"image": open(file_name, "rb")}
    r = requests.post('https://api.imgbb.com/1/upload', data={'key': os.getenv("IMGBB_KEY")}, files=files)
    return r.json()["data"]["url_viewer"]

    
