// src/static/js/dashboard.js - Dashboard tab logic

const Dashboard = {
    intervalId: null,

    init() {
        document.getElementById("btn-reinit").addEventListener("click", async () => {
            const btn = document.getElementById("btn-reinit");
            const result = document.getElementById("reinit-result");
            btn.disabled = true;
            btn.textContent = "Reinitializing...";
            try {
                const data = await api.post("/api/admin/client/reinitialize");
                showInline(result, data.message, !data.success);
            } catch (err) {
                showInline(result, "Failed: " + (err.detail || "Unknown error"), true);
            } finally {
                btn.disabled = false;
                btn.textContent = "Reinitialize Gemini Client";
                this.refresh();
            }
        });
    },

    activate() {
        this.refresh();
        this.intervalId = setInterval(() => this.refresh(), 10000);
    },

    deactivate() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    },

    async refresh() {
        try {
            const data = await api.get("/api/admin/status");
            this.updateCards(data);
            this.updateEndpointTable(data.stats.endpoints);
        } catch {
            document.getElementById("val-status").textContent = "Error";
        }
    },

    updateCards(data) {
        const statusEl = document.getElementById("val-status");
        statusEl.textContent = data.gemini_status === "connected" ? "Connected" : "Disconnected";
        statusEl.style.color = data.gemini_status === "connected" ? "var(--success)" : "var(--error)";

        document.getElementById("val-model").textContent = data.current_model || "--";
        document.getElementById("val-requests").textContent = data.stats.total_requests;
        document.getElementById("val-success").textContent = data.stats.success_count + " OK";
        document.getElementById("val-errors").textContent = data.stats.error_count + " ERR";
        document.getElementById("val-uptime").textContent = data.stats.uptime;

        // Update header badge
        const badge = document.getElementById("connection-status");
        badge.textContent = data.gemini_status === "connected" ? "Connected" : "Disconnected";
        badge.className = "status-badge " + data.gemini_status;
    },

    updateEndpointTable(endpoints) {
        const tbody = document.getElementById("endpoint-tbody");
        const noData = document.getElementById("no-endpoints");
        const entries = Object.entries(endpoints || {});

        if (entries.length === 0) {
            tbody.innerHTML = "";
            noData.classList.remove("hidden");
            return;
        }

        noData.classList.add("hidden");
        entries.sort((a, b) => b[1] - a[1]);
        tbody.innerHTML = entries
            .map(([path, count]) => `<tr><td>${escapeHtml(path)}</td><td>${count}</td></tr>`)
            .join("");
    },
};
