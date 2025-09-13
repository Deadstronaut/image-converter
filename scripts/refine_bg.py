# scripts/refine_bg.py
import os, io, sys
from typing import Optional

from PIL import Image
from supabase import create_client
from rembg import remove, new_session

# Kenar düzeltme için opsiyonel: cv2 varsa kullanır (yoksa atlar)
try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    HAS_CV = True
except Exception:
    HAS_CV = False

# --- ENV ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_ROLE_KEY = os.environ["SERVICE_ROLE_KEY"]
BUCKET = os.environ["BUCKET"]

# İsteğe bağlı env’ler
PREFIX = os.getenv("PREFIX", "").strip().strip("/")            # sadece bu klasörü işle (boşsa kök)
REFINE_MODE = os.getenv("REFINE_MODE", "normal").lower()       # soft | normal | aggressive
QUALITY = int(os.getenv("QUALITY", "82"))                      # WEBP kalite

# Supabase client
supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)
storage = supabase.storage.from_(BUCKET)

# --- PRESETS (sadece burada tanımlı; başka yerde override YOK) ---
PRESETS = {
    "soft": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 190,
        "alpha_matting_background_threshold": 35,
        "alpha_matting_erode_size": 0,
        # Kenar düzeltme
        "dilate_iter": 0,   # 0 = kapalı
        "feather_px": 0     # 0 = kapalı
    },
    "normal": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 200,
        "alpha_matting_background_threshold": 25,
        "alpha_matting_erode_size": 1,
        "dilate_iter": 1,
        "feather_px": 1
    },
    "aggressive": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 220,
        "alpha_matting_background_threshold": 15,
        "alpha_matting_erode_size": 2,
        "dilate_iter": 2,
        "feather_px": 2
    }
}

OPTS = PRESETS.get(REFINE_MODE, PRESETS["normal"])
SESSION = new_session(OPTS["model"])  # rembg python API için model seçimi

def log(*a):
    print(*a, flush=True)

def list_files(prefix: str) -> list[dict]:
    """Tek seferde 1000 dosya. Gerekirse sayfalama eklenebilir."""
    res = storage.list(prefix, {"limit": 1000})
    return [f for f in (res or []) if str(f.get("name", "")).lower().endswith((".jpg", ".jpeg", ".png"))]

def download(path: str) -> Optional[bytes]:
    try:
        data = storage.download(path)
        return data if isinstance(data, (bytes, bytearray)) else bytes(data)
    except Exception as e:
        log("download error:", path, e)
        return None

def upload(path: str, buf: bytes):
    storage.upload(path, buf, {"content-type": "image/webp", "upsert": True})

def remove_src(path: str):
    storage.remove([path])

def postprocess_edges(rgba: Image.Image, dilate_iter: int, feather_px: int) -> Image.Image:
    """Alfa kanalını hafif genişletip (dilate) yumuşatır (feather).
       HAS_CV yoksa olduğu gibi döner."""
    if not HAS_CV or (dilate_iter <= 0 and feather_px <= 0):
        return rgba

    r, g, b, a = rgba.split()
    a_np = np.array(a, dtype=np.uint8)

    if dilate_iter > 0:
        kernel = np.ones((3, 3), np.uint8)
        a_np = cv2.dilate(a_np, kernel, iterations=int(dilate_iter))

    if feather_px > 0:
        # kernel boyutu tek sayı olmalı
        k = max(1, int(feather_px) * 2 + 1)
        a_np = cv2.GaussianBlur(a_np, (k, k), 0)

    a2 = Image.fromarray(a_np, mode="L")
    return Image.merge("RGBA", (r, g, b, a2))

def process_file(src_path: str):
    raw = download(src_path)
    if not raw:
        log("Skip (download failed):", src_path)
        return

    # RGBA
    img = Image.open(io.BytesIO(raw)).convert("RGBA")

    # Rembg (python API) – preset değerleri uygulanıyor
    out = remove(
        img,
        session=SESSION,
        alpha_matting=OPTS["alpha_matting"],
        alpha_matting_foreground_threshold=OPTS["alpha_matting_foreground_threshold"],
        alpha_matting_background_threshold=OPTS["alpha_matting_background_threshold"],
        alpha_matting_erode_size=OPTS["alpha_matting_erode_size"],
    )

    # Kenar düzeltme (isteğe bağlı)
    out = postprocess_edges(
        out,
        dilate_iter=int(OPTS.get("dilate_iter", 0)),
        feather_px=int(OPTS.get("feather_px", 0)),
    )

    # WEBP encode
    buf = io.BytesIO()
    out.save(buf, format="WEBP", quality=QUALITY)
    webp_bytes = buf.getvalue()

    # Upload & temizle
    dst_path = src_path.rsplit(".", 1)[0] + ".webp"
    upload(dst_path, webp_bytes)
    remove_src(src_path)

    log(f"✅ {src_path} → {dst_path}")

def main():
    base = PREFIX if PREFIX else ""
    log("MODE:", REFINE_MODE, "| PREFIX:", base or "(root)", "| Q:", QUALITY)
    files = list_files(base)
    if not files:
        log("Hiç dosya yok.")
        return

    for f in files:
        name = f.get("name")
        src = f"{base}/{name}" if base else name
        process_file(src)

if __name__ == "__main__":
    main()
