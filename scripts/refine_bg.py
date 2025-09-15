# scripts/refine_bg.py
import argparse
from rembg import remove
from PIL import Image
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    parser.add_argument("--model", type=str, default="sam-hq")
    args = parser.parse_args()

    with open(args.input_path, "rb") as i:
        input_img = i.read()

    # MODEL'i gerçekten args.model’den al
    output = remove(
        input_img,
        model_name=args.model
    )

    with open(args.output_path, "wb") as o:
        o.write(output)

if __name__ == "__main__":
    sys.exit(main())
