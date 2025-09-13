# scripts/refine_bg.py
import sys, io
from rembg import remove
from PIL import Image

# Argümanlar: input_path output_path kalite mode
in_path = sys.argv[1]
out_path = sys.argv[2]
quality = int(sys.argv[3]) if len(sys.argv) > 3 else 82
mode = sys.argv[4] if len(sys.argv) > 4 else "normal"

PRESETS = {
    "soft": dict(model="isnet-general-use", alpha_matting=True,
                 alpha_matting_foreground_threshold=180,
                 alpha_matting_background_threshold=40,
                 alpha_matting_erode_size=0),
    "normal": dict(model="isnet-general-use", alpha_matting=True,
                   alpha_matting_foreground_threshold=200,
                   alpha_matting_background_threshold=25,
                   alpha_matting_erode_size=1),
    "aggressive": dict(model="isnet-general-use", alpha_matting=True,
                       alpha_matting_foreground_threshold=220,
                       alpha_matting_background_threshold=15,
                       alpha_matting_erode_size=2),
}

opts = PRESETS.get(mode, PRESETS["normal"])

# resmi oku
img = Image.open(in_path).convert("RGBA")

# rembg uygula
out = remove(img, **opts)

# webp olarak yaz
out.save(out_path, format="WEBP", quality=quality)
print(f"✅ Refined {in_path} → {out_path} ({mode})")
