from PIL import Image
import os

def convert_png_to_ico(png_path, ico_path):
    try:
        img = Image.open(png_path)
        # Prepare icon sizes
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, format='ICO', sizes=icon_sizes)
        print(f"Successfully converted {png_path} to {ico_path} with sizes: {icon_sizes}")
    except Exception as e:
        print(f"Error converting image: {e}")

if __name__ == "__main__":
    current_dir = os.getcwd()
    assets_dir = os.path.join(current_dir, "assets")
    png_file = os.path.join(assets_dir, "logo.png")
    ico_file = os.path.join(assets_dir, "logo.ico")

    if os.path.exists(png_file):
        convert_png_to_ico(png_file, ico_file)
    else:
        print(f"Error: {png_file} does not exist.")
