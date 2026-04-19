from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QImageWriter, QPainter
from PySide6.QtSvg import QSvgRenderer


# 參數控制區
DEFAULT_INPUT_SVG = Path("asset/logo.svg") # 預設來源 SVG
DEFAULT_OUTPUT_ICO = Path("asset/logo.ico") # 預設輸出 Windows icon
DEFAULT_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256) # ICO 內常用尺寸
ICO_PNG_BIT_DEPTH = 32 # Windows icon 使用 RGBA PNG frame


# 將 SVG render 成指定尺寸的透明 PNG bytes
def render_svg_to_png_bytes(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)

    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    buffer_data = QByteArray()
    buffer = QBuffer(buffer_data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(buffer_data)


# 將多個 PNG frame 包成 ICO 檔案
def write_ico(output_path: Path, png_frames: list[tuple[int, bytes]]) -> None:
    header_size = 6
    entry_size = 16
    image_offset = header_size + entry_size * len(png_frames)
    entries = []
    images = []

    for size, png_bytes in png_frames:
        size_byte = 0 if size >= 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                size_byte,
                size_byte,
                0,
                0,
                1,
                ICO_PNG_BIT_DEPTH,
                len(png_bytes),
                image_offset,
            )
        )
        images.append(png_bytes)
        image_offset += len(png_bytes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as file:
        file.write(struct.pack("<HHH", 0, 1, len(png_frames)))
        for entry in entries:
            file.write(entry)
        for image in images:
            file.write(image)


# 解析逗號分隔的 icon 尺寸
def parse_sizes(value: str) -> tuple[int, ...]:
    sizes = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not sizes:
        raise argparse.ArgumentTypeError("At least one size is required.")
    invalid_sizes = [size for size in sizes if size < 1 or size > 256]
    if invalid_sizes:
        raise argparse.ArgumentTypeError("ICO sizes must be between 1 and 256.")
    return sizes


# CLI 參數
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert SVG to Windows ICO.")
    parser.add_argument(
        "input_svg",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_SVG,
        help=f"Input SVG path. Default: {DEFAULT_INPUT_SVG}",
    )
    parser.add_argument(
        "output_ico",
        nargs="?",
        type=Path,
        default=DEFAULT_OUTPUT_ICO,
        help=f"Output ICO path. Default: {DEFAULT_OUTPUT_ICO}",
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=DEFAULT_ICON_SIZES,
        help="Comma-separated icon sizes. Default: 16,24,32,48,64,128,256",
    )
    return parser.parse_args()


# 主流程
def main() -> int:
    args = parse_args()
    input_svg = args.input_svg
    output_ico = args.output_ico

    if not input_svg.exists():
        print(f"SVG not found: {input_svg}")
        return 1

    if b"ico" not in QImageWriter.supportedImageFormats():
        print("Current Qt image plugins do not support ICO output.")
        return 1

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    renderer = QSvgRenderer(str(input_svg))
    if not renderer.isValid():
        print(f"Invalid SVG: {input_svg}")
        return 1

    png_frames = [(size, render_svg_to_png_bytes(renderer, size)) for size in args.sizes]
    write_ico(output_ico, png_frames)
    print(f"ICO created: {output_ico}")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
