# scripts/refine_bg.py
import argparse
from PIL import Image
import torch
import numpy as np
from safetensors.torch import load_file
from huggingface_hub import hf_hub_download
import os

def load_model(model_name: str):
    if model_name == "dynamic":
        from models.BiRefNet_dynamic.birefnet import BiRefNet, BiRefNetConfig
        config = BiRefNetConfig()
        model = BiRefNet(config)
        repo = "ZhengPeng7/BiRefNet_dynamic"
    elif model_name == "hr":
        from models.BiRefNet_HR.birefnet import BiRefNet, BiRefNetConfig
        config = BiRefNetConfig()
        model = BiRefNet(config)
        repo = "ZhengPeng7/BiRefNet_HR"
    else:
        raise ValueError(f"Bilinmeyen model: {model_name}")

    # HuggingFace'den indir
    model_path = hf_hub_download(repo_id=repo, filename="model.safetensors")
    weights = load_file(model_path)
    model.load_state_dict(weights, strict=False)
    return model

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
    parser.add_argument("--model", choices=["hr", "dynamic"], default="dynamic")
    args = parser.parse_args()

    print(f"🔍 Loading BiRefNet model: {args.model}")
    model = load_model(args.model)
    model.eval()

    image = Image.open(args.input).convert("RGB")
    arr = np.array(image).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)

    tensor, orig_size = pad_to_multiple(tensor, multiple=32)

    with torch.no_grad():
        pred = model(tensor)
        if isinstance(pred, (list, tuple)):
            pred = pred[0]
        mask = torch.sigmoid(pred).squeeze().cpu().numpy()

    h, w = orig_size
    mask = mask[:h, :w]

    mask = (mask > 0.5).astype(np.uint8) * 255
    mask_img = Image.fromarray(mask).resize(image.size)

    image.putalpha(mask_img)
    image.save(args.output)

    print(f"✅ Saved: {args.input} → {args.output} (model={args.model})")

if __name__ == "__main__":
    main()
