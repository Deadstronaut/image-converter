# scripts/refine_bg.py
import sys, io, argparse
import numpy as np
import cv2
from rembg import remove, new_session
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
parser.add_argument("--blur", type=float, default=1.0, help="Gaussian blur radius")
args = parser.parse_args()

in_path, out_path = args.input, args.output

# --- Session ---
print(f"📦 Loading model session: {args.model}")
session = new_session(args.model)

# --- Load image ---
with open(in_path, "rb") as f:
    inp = f.read()
img = Image.open(io.BytesIO(inp)).convert("RGBA")

# --- Get mask ---
mask = remove(img, only_mask=True, session=session)
mask = np.array(mask)

# --- Feather edges ---
if args.blur > 0:
    mask_img = Image.fromarray(mask)
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=args.blur))
    mask = np.array(mask_img)

# --- Apply mask ---
arr = np.array(img)
arr[:, :, 3] = mask
refined = Image.fromarray(arr, mode="RGBA")

refined.save(out_path, format="PNG")
print(f"✅ Refined: {in_path} → {out_path} (model={args.model}, blur={args.blur})")
