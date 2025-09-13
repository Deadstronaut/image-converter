# scripts/refine_bg.py
import sys, io
import numpy as np
import cv2
from rembg import remove
from PIL import Image, ImageFilter

# --- NumPy Guard ---
if int(np.__version__.split(".")[0]) >= 2:
    raise RuntimeError("Use numpy<2 (NumPy 1.x)")

if len(sys.argv) < 4:
    print("Usage: python refine_bg.py <input> <output> <mode>")
    sys.exit(1)

in_path, out_path, mode = sys.argv[1], sys.argv[2], sys.argv[3]

PRESETS = {
    "normal": {
        "model": "isnet-general-use",
        "alpha_matting": True,
        "alpha_matting_foreground_threshold": 220,
        "alpha_matting_background_threshold": 30,
        "alpha_matting_erode_size": 1,
    }
}
opts = PRESETS.get(mode, PRESETS["normal"])

# --- Load image ---
with open(in_path, "rb") as f:
    inp = f.read()
img = Image.open(io.BytesIO(inp)).convert("RGBA")

# --- Get mask only ---
mask = remove(img, only_mask=True, **opts)
mask = np.array(mask)

# --- Refine mask ---
kernel = np.ones((3, 3), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

# Feather edges
mask_img = Image.fromarray(mask)
mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=1))
mask = np.array(mask_img)

# --- Apply mask back ---
arr = np.array(img)
arr[:, :, 3] = mask
refined = Image.fromarray(arr, mode="RGBA")

refined.save(out_path, format="PNG")
print(f"✅ Refined: {in_path} → {out_path} ({mode})")
