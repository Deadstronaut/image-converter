import sys
import cv2
import numpy as np
from rembg import remove
from PIL import Image

if len(sys.argv) < 3:
    print("Usage: python refine_bg.py input.jpg output.png")
    sys.exit(1)

inp, outp = sys.argv[1], sys.argv[2]

# --- Load input
with open(inp, "rb") as f:
    input_bytes = f.read()

# --- Remove BG
result = remove(input_bytes, alpha_matting=True,
                alpha_matting_foreground_threshold=220,
                alpha_matting_background_threshold=30,
                alpha_matting_erode_size=1)

# --- Convert to numpy for refinement
image = Image.open(io.BytesIO(result)).convert("RGBA")
arr = np.array(image)

# --- Extract alpha channel
alpha = arr[:, :, 3]

# --- Smooth edges (morph + blur)
kernel = np.ones((3, 3), np.uint8)
alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel, iterations=1)
alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

arr[:, :, 3] = alpha

# --- Save result
Image.fromarray(arr).save(outp)
print(f"✅ Saved refined: {outp}")
