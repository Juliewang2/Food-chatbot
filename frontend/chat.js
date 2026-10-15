// 每个浏览器标签页一个会话 ID，后端用它区分不同用户的订单
function getSessionId() {
    let id = null;
    try { id = sessionStorage.getItem("chat_session_id"); } catch (e) {}
    if (!id) {
        id = Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
        try { sessionStorage.setItem("chat_session_id", id); } catch (e) {}
    }
    return id;
}

const sessionId = getSessionId();
const toggleBtn = document.getElementById("chat-toggle");
const closeBtn = document.getElementById("chat-close");
const chatBox = document.getElementById("chat-box");
const messages = document.getElementById("chat-messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
let welcomed = false;

function addMessage(text, who) {
    const div = document.createElement("div");
    div.className = "msg " + who;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
}

async function send(payload) {
    const typing = addMessage("...", "bot typing");
    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(Object.assign({ session_id: sessionId }, payload))
        });
        const data = await res.json();
        typing.remove();
        addMessage(data.reply, "bot");
    } catch (e) {
        typing.remove();
        addMessage("Sorry, I can't reach the server right now.", "bot");
    }
}

toggleBtn.addEventListener("click", () => {
    chatBox.hidden = !chatBox.hidden;
    if (!chatBox.hidden) {
        input.focus();
        // 第一次打开时触发 Dialogflow 的欢迎语
        if (!welcomed) {
            welcomed = true;
            send({ event: "WELCOME" });
        }
    }
});

closeBtn.addEventListener("click", () => { chatBox.hidden = true; });

form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, "user");
    input.value = "";
    send({ message: text });
});
