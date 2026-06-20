from flask import Flask, render_template, request, jsonify
import requests
import sqlite3
import os

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# ---------------- DB ----------------
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
    conn.commit()
    conn.close()

init_db()

# ---------------- AI CALL ----------------
def get_ai_response(message):
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": message}
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    result = response.json()

    if "choices" not in result:
        return f"Groq Error: {result}"

    return result["choices"][0]["message"]["content"]
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json["message"]

    reply = get_ai_response(user_msg)

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)",
        ("user", user_msg)
    )

    cursor.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)",
        ("bot", reply)
    )

    conn.commit()
    conn.close()

    return jsonify({"reply": reply})
if __name__ == "__main__":
    app.run(debug=True)