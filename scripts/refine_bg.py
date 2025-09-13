# scripts/refine_bg.py
import os, io
import numpy as np
from rembg import remove
from PIL import Image
from supabase import create_client

# --- ENV ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_ROLE_KEY = os.environ["SERVICE_ROLE_KEY"]
BUCKET = os.environ["BUCKET"]
PRODUCTS_TABLE = os.getenv("PRODUCTS_TABLE", "products")
IMAGE_COLUMN = os.getenv("IMAGE_COLUMN", "image_url")

supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
storage = supabase.storage.from_(BUCKET)

# --- PRESETS ---
PRESETS = {
    "soft": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 180,
        "alpha_matting_background_threshold": 40,
        "alpha_matting_erode_size": 0
    },
    "normal": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 200,
        "alpha_matting_background_threshold": 25,
        "alpha_matting_erode_size": 1
    },
    "aggressive": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 220,
        "alpha_matting_background_threshold": 15,
        "alpha_matting_erode_size": 2
    }
}

# preset seçimi
MODE = os.getenv("REFINE_MODE", "normal")  # workflow input ile gelir
SESSION_OPTS = PRESETS.get(MODE, PRESETS["normal"])

# --- PARAMS ---
SESSION_OPTS = {
    "model": "isnet-general-use",
    "alpha_matting": True,
    "alpha_matting_foreground_threshold": 200,  # ↑ düşerse daha fazla detay
    "alpha_matting_background_threshold": 25,   # ↑ artarsa daha fazla silme
    "alpha_matting_erode_size": 1               # 0 → hiç aşındırma, 1 → hafif
}

QUALITY = 82

def process_file(path):
    # indir
    res = storage.download(path)
    if not res:
        print(f"Skip: {path}")
        return

    img = Image.open(io.BytesIO(res)).convert("RGBA")

    # rembg
    out = remove(img, **SESSION_OPTS)

    # webp encode
    buf = io.BytesIO()
    out.save(buf, format="WEBP", quality=QUALITY)
    buf.seek(0)

    # upload
    new_path = path.rsplit(".",1)[0] + ".webp"
    storage.upload(new_path, buf.getvalue(), {"content-type":"image/webp","upsert":True})
    storage.remove([path])
    print(f"✅ {path} → {new_path}")

if __name__ == "__main__":
    # şimdilik tüm bucket içindekileri tek seferde çalıştırıyor
    data = storage.list("", {"limit":1000})
    for f in data:
        if f["name"].lower().endswith((".jpg",".jpeg",".png")):
            process_file(f["name"])
