function openModal() {
    document.getElementById("modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("modal").classList.add("hidden");
}

function switchBot(botId) {
    window.location.href = `/dashboard?bot_id=${botId}`;
}

async function toggleBot(botId, currentStatus) {

    const newStatus = !currentStatus;

    try {
        const res = await fetch("/api/bot/toggle", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                bot_id: botId,
                status: newStatus
            })
        });

        const data = await res.json();

        if (data.success) {
            location.reload();
        } else {
            alert("Gagal toggle bot");
        }

    } catch (err) {
        console.error(err);
        alert("Error koneksi");
    }
}

async function createBot() {

    const name = document.getElementById("bot_name").value;
    const token = document.getElementById("bot_token").value;
    const persona = document.getElementById("persona").value;
    const prompt = document.getElementById("prompt").value;

    if (!name || !token) {
        alert("Isi nama & token");
        return;
    }

    try {
        const res = await fetch("/api/bot/create", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name,
                telegram_token: token,
                persona_type: persona,
                system_prompt: prompt
            })
        });

        const data = await res.json();

        if (data.success) {
            alert("✅ Bot dibuat");
            location.reload();
        } else {
            alert(data.detail || "Error");
        }

    } catch (err) {
        console.error(err);
        alert("Server error");
    }
}

function goToInbox(leadId) {
    const urlParams = new URLSearchParams(window.location.search);
    const botId = urlParams.get("bot_id");

    window.location.href = `/inbox?bot_id=${botId}&lead_id=${leadId}`;
}

function switchBot(botId) {
    if (!botId) return; // ✅ guard
    window.location.href = `/dashboard?bot_id=${botId}`;
}