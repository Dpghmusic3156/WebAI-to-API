// src/static/js/utils.js - Shared API wrapper and helpers

const api = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw err;
        }
        return res.json();
    },

    async post(url, body) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw err;
        }
        return res.json();
    },
};

function showResult(el, type, message) {
    el.textContent = message;
    el.className = `result-box ${type}`;
    el.classList.remove("hidden");
}

function showInline(el, message, isError) {
    el.textContent = message;
    el.style.color = isError ? "var(--error)" : "var(--success)";
    setTimeout(() => { el.textContent = ""; }, 3000);
}

function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
}
