import sys, io
import numpy as np
import cv2
from rembg import remove
from PIL import Image

# --- NumPy Guard ---
if int(np.__version__.split(".")[0]) >= 2:
    raise RuntimeError("Use numpy<2 (NumPy 1.x)")

in_path, out_path = sys.argv[1], sys.argv[2]

# --- Options (tek model) ---
opts = {
    "model": "birefnet-massive",
    "alpha_matting": True,
}

# --- Load image ---
with open(in_path, "rb") as f:
    inp = f.read()
img = Image.open(io.BytesIO(inp)).convert("RGBA")

# --- Get mask ---
mask = remove(img, only_mask=True, **opts)
mask = np.array(mask)

# --- Morphology (light cleanup) ---
kernel = np.ones((3, 3), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

# --- Apply mask ---
arr = np.array(img)
arr[:, :, 3] = mask
refined = Image.fromarray(arr, mode="RGBA")

refined.save(out_path, format="PNG")
print(f"✅ Refined: {in_path} → {out_path} (model=birefnet-massive)")
