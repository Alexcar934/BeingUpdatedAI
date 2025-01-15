import base64
import pandas as pd
from email.message import EmailMessage
from email import policy
import os
import pickle
# Gmail API utils
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# for encoding/decoding messages in base64
# for dealing with attachement MIME types
import re
import unicodedata

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

def clean_email_content(content):
    try:
        # 1. Eliminar referencias de imágenes o indicadores (e.g., "[image: Google]")
        content = re.sub(r'\[image:[^\]]+\]', '', content)

        # 2. Eliminar direcciones de correo electrónico
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '', content)

        # 3. Eliminar URLs
        content = re.sub(r'http\S+|www\S+|https\S+', '', content, flags=re.MULTILINE)

        # 4. Eliminar caracteres especiales (excepto espacios)
        content = re.sub(r'[^\w\s]', '', content)

        # 5. Normalizar texto para eliminar tildes y caracteres Unicode
        content = unicodedata.normalize("NFKD", content).encode("ascii", "ignore").decode("utf-8")

        # 6. Eliminar saltos de línea y espacios redundantes
        content = re.sub(r'\s+', ' ', content).strip()

        # 7. Mantener texto principal eliminando pies de correos genéricos o firmas
        content = re.sub(r'(Google Ireland Ltd\..*|© \d{4} Google.*)', '', content, flags=re.DOTALL)

        return content.strip()
    except Exception as e:
        print(f"Error limpiando contenido: {e}")
        return ""