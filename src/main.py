import streamlit as st
import pandas as pd
from functions import authenticate, get_emails, clean_email_content
from googleapiclient.discovery import build
import os
from datetime import datetime, timedelta
import openai

# Configurar la página de Streamlit
st.set_page_config(page_title="Email Analyzer", layout="wide")

st.title("📧 Email Analyzer with OpenAI")
st.write("Este proyecto analiza correos electrónicos usando la API de Gmail y GPT.")

# Sidebar para configuraciones
st.sidebar.header("Configuraciones")
max_results = st.sidebar.slider("Número de correos a analizar:", min_value=5, max_value=50, value=25, step=5)

# Autenticación con Gmail
st.sidebar.write("Autenticando con Gmail...")
try:
    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)
    st.sidebar.success("Autenticación exitosa.")
except Exception as e:
    st.sidebar.error(f"Error al autenticar: {e}")

# Obtener correos y filtrar por última semana
if st.button("📥 Obtener correos de la última semana"):
    with st.spinner("Descargando correos..."):
        emails_df = get_emails(service, max_results=max_results)
        st.success("Correos descargados exitosamente.")
        
        # Procesar fechas
        emails_df['fecha'] = pd.to_datetime(emails_df['fecha'], errors='coerce', utc=True)
        
        # Filtrar correos de la última semana
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        recent_emails_df = emails_df[emails_df['fecha'] >= one_week_ago]
        
        if recent_emails_df.empty:
            st.warning("No se encontraron correos de la última semana.")
        else:
            st.write("### Correos descargados de la última semana:")
            st.dataframe(recent_emails_df)
            
            # Limpiar el contenido de los correos
            recent_emails_df['contenido_limpio'] = recent_emails_df['contenido'].apply(clean_email_content)

            # Análisis inicial con OpenAI
            st.write("### Análisis de newsletters con OpenAI:")
            openai.api_key = os.getenv('OPENAI_API_KEY')

            prompt_template = """
            You are an assistant that analyzes emails and extracts key points from newsletters.
            1. If the email is NOT a newsletter, respond ONLY with: `NO`.
            2. If the email IS a newsletter, extract the interesting news items:
                - Translate the news to Spanish.
                - Present the top points in bullet format.

            Email:
            {content}
            """

            analyzed_results = []
            for content in recent_emails_df['contenido_limpio']:
                messages = [
                    {"role": "system", "content": prompt_template},
                    {"role": "user", "content": content}
                ]
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=150,
                    temperature=1
                )
                result = response.choices[0].message.content
                analyzed_results.append(result)
            
            recent_emails_df['respuesta_gpt'] = analyzed_results

            # Filtrar noticias interesantes de las respuestas
            PROMPT_FINAL = '--'.join([i for i in recent_emails_df['respuesta_gpt'] if '-' in i]).replace('YES', '').replace('\n', ' - ')

            # Mostrar resultados preliminares
            st.write("### Respuestas del análisis inicial:")
            st.dataframe(recent_emails_df[['fecha', 'titulo', 'respuesta_gpt']])

            # Análisis final: selección de las 10 noticias más importantes
            st.write("### Selección de las 10 noticias más importantes:")
            final_messages = [
                {"role": "system", "content": """
                Ahora vas a analizar cada una de estas noticias que te pasaré en el prompt, y vas a seleccionar cuáles son las 10 más importantes.
                Tu criterio de selección se basará en:
                1. Innovaciones dentro del mundo de la ciencia de datos y la inteligencia artificial.
                2. Otros campos en menor medida.
                Quiero que las noticias se presenten en castellano en el siguiente formato:

                Entrada del Usuario:
                -- Noticia 1
                -- Noticia 2

                Formato de Respuesta:
                1. Noticia resumida más importante
                2. Segunda noticia más importante
                3. ...
                """},
                {"role": "user", "content": f"{PROMPT_FINAL}"}
            ]

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=final_messages,
                max_tokens=1000,
                temperature=1
            )
            final_results = response.choices[0].message.content

            # Mostrar el resultado final
            st.write("### Noticias seleccionadas:")
            st.text(final_results)

# Mostrar instrucciones adicionales
st.write("### Notas:")
st.info("El análisis se centra en priorizar temas relacionados con inteligencia artificial y ciencia de datos.")
