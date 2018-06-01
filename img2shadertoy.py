#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Convert image to a Shadertoy script
"""

import os, sys, argparse, logging
logging.basicConfig(format='-- %(message)s')
logger = logging.getLogger('readbmp')
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("filename", help="path to bmp file")
	args = parser.parse_args()

	with open(args.filename, "rb") as binary_file:
		data = binary_file.read()
		logger.info("Read file {0} into memory".format(args.filename))

	# https://en.wikipedia.org/wiki/BMP_file_format
	header_text = data[0:2].decode('utf-8')
	logger.info("BMP header {0}".format(header_text))
	if header_text != "BM":
		raise RuntimeError("File has incorrect header, expected 'BM'")

	filesize = int.from_bytes(data[2:6], byteorder='little')
	logger.info("File size in header {0}".format(filesize))
	if os.path.getsize(args.filename) != filesize:
		raise RuntimeError("Header reports incorrect file size")

	imgdata_offset = int.from_bytes(data[10:14], byteorder='little')
	logger.info("Image data offset {0}".format(imgdata_offset))

	dib_header_size = int.from_bytes(data[14:18], byteorder='little')
	logger.info("DIB header size {0}".format(dib_header_size))
	if dib_header_size != 40:
		raise RuntimeError("DIB header size 40 (BITMAPINFOHEADER) expected")

	image_width = int.from_bytes(data[18:22], byteorder='little')
	logger.info("Image width {0}".format(image_width))
	if image_width % 32 != 0:
		raise RuntimeError("Image width multiple of 32 expected")

	image_height = int.from_bytes(data[22:26], byteorder='little')
	logger.info("Image height {0}".format(image_height))

	color_planes = int.from_bytes(data[26:28], byteorder='little')
	logger.info("Color planes {0}".format(color_planes))
	if color_planes != 1:
		raise RuntimeError("1 color plane expected")

	bits_per_pixel = int.from_bytes(data[28:30], byteorder='little')
	logger.info("Bits per pixel {0}".format(bits_per_pixel))
	if bits_per_pixel != 1:
		raise RuntimeError("Only 1 bit per pixel supported")

	compression_method = int.from_bytes(data[30:34], byteorder='little')
	logger.info("Compression method {0}".format(compression_method))
	if compression_method != 0:
		raise RuntimeError("Only compression method 0 is supported")

	image_size = int.from_bytes(data[34:38], byteorder='little')
	logger.info("Raw image size {0}".format(image_size))

	palette_size = int.from_bytes(data[46:50], byteorder='little')
	logger.info("Palette size {0}".format(palette_size))

	palette = [None] * palette_size
	for i in range(palette_size):
		palette_index = 14 + dib_header_size + i * 4
		blue = data[palette_index]
		green = data[palette_index + 1]
		red = data[palette_index + 2]
		palette[i] = (red, green, blue)
	logger.info("Palette {0}".format(str(palette)))

	row_size = int(int((bits_per_pixel * image_width + 31) / 32) * 4)
	logger.info("Row size {0} bytes".format(row_size))

	row_data = [None] * image_height
	for i in range(image_height):
		row_index = imgdata_offset + i * row_size
		row_data[i] = data[row_index : row_index + row_size]

	# Generate output
	print("const ivec2 bitmap_size = ivec2({0}, {1});".format(image_width, image_height))
	print("const int longs_per_line = {0};".format(row_size // 4))

	print("const vec3[] palette = vec3[] (")
	for i in range(palette_size):
		color = palette[i]
		print("vec3({0:.2f}, {1:.2f}, {2:.2f})".format(color[0] / 255, color[1] / 255, color[2] / 255) + ("," if i != palette_size-1 else ""))
	print(");")

	print("const int[] bitmap = int[] (")
	for i in range(image_height):
		hexvals = []
		for k in range(row_size // 4):
			hexvals.append("0x" + row_data[i][k * 4 : (k+1) * 4].hex())
		print(", ".join(hexvals) + ("," if i != image_height-1 else ""))
	print(");")

	print("""void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
	vec2 uv = fragCoord/iResolution.y;
	int palette_index = 0;

	if(uv.x <= 1.0 && uv.y <= 1.0)
	{
		ivec2 fetch_pos = ivec2(uv.x * float(bitmap_size.x), uv.y * float(bitmap_size.y));
		int line_index = fetch_pos.y * longs_per_line;

		int long_index = line_index + fetch_pos.x / 32;
		int bitmap_long = bitmap[long_index];

		int bit_index = 31 - fetch_pos.x % 32;
		int mask = 1 << bit_index;

		palette_index = ((bitmap_long & mask) == 0) ? 0 : 1;
	}

	vec3 col = palette[palette_index];
	fragColor = vec4(col,1.0);
}""")
