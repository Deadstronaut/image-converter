# scripts/refine_bg.py
import argparse
from PIL import Image
import torch
import numpy as np
from safetensors.torch import load_file
import os, sys, importlib.util

base_dir = os.path.dirname(__file__)

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
        model_dir = os.path.join(base_dir, "models", "RMBG-2.0")

        # birefnet.py dosyasını oku ve relative import'u düzelt
        biref_path = os.path.join(model_dir, "birefnet.py")
        with open(biref_path, "r", encoding="utf-8") as f:
            src = f.read()
        src = src.replace("from .BiRefNet_config import BiRefNetConfig", "from BiRefNet_config import BiRefNetConfig")

        # temp bir dosya yaz
        fixed_biref_path = os.path.join(model_dir, "_birefnet_fixed.py")
        with open(fixed_biref_path, "w", encoding="utf-8") as f:
            f.write(src)

        # BiRefNet_config modülünü yükle
        cfg_path = os.path.join(model_dir, "BiRefNet_config.py")
        spec_cfg = importlib.util.spec_from_file_location("BiRefNet_config", cfg_path)
        cfg_module = importlib.util.module_from_spec(spec_cfg)
        spec_cfg.loader.exec_module(cfg_module)
        sys.modules["BiRefNet_config"] = cfg_module

        # birefnet_fixed modülünü yükle
        spec_biref = importlib.util.spec_from_file_location("birefnet", fixed_biref_path)
        birefnet = importlib.util.module_from_spec(spec_biref)
        spec_biref.loader.exec_module(birefnet)

        BiRefNet, BiRefNetConfig = birefnet.BiRefNet, birefnet.BiRefNetConfig
        model = BiRefNet(BiRefNetConfig())
        weights = load_file(os.path.join(model_dir, "model.safetensors"))
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
