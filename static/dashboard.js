function openModal() {
    document.getElementById("modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("modal").classList.add("hidden");
}

async function toggleBot(botId, currentStatus) {

    console.log("RAW INPUT:", { botId, currentStatus });

    // FORCE BOOLEAN CLEAN
    const isActive = String(currentStatus).toLowerCase() === "true";

    const payload = {
        bot_id: parseInt(botId),
        is_active: !isActive
    };

    console.log("FINAL PAYLOAD:", payload);

    const res = await fetch("/api/bot/toggle", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const text = await res.text(); // IMPORTANT DEBUG STEP

    console.log("RAW RESPONSE:", text);

    let data;
    try {
        data = JSON.parse(text);
    } catch (e) {
        console.error("Response bukan JSON valid");
        return;
    }

    console.log("PARSED:", data);

    if (!res.ok) {
        alert(data.detail || "422 Error");
        return;
    }

    if (data.success) {
        location.reload();
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

    window.location.href =
        `/inbox?bot_id=${botId}&lead_id=${leadId}`;
}