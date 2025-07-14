import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import openai
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# Autoriser les requêtes venant de ton site Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://eloquent-otter-def762.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.get("/session")
async def get_session():
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    session_id = data.get("session_id")

    if not session_id:
        return JSONResponse({"error": "Missing session_id"}, status_code=400)

    try:
        # 1. Stocker le message utilisateur
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        session_id TEXT,
                        message TEXT,
                        is_user BOOLEAN
                    );
                """)
                cursor.execute(
                    "INSERT INTO conversations (session_id, message, is_user) VALUES (%s, %s, TRUE)",
                    (session_id, user_input)
                )

        # 2. Obtenir la réponse d'OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_input}]
        )
        assistant_reply = response['choices'][0]['message']['content']

        # 3. Stocker la réponse de l'IA
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO conversations (session_id, message, is_user) VALUES (%s, %s, FALSE)",
                    (session_id, assistant_reply)
                )

        return JSONResponse({"response": assistant_reply})

    except Exception as e:
        print("Erreur :", e)
        return JSONResponse({"error": str(e)}, status_code=500)
