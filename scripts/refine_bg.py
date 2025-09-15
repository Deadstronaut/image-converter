# scripts/refine_bg.py
import argparse
from PIL import Image
import torch
import numpy as np
from safetensors.torch import load_file
import sys, os
sys.path.append(os.path.dirname(__file__))


# --- Model importları ---
from models.BiRefNet_dynamic.birefnet import BiRefNet as DynamicNet, BiRefNetConfig as DynamicConfig
from models.BiRefNet_HR.birefnet import BiRefNet as HRNet, BiRefNetConfig as HRConfig


def load_model(model_name: str):
    if model_name == "dynamic":
        config = DynamicConfig()
        model = DynamicNet(config)
        weights = load_file("scripts/models/BiRefNet_dynamic/model.safetensors")
        model.load_state_dict(weights)
        return model
    elif model_name == "hr":
        config = HRConfig()
        model = HRNet(config)
        weights = load_file("scripts/models/BiRefNet_HR/model.safetensors")
        model.load_state_dict(weights)
        return model
    else:
        raise ValueError(f"Bilinmeyen model: {model_name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input image path (JPG/PNG)")
    parser.add_argument("output", help="Output image path (PNG)")
    parser.add_argument("--model", choices=["hr", "dynamic"], default="dynamic",
                        help="Kullanılacak BiRefNet modeli")
    args = parser.parse_args()

    print(f"🔍 Loading BiRefNet model: {args.model}")
    model = load_model(args.model)
    model.eval()

    # Image oku
    image = Image.open(args.input).convert("RGB")
    arr = np.array(image).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)  # [1,3,H,W]

    with torch.no_grad():
        pred = model(tensor)
        if isinstance(pred, (list, tuple)):
            pred = pred[0]
        mask = torch.sigmoid(pred).squeeze().cpu().numpy()

    # Binarize
    mask = (mask > 0.5).astype(np.uint8) * 255
    mask_img = Image.fromarray(mask).resize(image.size)

    # Apply alpha mask
    image.putalpha(mask_img)
    image.save(args.output)

    print(f"✅ Saved: {args.input} → {args.output} (model={args.model})")


if __name__ == "__main__":
    main()
