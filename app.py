from flask import Flask, render_template, request, jsonify
import requests
import sqlite3
import os
import json

app = Flask(__name__)

import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ---------------- DB INIT ----------------

def init_db():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- MEMORY ----------------

def save_memory(key, value):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO memory(key, value)
        VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))

    conn.commit()
    conn.close()


def get_memory():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM memory")
    rows = cursor.fetchall()

    conn.close()
    return rows


def extract_memory(user_message):
    msg = user_message.lower()

    if "my name is" in msg:
        name = user_message.lower().split("my name is")[-1].strip()
        save_memory("name", name)

    if "call me" in msg:
        name = user_message.lower().split("call me")[-1].strip()
        save_memory("name", name)

# ---------------- HISTORY ----------------

def load_history():

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, content
        FROM messages
        ORDER BY id ASC
        LIMIT 20
    """)

    rows = cursor.fetchall()
    conn.close()

    memory_text = ""
    for k, v in get_memory():
        memory_text += f"{k}: {v}\n"

    messages = [
        {
            "role": "system",
            "content": f"""
You are a helpful AI assistant with memory.

User memory:
{memory_text}

Use memory naturally in responses.
If memory is empty, ask user details.
"""
        }
    ]

    for role, content in rows:
        messages.append({
            "role": "assistant" if role == "bot" else "user",
            "content": content
        })

    return messages

# ---------------- STREAM AI ----------------

def call_groq_stream(messages):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "stream": True
    }

    response = requests.post(url, headers=headers, json=payload, stream=True)

    full_text = ""

    for line in response.iter_lines():
        if line:

            decoded = line.decode("utf-8")

            if "content" in decoded:
                try:
                    data = json.loads(decoded.replace("data: ", ""))
                    delta = data["choices"][0]["delta"].get("content", "")

                    full_text += delta
                    yield delta

                except:
                    pass

    return full_text

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("index.html")

# ---------------- CHAT ----------------

@app.route("/chat", methods=["POST"])
def chat():

    user_message = request.json.get("message", "")

    if not user_message:
        return jsonify({"reply": "Empty message"})

    # extract memory
    extract_memory(user_message)

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO messages(role, content) VALUES(?, ?)",
        ("user", user_message)
    )

    conn.commit()
    conn.close()

    def generate():

        messages = load_history()
        messages.append({"role": "user", "content": user_message})

        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "stream": True
        }

        response = requests.post(url, headers=headers, json=payload, stream=True)

        full_text = ""

        for line in response.iter_lines():

            if line:
                decoded = line.decode("utf-8")

                if "content" in decoded:
                    try:
                        data = json.loads(decoded.replace("data: ", ""))
                        delta = data["choices"][0]["delta"].get("content", "")

                        full_text += delta
                        yield delta

                    except:
                        pass

        # save bot reply
        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO messages(role, content) VALUES(?, ?)",
            ("bot", full_text)
        )

        conn.commit()
        conn.close()

    return app.response_class(generate(), mimetype="text/plain")

# ---------------- HISTORY API ----------------

@app.route("/history")
def history():

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT role, content FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()

    conn.close()

    return jsonify(rows)

# ---------------- CLEAR CHAT ----------------

@app.route("/clear", methods=["POST"])
def clear():

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages")

    conn.commit()
    conn.close()

    return jsonify({"status": "cleared"})

# ---------------- NEW CHAT ----------------

@app.route("/newchat")
def newchat():

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages")

    conn.commit()
    conn.close()

    return jsonify({"status": "new chat"})

# ---------------- RUN ----------------

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)