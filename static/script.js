function addMessage(role, text) {
    let div = document.createElement("div");
    div.className = role;
    div.innerText = text;
    document.getElementById("chatBox").appendChild(div);
}

async function sendMessage() {
    let input = document.getElementById("userInput");
    let msg = input.value;

    if (!msg) return;

    addMessage("user", msg);
    input.value = "";

    // typing effect
    let typing = document.createElement("div");
    typing.className = "bot";
    typing.innerText = "typing...";
    document.getElementById("chatBox").appendChild(typing);

    let res = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: msg })
    });

    let data = await res.json();

    typing.remove();

    typeEffect(data.reply);
}

function typeEffect(text) {
    let i = 0;

    let msg = document.createElement("div");
    msg.className = "bot";
    document.getElementById("chatBox").appendChild(msg);

    let interval = setInterval(() => {
        msg.innerHTML += text.charAt(i);
        i++;

        if (i >= text.length) {
            clearInterval(interval);
        }
    }, 15);
}
window.onload = async function () {
    let res = await fetch("/history");
    let data = await res.json();

    data.forEach(msg => {
        addMessage(msg[0], msg[1]);
    });
};
function clearChat() {
    document.getElementById("chat-box").innerHTML = "";
}