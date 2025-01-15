from googleapiclient.discovery import build
import base64
import pandas as pd
from email.message import EmailMessage
from email import policy
import os
import pickle
# Gmail API utils
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# for encoding/decoding messages in base64
from base64 import urlsafe_b64decode, urlsafe_b64encode
# for dealing with attachement MIME types
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type
from dotenv import load_dotenv

load_dotenv('credentials.env')

# Acceder a las credenciales

PASSWORD = os.getenv('PASSWORD')

# Request all access (permission to read/send/receive emails, manage the inbox, and more)
SCOPES = ['https://mail.google.com/']



# Función para decodificar los correos
def decode_email(message):
    try:
        # Decodifica el contenido del mensaje
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        
        # Extrae la fecha, el remitente y el asunto del correo
        date = next((header["value"] for header in headers if header["name"] == "Date"), None)
        sender = next((header["value"] for header in headers if header["name"] == "From"), None)
        subject = next((header["value"] for header in headers if header["name"] == "Subject"), None)
        
        # Decodifica el contenido del mensaje
        parts = payload.get("parts", [])
        content = ""
        for part in parts:
            if part["mimeType"] == "text/plain":  # Solo texto
                data = part.get("body", {}).get("data", "")
                content = base64.urlsafe_b64decode(data).decode("utf-8")
                break

        return {"fecha": date, "correo": sender, "titulo": subject, "contenido": content}
    except Exception as e:
        print(f"Error decodificando el correo: {e}")
        return None

# Función para obtener los correos
def get_emails(service, max_results=10):
    try:
        # Lista de correos a procesar
        results = service.users().messages().list(userId="me", maxResults=max_results).execute()
        messages = results.get("messages", [])
        
        emails = []
        for msg in messages:
            msg_id = msg["id"]
            message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            email_data = decode_email(message)
            if email_data:
                emails.append(email_data)
        
        # Retorna un DataFrame con los datos
        return pd.DataFrame(emails)
    except Exception as e:
        print(f"Error obteniendo los correos: {e}")
        return pd.DataFrame()


def authenticate():
    creds = None
    # Verifica si ya existe un archivo con credenciales almacenadas
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    
    # Si no hay credenciales o son inválidas, realiza el flujo de autenticación
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guarda las credenciales para el futuro
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    
    return creds