# scripts/refine_bg.py
import sys, io
import numpy as np
from rembg import remove
from PIL import Image

# --- NumPy Guard ---
if int(np.__version__.split(".")[0]) >= 2:
    raise RuntimeError(
        f"Incompatible NumPy version {np.__version__}. "
        "Please use numpy<2 (NumPy 1.x)."
    )

# --- ARGS ---
if len(sys.argv) < 4:
    print("Usage: python refine_bg.py <input> <output> <mode>")
    sys.exit(1)

in_path, out_path, mode = sys.argv[1], sys.argv[2], sys.argv[3]

# --- PRESETS ---
PRESETS = {
    "soft": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 200,
        "alpha_matting_background_threshold": 30,
        "alpha_matting_erode_size": 0,
    },
    "normal": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 200,
        "alpha_matting_background_threshold": 25,
        "alpha_matting_erode_size": 1,
    },
    "aggressive": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 220,
        "alpha_matting_background_threshold": 15,
        "alpha_matting_erode_size": 2,
    },
}

opts = PRESETS.get(mode, PRESETS["normal"])

# --- PROCESS ---
with open(in_path, "rb") as f:
    inp = f.read()

img = Image.open(io.BytesIO(inp)).convert("RGBA")
out = remove(img, **opts)

out.save(out_path, format="PNG")
print(f"✅ Refined: {in_path} → {out_path} ({mode})")
