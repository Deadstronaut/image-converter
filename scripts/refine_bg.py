import sys
import io
import argparse
from rembg import remove
from PIL import Image

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", help="Girdi görseli")
    parser.add_argument("output_path", help="Çıktı görseli")
    parser.add_argument("--model", default="u2net", help="Model adı (örn: u2net, u2netp, sam-hq, isnet-general, ...)")
    args = parser.parse_args()

    with open(args.input_path, "rb") as f:
        input_img = f.read()

    # Sadece model_name parametresi
    result = remove(input_img, model_name=args.model)

    with open(args.output_path, "wb") as f:
        f.write(result)

    return 0

if __name__ == "__main__":
    sys.exit(main())
