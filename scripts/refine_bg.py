import argparse
from PIL import Image
import torch
import numpy as np
from safetensors.torch import load_file
import os, sys

base_dir = os.path.dirname(__file__)

# Hugging Face opsiyonel (gated repo gerekirse)
try:
    from huggingface_hub import hf_hub_download
except ImportError:
    hf_hub_download = None

def load_model(model_name: str):
    if model_name == "dynamic":
        sys.path.append(os.path.join(base_dir, "models", "BiRefNet_dynamic"))
        from birefnet import BiRefNet, BiRefNetConfig
        model = BiRefNet(BiRefNetConfig())
        weights = load_file(os.path.join(base_dir, "models", "BiRefNet_dynamic", "model.safetensors"))
        model.load_state_dict(weights)
        return model

    elif model_name == "hr":
        sys.path.append(os.path.join(base_dir, "models", "BiRefNet_HR"))
        from birefnet import BiRefNet, BiRefNetConfig
        model = BiRefNet(BiRefNetConfig())
        weights = load_file(os.path.join(base_dir, "models", "BiRefNet_HR", "model.safetensors"))
        model.load_state_dict(weights)
        return model

    elif model_name == "rmbg20":
        sys.path.append(os.path.join(base_dir, "models", "RMBG-2.0"))
        from birefnet import BiRefNet, BiRefNetConfig
        model = BiRefNet(BiRefNetConfig())
        weights = load_file(os.path.join(base_dir, "models", "RMBG-2.0", "model.safetensors"))
        model.load_state_dict(weights)
        return model

    else:
        raise ValueError(f"Bilinmeyen model: {model_name}")

def pad_to_multiple(tensor, multiple=32):
    _, _, h, w = tensor.shape
    new_h = ((h + multiple - 1) // multiple) * multiple
    new_w = ((w + multiple - 1) // multiple) * multiple
    pad_h, pad_w = new_h - h, new_w - w
    padded = torch.nn.functional.pad(tensor, (0, pad_w, 0, pad_h), mode="reflect")
    return padded, (h, w)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input image path (JPG/PNG)")
    parser.add_argument("output", help="Output image path (PNG)")
    parser.add_argument("--model", choices=["dynamic", "hr", "rmbg20"], default="dynamic")
    args = parser.parse_args()

    print(f"🔍 Loading BiRefNet model: {args.model}")
    model = load_model(args.model)
    model.eval()

    # Resim oku
    image = Image.open(args.input).convert("RGB")
    arr = np.array(image).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)

    tensor, orig_size = pad_to_multiple(tensor)
    with torch.no_grad():
        pred = model(tensor)
        if isinstance(pred, (list, tuple)):
            pred = pred[0]
        mask = torch.sigmoid(pred).squeeze().cpu().numpy()

    h, w = orig_size
    mask = mask[:h, :w]
    mask = (mask > 0.5).astype(np.uint8) * 255
    mask_img = Image.fromarray(mask).resize(image.size)

    # Alpha uygula
    image.putalpha(mask_img)
    image.save(args.output)

    print(f"✅ Saved: {args.input} → {args.output} (model={args.model})")

if __name__ == "__main__":
    main()
