from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import sqlite3
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
import openai

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# ✅ Autoriser l'origine Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://eloquent-otter-def762.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📦 Modèle pour la requête
class Message(BaseModel):
    session_id: str
    message: str

# 📂 Création (si nécessaire) de la base
def create_table():
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT,
                    user_message TEXT,
                    ai_response TEXT,
                    timestamp TEXT
                )""")
    conn.commit()
    conn.close()

create_table()

# 🧠 Fonction d’appel à OpenAI
def generate_response(message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Remplace si tu veux GPT-4
        messages=[
            {"role": "system", "content": "Tu es Néo, un ami bienveillant et drôle."},
            {"role": "user", "content": message}
        ]
    )
    return response["choices"][0]["message"]["content"]

@app.post("/chat")
async def chat(msg: Message):
    response = generate_response(msg.message)

    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)", (
        msg.session_id,
        msg.message,
        response,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

    return {"response": response}

@app.get("/session")
async def get_session():
    return {"session_id": str(uuid4())}
