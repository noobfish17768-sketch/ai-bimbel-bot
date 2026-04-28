async function toggleBot(status) {
    try {
        const res = await fetch("/api/bot/toggle", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                status: status
            })
        });

        const data = await res.json();

        if (data.success) {
            console.log("Bot status updated:", status);
        } else {
            alert("Error: " + (data.detail || "Unknown error"));
        }

    } catch (err) {
        console.error(err);
        alert("Request gagal");
    }
}