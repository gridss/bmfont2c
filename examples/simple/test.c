#include "fontlibrary.h"
#include <stdio.h>

void print_char(fontStyle_t *font, char c)
{
	const uint8_t width_px = font->GlyphWidth[c - font->FirstAsciiCode];
	const uint8_t width_bytes = font->GlyphBytesWidth;
	const uint8_t height_px = font->GlyphHeight;
	const uint8_t *bitmap = &font->GlyphBitmaps[(width_bytes * height_px) * (c - font->FirstAsciiCode)];

	uint8_t j, i_px, i_bytes;

	// For each row
	for (j = 0; j < height_px; j++) {
		// For each byte in width
		for (i_px = 0, i_bytes = 0;
		     i_px < width_px && i_bytes < width_bytes;
		     i_bytes++) {
			const uint8_t val = bitmap[j * width_bytes + i_bytes];
			int8_t index_in_byte;
			// For each pixel in the byte
			for (index_in_byte = 7;
			     index_in_byte >= 0 && i_px < width_px;
			     index_in_byte--, i_px++) {
				if (val & (1 << index_in_byte)) {
					printf("o");
				} else {
					printf(".");
				}
			}
		}
		printf("\n");
	}
}

void print_string(fontStyle_t *font, const char *text)
{
	const char *c = text;

	while (*c) {
		print_char(font, *c);
		c++;
	}
}

int main()
{
	print_string(&FontStyle_Liberation, "Hello, world!");
	return 0;
}
