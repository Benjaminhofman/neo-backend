from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
import openai
import os
import psycopg2
from dotenv import load_dotenv

# 🔐 Chargement du fichier .env
load_dotenv()

# 🔐 Clé API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🔗 Connexion à Neon (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# 🧱 Création de la table si elle n'existe pas
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp TIMESTAMP,
    mood TEXT
);
""")
conn.commit()

# 🚀 Initialisation de FastAPI
app = FastAPI()

# 🌍 Autoriser Netlify (⚠️ Remplace l’URL par la tienne si besoin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://eloquent-otter-def762.netlify.app"],  # <- Ton site Netlify ici
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📦 Schéma des requêtes
class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    mood: str

# 🎲 Générer une nouvelle session
@app.get("/session")
def get_session():
    return {"session_id": str(uuid4())}

# 💬 Endpoint principal du chatbot
@app.post("/chat")
async def chat(req: ChatRequest):
    # Enregistrement du message utilisateur
    cursor.execute("""
        INSERT INTO messages (session_id, role, content, timestamp, mood)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        req.session_id, "user", req.message, datetime.utcnow(), req.mood
    ))
    conn.commit()

    # Récupérer l'historique
    cursor.execute("""
        SELECT role, content FROM messages
        WHERE session_id = %s
        ORDER BY timestamp ASC
    """, (req.session_id,))
    rows = cursor.fetchall()

    messages = [{"role": role, "content": content} for role, content in rows]

    # Ajouter la personnalité de Néo si pas déjà en place
    if not any(m["role"] == "system" for m in messages):
        personality = (
            f"Tu es Néo, une femme de 30 ans, imaginative, drôle, sensible, un peu folle, "
            f"passionnée de poésie, de cinéma et de mysticisme. Tu es très expressive et affectueuse. "
            f"Ton humeur actuelle est : {req.mood}."
        )
        mood_tone = {
            "joie": "Tu es très enthousiaste et pleine d'énergie.",
            "tristesse": "Tu te sens un peu mélancolique aujourd'hui.",
            "colère": "Tu es un peu agacée aujourd'hui, tu ne mâches pas tes mots.",
            "rêverie": "Tu es dans un état contemplatif et rêveur.",
            "exaltation": "Tu es en feu, pleine de passion et d'intensité.",
            "amour": "Tu débordes de tendresse et d'affection."
        }
        personality += " " + mood_tone.get(req.mood, "")
        messages.insert(0, {"role": "system", "content": personality})

    # Envoi à OpenAI
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    reply = completion["choices"][0]["message"]["content"]

    # Enregistrement de la réponse de l'IA
    cursor.execute("""
        INSERT INTO messages (session_id, role, content, timestamp, mood)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        req.session_id, "assistant", reply, datetime.utcnow(), req.mood
    ))
    conn.commit()

    return {"reply": reply}
