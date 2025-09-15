import sys, io, argparse
import numpy as np
from rembg import remove
from PIL import Image

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

opts = {"model": args.model}

# --- Load image ---
with open(in_path, "rb") as f:
    inp = f.read()
img = Image.open(io.BytesIO(inp)).convert("RGBA")

# --- Remove BG ---
result = remove(img, **opts)

result.save(out_path, format="PNG")
print(f"✅ Refined: {in_path} → {out_path} (model={args.model})")
