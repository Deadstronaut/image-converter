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

# --- Remove BG ---
with open(in_path, "rb") as f:
    inp = f.read()
img = Image.open(io.BytesIO(inp)).convert("RGBA")
out = remove(img, **opts)

# --- Refine mask with OpenCV ---
arr = np.array(out)
alpha = arr[:, :, 3]

# Closing (fill small holes) + Opening (remove noise)
kernel = np.ones((3, 3), np.uint8)
alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel, iterations=1)
alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel, iterations=1)

# Feather edges
alpha_img = Image.fromarray(alpha)
alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1))

# Recombine RGBA
arr[:, :, 3] = np.array(alpha_img)
refined = Image.fromarray(arr, mode="RGBA")

refined.save(out_path, format="PNG")
print(f"✅ Refined: {in_path} → {out_path} ({mode})")
