const chatContainer = document.getElementById('chat-container');
const promptInput = document.getElementById('prompt-input');
let tempBaseUrl = '/Backend/Core/Temporary';

function formatText(rawText) {
    if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
        return marked.parse(rawText);
    }
    return String(rawText || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}

window.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        if (data.temp_url) {
            tempBaseUrl = data.temp_url.replace(/\/+$/, '');
        }
        if (data.status === 'success' && Array.isArray(data.history)) {
            chatContainer.innerHTML = '';
            data.history.forEach(msg => {
                let text = msg.content || '';
                if (text.startsWith('[Janak]:')) text = text.replace('[Janak]:', '').trim();
                if (text.startsWith('[Unknown]:')) text = text.replace('[Unknown]:', '').trim();

                appendMessage(text, msg.role, msg.attachment || null);
            });
        }
    } catch (err) {
        console.error("Could not load history:", err);
    }
});

promptInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') sendCommand();
});

async function sendCommand() {
    const text = promptInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    promptInput.value = '';
    chatContainer.scrollTop = chatContainer.scrollHeight;

    const loadingId = appendMessage("Processing matrix...", 'assistant');
    const loadingDiv = document.getElementById(loadingId);

    try {
        const res = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: text, speaker: 'Janak' })
        });
        const data = await res.json();
        if (data.temp_url) {
            tempBaseUrl = data.temp_url.replace(/\/+$/, '');
        }

        const replyText = data.response || "Operation completed successfully.";
        renderParsedContent(replyText, loadingDiv, data.attachment || null);
    } catch (err) {
        loadingDiv.innerText = "ERROR: Connection to local backend lost.";
    }
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

let msgCounter = 0;

function appendMessage(text, sender, attachment = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    msgCounter += 1;
    const id = `msg-${Date.now()}-${msgCounter}`;
    msgDiv.id = id;

    if (sender === 'user') {
        msgDiv.innerText = text;
    } else {
        renderParsedContent(text, msgDiv, attachment);
    }

    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return id;
}
function renderMarkdownSafe(rawText) {
    const safeStr = String(rawText ?? "");
    if (typeof marked !== "undefined" && typeof marked.parse === "function") {
        return marked.parse(safeStr);
    }
    return safeStr
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>");
}

function renderParsedContent(text, containerElement) {
    containerElement.innerHTML = "";

    const customMatch = String(text || "").match(/\[CHART_IMG:(.*?)\]/);
    const mdMatch = String(text || "").match(/!\[.*?\]\((.*?)\)/);

    let filename = null;
    let rawTag = null;

    if (customMatch) {
        filename = customMatch[1];
        rawTag = customMatch[0];
    } else if (mdMatch) {
        filename = mdMatch[1];
        rawTag = mdMatch[0];
    }

    if (filename) {
        filename = filename.split("/").pop().split("\\").pop();
        const cleanText = String(text || "").replace(rawTag, "").trim();

        if (cleanText) {
            const textDiv = document.createElement("div");
            textDiv.innerHTML = renderMarkdownSafe(cleanText);
            containerElement.appendChild(textDiv);
        }

        const img = document.createElement("img");
        img.className = "chart-img";
        img.src = `/Backend/Core/Temporary/${encodeURIComponent(filename)}?t=${Date.now()}`;
        img.alt = "Generated Chart";
        containerElement.appendChild(img);
    } else {
        containerElement.innerHTML = renderMarkdownSafe(text);
    }
}