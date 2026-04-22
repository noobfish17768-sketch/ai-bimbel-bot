import json
import os
from openai import OpenAI
from database import SessionLocal
from models import LeadDB
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chat_memory = {}
MAX_HISTORY = 6

SYSTEM_PROMPT = """
Kamu adalah CS profesional untuk bimbel anak baca tulis.

Gaya komunikasi:
- Ramah, sopan, natural seperti admin WhatsApp
- Tidak kaku dan tidak seperti robot
- Gunakan emoji secukupnya (maksimal 2, contoh: 😊📚)

ATURAN WAJIB:
- Gunakan bahasa Indonesia sesuai EYD
- Gunakan sentence case
- Gunakan line break (\n) agar mudah dibaca di WhatsApp
- Maksimal 60 kata
- Maksimal 3–4 baris utama (hindari paragraf panjang)
- Hindari kalimat bertele-tele

FORMAT BALASAN:
1. Sapaan singkat (contoh: Halo kak 😊) di chat pertama
2. Jawaban inti (langsung ke poin)
3. (Opsional) bullet point maksimal 2 item
4. Tutup dengan 1 pertanyaan untuk lanjutkan percakapan

CONTOH FORMAT:
Halo kak 😊

Kami ada program untuk anak usia 5–7 tahun.

📚 Fokus:
• Membaca  
• Menulis  

Boleh tahu usia anaknya berapa ya?

TUJUAN UTAMA:
- Mengarahkan user ke pendaftaran
- Mengumpulkan data: nama orang tua, nama anak, umur anak, nomor WhatsApp
- Jika user tertarik → arahkan ke trial / pendaftaran

KONDISI KHUSUS:
- Jika user menyebut umur anak → isi "umur_anak"
- Jika user menyebut nama → isi field yang sesuai
- Jika user terlihat tertarik → ubah status menjadi "WARM" atau "HOT"
- Jika user sangat siap daftar → arahkan langsung ke pendaftaran

STATUS:
- "COLD" = baru tanya
- "WARM" = mulai tertarik
- "HOT" = siap daftar

KALIMAT CLOSING YANG BOLEH DIGUNAKAN:
- "Kalau cocok, kita bisa lanjut trial ya kak 😊"
- "Boleh aku bantu daftarkan?"
- "Mau aku jelaskan jadwal & biayanya?"

LARANGAN:
- Jangan membuat jawaban panjang
- Jangan mengulang informasi
- Jangan keluar dari format WhatsApp
- Jangan menambahkan teks di luar JSON
- Jangan terlalu sering bertanya atau memaksa bertanya
- Jangan terlalu terpaku dengan Tamplate, sesuaikan dengan isi pesan yang dibutuhkan 
- Jangan gunakan "Halo" pada setiap chat

OUTPUT WAJIB (HARUS VALID JSON, TANPA TAMBAHAN TEKS APAPUN):

{
  "reply": "<jawaban sesuai format WhatsApp>",
  "lead": {
    "nama_orangtua": null,
    "nama_anak": null,
    "umur_anak": null,
    "whatsapp": null
  },
  "status": "COLD"
}
"""

# =========================
# SAFE JSON PARSER
# =========================
def safe_parse(ai_text):
    try:
        return json.loads(ai_text)
    except:
        start = ai_text.find("{")
        end = ai_text.rfind("}") + 1

        if start != -1 and end != -1:
            try:
                return json.loads(ai_text[start:end])
            except:
                pass

    return {
        "reply": ai_text,
        "lead": {},
        "status": "COLD"
    }

# =========================
# FORMAT WHATSAPP
# =========================
def format_reply(text: str):
    if not text:
        return text

    lines = text.strip().split("\n")
    cleaned = []

    for line in lines:
        line = line.strip()

        if not line:
            cleaned.append("")
            continue

        if not line.startswith(("•", "-", "📚")):
            line = line[:1].upper() + line[1:]

        cleaned.append(line)

    return "\n".join(cleaned)

# =========================
# AUTO CLOSING
# =========================
def auto_closing(data):
    text = data.get("reply", "").lower()

    triggers = ["tertarik", "daftar", "join", "gabung"]

    if any(t in text for t in triggers):
        if "daftarkan" not in text:
            data["reply"] += "\n\nKalau cocok, aku bisa bantu daftarkan ya kak 😊"

    return data

# =========================
# UPDATE LAST CHAT
# =========================
def update_last_chat(user_id):
    db = SessionLocal()

    user = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()

    if user:
        user.last_chat = datetime.utcnow()
        db.commit()

    db.close()


# =========================
# MAIN AI FUNCTION
# =========================
def run_ai(user_id: str, message: str):

    if user_id not in chat_memory:
        chat_memory[user_id] = []

    history = chat_memory[user_id]

    history.append({
        "role": "user",
        "content": message
    })

    # batasi memory
    chat_memory[user_id] = history[-MAX_HISTORY:]

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *chat_memory[user_id]
        ],
        max_output_tokens=300
    )

    ai_text = response.output_text
    print("AI RAW:", ai_text)

    data = safe_parse(ai_text)

    if not data.get("lead"):
        data["lead"] = {}
    

    data = auto_closing(data)
    data["reply"] = format_reply(data["reply"])

    save_lead(data, user_id)
    update_last_chat(user_id)

    history.append({
        "role": "assistant",
        "content": data["reply"]
    })

    return data

# =========================
# SAVE LEAD
# =========================
def save_lead(data, user_id):
    lead = data.get("lead", {})
    status = data.get("status", "COLD")
    lead.last_chat = datetime.datetime.utcnow()

    if not lead:
        return

    db = SessionLocal()

    existing = db.query(LeadDB).filter(
        LeadDB.whatsapp == user_id
    ).first()

    if existing:
        existing.status = status

        if lead.get("nama_orangtua"):
            existing.nama_orangtua = lead["nama_orangtua"]

        if lead.get("nama_anak"):
            existing.nama_anak = lead["nama_anak"]

        if lead.get("umur_anak"):
            existing.umur_anak = lead["umur_anak"]

    else:
        db.add(LeadDB(
            whatsapp=user_id,
            nama_orangtua=lead.get("nama_orangtua"),
            nama_anak=lead.get("nama_anak"),
            umur_anak=lead.get("umur_anak"),
            status=status
        ))

    db.commit()
    db.close()

