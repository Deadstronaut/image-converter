import sys
import argparse
from rembg import remove, new_session

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    parser.add_argument("--model", default="u2net")
    args = parser.parse_args()

    # input oku
    with open(args.input_path, "rb") as f:
        input_img = f.read()

    # sadece senin seçtiğin modelle session aç
    session = new_session(model_name=args.model)

    # remove'u session ile çağır
    result = remove(input_img, session=session)

    # çıktıyı yaz
    with open(args.output_path, "wb") as f:
        f.write(result)

if __name__ == "__main__":
    sys.exit(main())
