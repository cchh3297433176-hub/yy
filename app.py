# -*- coding: utf-8 -*-
import os, sqlite3, secrets
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import uvicorn

app = FastAPI(title="MCYT")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DB_PATH = "/root/mcyt-server/auth.db"
conn = sqlite3.connect(DB_PATH)
conn.cursor().execute("CREATE TABLE IF NOT EXISTS access_codes (code TEXT PRIMARY KEY, device_id TEXT DEFAULT NULL)")
conn.commit()
conn.close()

print("Loading Whisper tiny model...")
whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("Whisper ready!")

@app.post("/api/auth/verify")
def verify(code: str = Form(...), device_id: str = Form(...)):
    c = sqlite3.connect(DB_PATH)
    cur = c.cursor()
    cur.execute("SELECT device_id FROM access_codes WHERE code = ?", (code,))
    row = cur.fetchone()
    if not row:
        c.close()
        raise HTTPException(status_code=403, detail="INVALID_CODE")
    bound = row[0]
    if not bound:
        cur.execute("UPDATE access_codes SET device_id = ? WHERE code = ?", (device_id, code))
        c.commit()
        c.close()
        return {"status": "success", "msg": "BOUND"}
    c.close()
    if bound == device_id:
        return {"status": "success", "msg": "OK"}
    raise HTTPException(status_code=403, detail="DEVICE_MISMATCH")

@app.post("/api/asr/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("zh")):
    tmp = f"/tmp/{secrets.token_hex(6)}.webm"
    with open(tmp, "wb") as f:
        f.write(await file.read())
    try:
        segs, _ = whisper_model.transcribe(tmp, language=language)
        txt = "".join([s.text for s in segs]).strip()
        return {"status": "success", "text": txt}
    finally:
        if os.path.exists(tmp): os.remove(tmp)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
