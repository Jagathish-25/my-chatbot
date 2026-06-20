from flask import Flask, render_template, request, jsonify, session
import sqlite3, requests, uuid

app = Flask(__name__)
app.secret_key = "supersecret"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("chatbot.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT,
            user TEXT,
            role TEXT,
            content TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" not in session:
        session["user"] = "user_" + str(uuid.uuid4())[:6]

    if "chat_id" not in session:
        session["chat_id"] = str(uuid.uuid4())

    return render_template("index.html")

# ---------------- NEW CHAT ----------------
@app.route("/newchat")
def newchat():
    session["chat_id"] = str(uuid.uuid4())
    return jsonify({"ok": True})

# ---------------- GET CHATS ----------------
@app.route("/get_chats")
def get_chats():
    user = session["user"]

    conn = sqlite3.connect("chatbot.db")
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT id FROM chats WHERE user=?", (user,))
    chats = cur.fetchall()

    conn.close()

    return jsonify(chats)

# ---------------- LOAD CHAT ----------------
@app.route("/load/<chat_id>")
def load(chat_id):
    conn = sqlite3.connect("chatbot.db")
    cur = conn.cursor()

    cur.execute("SELECT role, content FROM chats WHERE id=? ORDER BY rowid", (chat_id,))
    data = cur.fetchall()

    conn.close()

    return jsonify(data)

# ---------------- CHAT STREAM ----------------
@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json["message"]
    chat_id = session["chat_id"]
    user = session["user"]

    def generate():

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": user_msg,
                "stream": True
            },
            stream=True
        )

        full = ""

        for line in response.iter_lines():
            if line:
                import json
                data = json.loads(line.decode("utf-8"))
                chunk = data.get("response", "")
                full += chunk
                yield chunk

        # save
        conn = sqlite3.connect("chatbot.db")
        cur = conn.cursor()

        cur.execute("INSERT INTO chats VALUES (?,?,?,?)",
                    (chat_id, user, "user", user_msg))

        cur.execute("INSERT INTO chats VALUES (?,?,?,?)",
                    (chat_id, user, "bot", full))

        conn.commit()
        conn.close()

    return app.response_class(generate(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)