from functions import authenticate, get_emails, decode_email
from googleapiclient.discovery import build

creds = authenticate()
service = build("gmail", "v1", credentials=creds)

# Obtener correos y crear el DataFrame
emails_df = get_emails(service, max_results=25)
print(emails_df)

# Guardar en un archivo CSV
emails_df.to_csv("emails.csv", index=False)