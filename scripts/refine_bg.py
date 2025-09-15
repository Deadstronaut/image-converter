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
parser.add_argument("--fg", type=int, default=220, help="Foreground threshold")
parser.add_argument("--bg", type=int, default=30, help="Background threshold")
parser.add_argument("--erode", type=int, default=1, help="Erode size")
parser.add_argument("--fill-holes", type=lambda v: v.lower() in ("1","true","yes"), default=True)
parser.add_argument("--blur", type=float, default=1.0, help="Gaussian blur radius")
parser.add_argument("--model", type=str, default="isnet-general-use",
    choices=["u2net","u2netp","u2net_human_seg","u2net_cloth_seg","silueta",
         "isnet-general-use","isnet-anime",
         "sam","sam-hq",
         "birefnet-general","birefnet-general-lite","birefnet-portrait",
         "birefnet-dis","birefnet-hrsod","birefnet-cod","birefnet-massive"],
    help="Kullanılacak model")
args = parser.parse_args()

in_path, out_path = args.input, args.output

opts = {
    "model": args.model,
    "alpha_matting": True,
    "alpha_matting_foreground_threshold": args.fg,
    "alpha_matting_background_threshold": args.bg,
    "alpha_matting_erode_size": args.erode,
}

# --- Load image ---
with open(in_path, "rb") as f:
    inp = f.read()
img = Image.open(io.BytesIO(inp)).convert("RGBA")

# --- Get mask ---
mask = remove(img, only_mask=True, **opts)
mask = np.array(mask)

# --- Morphological refinements ---
kernel = np.ones((3, 3), np.uint8)
if args.fill_holes:
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

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
print(f"✅ Refined: {in_path} → {out_path} (model={args.model}, fg={args.fg}, bg={args.bg}, erode={args.erode}, blur={args.blur}, fill_holes={args.fill_holes})")
