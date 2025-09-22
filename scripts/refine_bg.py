"""Refine product backgrounds using locally downloaded BiRefNet weights."""

import argparse
import os
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from safetensors.torch import load_file

# Allow local model packages to be resolved when the script is invoked via subprocess
sys.path.append(os.path.dirname(__file__))

# --- Optional transformers dependency ----------------------------------------------------
try:
    from transformers import PreTrainedModel, PretrainedConfig  # type: ignore
except ImportError:  # pragma: no cover - lightweight fallback for Actions runner
    class PreTrainedModel(torch.nn.Module):  # type: ignore
        def __init__(self, *args, **kwargs):
            super().__init__()

    class PretrainedConfig:  # type: ignore
        pass

SCRIPT_DIR = Path(__file__).resolve().parent

MODEL_SPECS = {
    "dynamic": {
        "module": "models.BiRefNet_dynamic.birefnet",
        "model_attr": "BiRefNet",
        "config_attr": "BiRefNetConfig",
        "weights": SCRIPT_DIR / "models" / "BiRefNet_dynamic" / "model.safetensors",
        "expected_dir": SCRIPT_DIR / "models" / "BiRefNet_dynamic",
    },
    "hr": {
        "module": "models.BiRefNet_HR.birefnet",
        "model_attr": "BiRefNet",
        "config_attr": "BiRefNetConfig",
        "weights": SCRIPT_DIR / "models" / "BiRefNet_HR" / "model.safetensors",
        "expected_dir": SCRIPT_DIR / "models" / "BiRefNet_HR",
    },
    "general": {
        "module": "models.BiRefNet_general.birefnet",
        "model_attr": "BiRefNet",
        "config_attr": "BiRefNetConfig",
        "weights": SCRIPT_DIR / "models" / "BiRefNet_general" / "model.safetensors",
        "expected_dir": SCRIPT_DIR / "models" / "BiRefNet_general",
    },
}

_MODEL_CACHE = {}


def load_model(model_name: str):
    if model_name not in MODEL_SPECS:
        raise ValueError(f"Unknown model: {model_name}")

    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]

    spec = MODEL_SPECS[model_name]
    try:
        module = import_module(spec["module"])
    except ModuleNotFoundError as exc:
        missing_name = getattr(exc, "name", "") or ""
        if missing_name == spec["module"]:
            raise RuntimeError(
                "Model '" + model_name + "' is not available locally. "
                + "Expected package under '" + str(spec["expected_dir"]) + "'.\n"
                + "Download the model repository via git lfs from Hugging Face and try again."
            ) from exc
        raise RuntimeError(
            "Model '" + model_name + "' dependencies are missing (failed to import '" + missing_name + "').\n"
            + "Install required Python packages, for example: pip install transformers huggingface-hub accelerate"
        ) from exc

    model_cls = getattr(module, spec["model_attr"])
    config_cls = getattr(module, spec["config_attr"])
    weights_path = spec["weights"]
    if not weights_path.exists():
        raise FileNotFoundError(
            "Weights file not found for model '" + model_name + "'. Expected: " + str(weights_path)
        )

    weights = load_file(str(weights_path))
    model = model_cls(config_cls())
    model.load_state_dict(weights)
    model.eval()
    _MODEL_CACHE[model_name] = model
    return model


def pad_to_multiple(tensor: torch.Tensor, multiple: int = 32):
    _, _, h, w = tensor.shape
    new_h = ((h + multiple - 1) // multiple) * multiple
    new_w = ((w + multiple - 1) // multiple) * multiple
    pad_h = new_h - h
    pad_w = new_w - w
    padded = torch.nn.functional.pad(tensor, (0, pad_w, 0, pad_h), mode="reflect")
    return padded, (h, w)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input image path (JPG/PNG)")
    parser.add_argument("output", help="Output image path (PNG)")
    parser.add_argument(
        "--model",
        choices=["hr", "dynamic", "general"],
        default="dynamic",
        help="BiRefNet model to use",
    )
    args = parser.parse_args()

    print(f"Loading BiRefNet model: {args.model}")
    model = load_model(args.model)

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

    print(f"Saved refined image: {args.output} (model={args.model})")


if __name__ == "__main__":
    main()
