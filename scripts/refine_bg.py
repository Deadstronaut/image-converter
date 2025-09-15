# scripts/refine_bg.py
import argparse
from PIL import Image
import torch
from transformers import AutoModelForImageSegmentation, AutoProcessor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input image path (JPG/PNG)")
    parser.add_argument("output", help="Output image path (PNG)")
    parser.add_argument("--model", choices=["hr","dynamic"], default="dynamic",
                        help="Kullanılacak BiRefNet modeli: hr veya dynamic")
    args = parser.parse_args()

    # Model path seçimi
    model_path = (
        "scripts/models/BiRefNet_HR"
        if args.model == "hr"
        else "scripts/models/BiRefNet_dynamic"
    )

    print(f"🔍 Loading model from {model_path} ...")
    model = AutoModelForImageSegmentation.from_pretrained(model_path, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)

    # Image oku
    image = Image.open(args.input).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    # Prediction
    with torch.no_grad():
        preds = model(**inputs).logits

    mask = preds[0].sigmoid().squeeze()
    mask = (mask > 0.5).float() * 255  # binarize
    mask_img = Image.fromarray(mask.byte().cpu().numpy()).resize(image.size)

    # Apply alpha mask
    image.putalpha(mask_img)
    image.save(args.output)

    print(f"✅ Saved: {args.input} → {args.output} (model={args.model})")

if __name__ == "__main__":
    main()
