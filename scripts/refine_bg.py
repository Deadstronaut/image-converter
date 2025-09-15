# scripts/refine_bg.py
import sys, io, argparse
import numpy as np
import cv2
from rembg import remove
from PIL import Image, ImageFilter

# --- NumPy Guard ---
if int(np.__version__.split(".")[0]) >= 2:
    raise RuntimeError("Use numpy<2 (NumPy 1.x)")

# --- Args ---
parser = argparse.ArgumentParser()
parser.add_argument("input", help="Input image path")
parser.add_argument("output", help="Output image path")
parser.add_argument("--model", type=str, default="birefnet-massive",
    choices=[
        "u2net","u2netp","u2net_human_seg","u2net_cloth_seg","silueta",
        "isnet-general-use","isnet-anime",
        "sam","sam-hq",
        "birefnet-general","birefnet-general-lite","birefnet-portrait",
        "birefnet-dis","birefnet-hrsod","birefnet-cod","birefnet-massive"
    ],
    help="Kullanılacak model")
args = parser.parse_args()

in_path, out_path = args.input, args.output

opts = {
    "model": args.model,
    "alpha_matting": False
}

# --- DEBUG ---
print("🔍 RefineBG Debug")
print("  Input:", in_path)
print("  Output:", out_path)
print("  Selected Model:", args.model)
print("  Options:", opts)

# --- Load image ---
with open(in_path, "rb") as f:
    inp = f.read()
img = Image.open(io.BytesIO(inp)).convert("RGBA")

# --- Get mask ---
try:
    mask = remove(img, only_mask=True, **opts)
    print("✅ remove() çalıştı, maske alındı")
except Exception as e:
    print("❌ remove() hata:", e)
    sys.exit(1)

mask = np.array(mask)

# --- Apply mask ---
arr = np.array(img)
arr[:, :, 3] = mask
refined = Image.fromarray(arr, mode="RGBA")

refined.save(out_path, format="PNG")
print(f"🎯 DONE: {in_path} → {out_path} (model={args.model})")
