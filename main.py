import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import openai
from sqlalchemy import create_engine, text

# Charger les variables d’environnement
load_dotenv()

# Initialiser l'app FastAPI
app = FastAPI()

# Configurer CORS pour autoriser Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://eloquent-otter-def762.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Connexion à PostgreSQL (Neon)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})

# Création de la table (si elle n'existe pas)
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """))

# ➕ Endpoint pour démarrer une session
@app.get("/session")
def start_session():
    return {"session_id": "neo-session-id"}

# 💬 Endpoint pour envoyer un message
@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message")

    if not user_message:
        return {"error": "Message manquant"}

    # Sauvegarder le message utilisateur
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO messages (role, content) VALUES (:role, :content)"),
                     {"role": "user", "content": user_message})

    # Envoyer la requête à OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un assistant amical appelé Néo."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response["choices"][0]["message"]["content"]

        # Sauvegarder la réponse IA
        with engine.connect() as conn:
            conn.execute(text("INSERT INTO messages (role, content) VALUES (:role, :content)"),
                         {"role": "assistant", "content": bot_reply})

        return {"response": bot_reply}

    except Exception as e:
        return {"error": str(e)}
