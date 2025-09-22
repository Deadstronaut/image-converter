# scripts/refine_bg.py
import argparse
from PIL import Image
import torch
import numpy as np
import os, sys, importlib.util

base_dir = os.path.dirname(__file__)

def load_model():
    model_dir = os.path.join(base_dir, "models", "RMBG-2.0")

    # birefnet import düzeltmeleri (senin kodun aynı kalıyor)
    biref_path = os.path.join(model_dir, "birefnet.py")
    with open(biref_path, "r", encoding="utf-8") as f:
        src = f.read()
    src = src.replace("from .BiRefNet_config import BiRefNetConfig",
                      "from BiRefNet_config import BiRefNetConfig")
    fixed_biref_path = os.path.join(model_dir, "_birefnet_fixed.py")
    with open(fixed_biref_path, "w", encoding="utf-8") as f:
        f.write(src)

    # config import
    cfg_path = os.path.join(model_dir, "BiRefNet_config.py")
    spec_cfg = importlib.util.spec_from_file_location("BiRefNet_config", cfg_path)
    cfg_module = importlib.util.module_from_spec(spec_cfg)
    spec_cfg.loader.exec_module(cfg_module)
    sys.modules["BiRefNet_config"] = cfg_module

    # birefnet import
    spec_biref = importlib.util.spec_from_file_location("birefnet", fixed_biref_path)
    birefnet = importlib.util.module_from_spec(spec_biref)
    spec_biref.loader.exec_module(birefnet)

    BiRefNet, BiRefNetConfig = birefnet.BiRefNet, birefnet.BiRefNetConfig
    model = BiRefNet(BiRefNetConfig())

    # önce safetensors dene
    safepath = os.path.join(model_dir, "model.safetensors")
    binpath = os.path.join(model_dir, "pytorch_model.bin")
    try:
        if os.path.exists(safepath):
            weights = load_file(safepath)
            model.load_state_dict(weights, strict=False)
            print("✅ model.safetensors yüklendi")
        elif os.path.exists(binpath):
            weights = torch.load(binpath, map_location="cpu", weights_only=False)
            model.load_state_dict(weights, strict=False)
            print("✅ pytorch_model.bin yüklendi")
        else:
            raise FileNotFoundError("Hiçbir ağırlık dosyası bulunamadı")
    except Exception as e:
        print("❌ Model yükleme hatası:", e)
        raise
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
    args = parser.parse_args()

    print(f"🔍 Loading BiRefNet model: RMBG-2.0")
    model = load_model()
    model.eval()

    # read image
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

    # apply alpha
    image.putalpha(mask_img)
    image.save(args.output)
    print(f"✅ Saved: {args.input} → {args.output}")


if __name__ == "__main__":
    main()
