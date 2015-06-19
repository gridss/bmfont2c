#!/usr/bin/env python
# encoding: utf-8

# Filename    : bmfont2c.py
# Description : Converts bitmap font(s) generated by BMFont to C code
# Author      : Lars Ole Pontoppidan, 2014
# URL         : http://larsee.dk/

script_revision = '2014-05-24'

# --------------------------------  LICENSE  -----------------------------------
#
# Copyright (c) 2014, Lars Ole Pontoppidan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# *  Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# *  Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# *  Neither the name of the original author (Lars Ole Pontoppidan) nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

# --------------------------------  READ ME  ------------------------------------
#
# bmfont2c.py reads bitmap font output from the Bitmap Font Generator by
# AngelCode: http://www.angelcode.com/products/bmfont/  and outputs byte table
# arrays in C language suitable for rendering on monochrome matrix LCD.
#
# The conversion process is configured in a configuration file. Multiple font
# conversions can be specified, which will result in multiple fonts being output
# in the same C header and source file.
#
# Usage: python bmfont2c.py <config filename>
# or:    python bmfont2c.py   (will use "bmfont2c.cfg" as config filename)
#
# NOTE: When generating the font in BMFont remember to select XML format as the
# font descriptor format.
#
# The script requires Pillow Python module for image processing, and should work
# in both Python 2 and 3.
#
#
# Example config file:
# ---------------------
#
# [General]
# OutputHeader = fontlibrary.h
# OutputSource = fontlibrary.c
#
# [Font1]
# InputFile = somefont.fnt
# CFontName = SomeFont
# FirstAscii = 32
# LastAscii = 126
# BytesWidth = 2
# BytesHeight = 16
# CropX = 0
# CropY = 3
# FixedWidth = 0
#
# [Font2]
# InputFile = otherfont.fnt
# CFontName = OtherFont
#  (...)
#

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from PIL import Image as image
from xml.dom import minidom
import sys
import os

datatype = 'uint8_t'
extra_bitmap_type_specifier = ''

header_start = """
//
// Bitmap font C header file generated by bmfont2c.py
//

#ifndef FONTLIBRARY_H_
#define FONTLIBRARY_H_

#include <stdint.h>

typedef struct
{{
    {datatype} GlyphCount;
    {datatype} FirstAsciiCode;
    {datatype} GlyphBytesWidth;
    {datatype} GlyphHeight;
    {datatype} FixedWidth;
    {datatype} const *GlyphWidth;
    {datatype} const *GlyphBitmaps;
    {datatype} const *GlyphOffsets;
}} fontStyle_t;

"""

header_end = """

#endif /* FONTLIBRARY_H_ */
"""


source_start = """
//
// Bitmap font C source generated by bmfont2c.py
//

#include <stdint.h>
#include <stdlib.h>
"""

total_ram = 0


class Config:
    def __init__(self, cfg, section):
        self.font_input  = cfg.get(section, "InputFile")
        self.c_fontname  = cfg.get(section, "CFontName")

        # Ascii range to grab
        self.first_ascii  = cfg.getint(section, "FirstAscii")
        self.last_ascii   = cfg.getint(section, "LastAscii")

        # Glyph sizing
        self.bytes_width  = cfg.getint(section, "BytesWidth")
        self.bytes_height = cfg.getint(section, "BytesHeight")
        self.crop_x       = cfg.getint(section, "CropX")
        self.crop_y       = cfg.getint(section, "CropY")

        if cfg.has_option(section, "Strings"):
            strings_file = cfg.get(section, "Strings")
            self.chars = loadStringsCharSet(strings_file)
        else:
            self.chars = None

        if cfg.has_option(section, "FixedWidth"):
            self.fixed_width = cfg.getint(section, "FixedWidth")
        else:
            self.fixed_width = 0

def loadStringsCharSet(strings_file):
    '''Load strings from a file, create a set with characters used.'''
    with open(strings_file) as f:
        strings = f.readlines()

    return set(''.join(strings).replace('\n', ''))


def makeFontStyleDecl(config):
    s = "\nfontStyle_t FontStyle_%s = \n" % config.c_fontname
    s += "{\n"
    s += "    %d, // Glyph count\n" % (config.last_ascii - config.first_ascii + 1)
    s += "    %d, // First ascii code\n" % config.first_ascii
    s += "    %d, // Glyph width (bytes)\n" % config.bytes_width
    s += "    %d, // Glyph height (bytes)\n" % config.bytes_height
    s += "    %d, // Fixed width or 0 if variable\n" % config.fixed_width
    if config.fixed_width == 0:
        s += "    %s_Widths,\n" % config.c_fontname
    else:
        s += "    (void*)0,\n"
    s += "    %s_Bitmaps,\n" % config.c_fontname
    if config.chars:
        s += "    {}_Offsets\n".format(config.c_fontname)
    else:
        s += "    (void*)0,\n"
    s += "};\n"
    return s

def makeFontStyleHeader(config):
    return "\nextern fontStyle_t FontStyle_%s;" % config.c_fontname


def makeBitmapsOffsetTable(config):
    s = '\nint8_t {}_Offsets[] = \n{{\n    '.format(config.c_fontname)

    i = 0
    n = 0
    for ascii in range(config.first_ascii, config.last_ascii + 1):
        char = chr(ascii)

        if config.chars and char in config.chars:
            s += '{: 2}, '.format(n)
            n = n + 1
        else:
            s += '-1, '

        i = i + 1
        if i % 8 == 0:
            s += '\n    '

    s += '\n}\n'

    return s

def makeBitmapsTable(config, img, glyphs):
    size = (config.last_ascii - config.first_ascii + 1) * config.bytes_width * config.bytes_height
    s = "\nstatic const %s %s %s_Bitmaps[] = \n{" % (datatype,
                                                     extra_bitmap_type_specifier,
                                                     config.c_fontname)
    global total_ram
    total_ram += size

    for ascii in range(config.first_ascii, config.last_ascii + 1):
        char = chr(ascii)
        if config.chars and char not in config.chars:
            continue

        # Find the glyph
        glyph_found = None
        for glyph in glyphs:
            if glyph.id == ascii:
                glyph_found = glyph
                break

        if glyph_found is None:
            print("INFO: No glyph for ASCII: %d, using substitute" % ascii)
            s += "\n    // No glyph for ASCII: %d, using substitute:" % ascii
            # We use first glyph instead
            glyph_found = glyphs[0]

        s += glyph_found.makeBitmapCode(img, config.bytes_width * 8, config.bytes_height,
                             config.crop_x, config.crop_y)

    s += "};\n"

    return s


def makeWidthsTable(config, glyphs):
    count = config.last_ascii - config.first_ascii + 1
    s = "\n%s %s_Widths[%u] = \n{" % (datatype, config.c_fontname, count)
    i = 0
    global total_ram
    total_ram += count

    for ascii in range(config.first_ascii, config.last_ascii + 1):
        char = chr(ascii)
        if config.chars and char not in config.chars:
            continue

        # Find the glyph
        glyph_found = None
        for glyph in glyphs:
            if glyph.id == ascii:
                glyph_found = glyph
                break

        if glyph_found is None:
            # We use first glyph instead
            glyph_found = glyphs[0]

        if i == 0:
            s += "\n    "

        i = (i + 1) % 8
        s += glyph_found.makeWidthCode()

    s += "\n};\n"
    return s


def loadFont(config):
    # Open xml
    print("Reading font description: " + config.font_input)
    font = minidom.parse(config.font_input)

    # Open page 0 image:
    file = font.getElementsByTagName('page')[0].attributes['file'].value
    print("Reading font bitmap: " + file)
    img = image.open(file)

    # Get the glyphs
    chars = font.getElementsByTagName('char')

    glyphs = []
    for char in chars:
        glyphs.append(Glyph(char))

    return (img, glyphs)

def makeFontSource(config):
    img, glyphs = loadFont(config)

    source = makeBitmapsTable(config, img, glyphs)

    if config.fixed_width == 0:
        source += makeWidthsTable(config, glyphs)

    if config.chars:
        source += makeBitmapsOffsetTable(config)

    source += makeFontStyleDecl(config)

    return source

def processConfig(cfg):
    # Get the general configuration
    output_header = cfg.get("General", "OutputHeader")
    output_source = cfg.get("General", "OutputSource")

    # Start up the header and source file
    header = header_start.format(datatype=datatype)
    source = source_start
    source += '#include "%s"\n' % output_header

    font_no = 1

    global total_ram
    total_ram = 0

    while cfg.has_section("Font%d" % font_no):
        config = Config(cfg, "Font%d" % font_no)
        source = source + makeFontSource(config)
        header = header + makeFontStyleHeader(config)
        font_no += 1

    header += header_end

    print("INFO: Font tables use: %u bytes" % total_ram)

    print("Writing output: " + output_source)

    with open(output_source, "w") as text_file:
        text_file.write(source)

    print("Writing output: " + output_header)

    with open(output_header, "w") as text_file:
        text_file.write(header)


class Glyph:
    def __init__(self, char):
        self.id = int(char.attributes['id'].value)
        self.x  = int(char.attributes['x'].value)
        self.y  = int(char.attributes['y'].value)
        self.width = int(char.attributes['width'].value)
        self.height = int(char.attributes['height'].value)
        self.xoffset  = int(char.attributes['xoffset'].value)
        self.yoffset  = int(char.attributes['yoffset'].value)
        self.xadvance = int(char.attributes['xadvance'].value)

    def printRaw(self, img):
        print("id: %d, width: %d, height: %d" % (self.id, self.width, self.height))
        print("xoffset: %d, yoffset: %d, xadvance: %d" % (self.xoffset, self.yoffset, self.xadvance))
        for y in range(self.y, self.y + self.height):
            s = ""
            for x in range(self.x, self.x + self.width):
                if img.getpixel((x,y)) > 127:
                    s += '1'
                else:
                    s += '0'
            print(s)

    def printNormalized(self, img, width, height, crop_x = 0, crop_y = 0):
        for y in range(0, height):
            s = ""
            for x in range(0, width):
                use_x = x - self.xoffset + crop_x
                use_y = y - self.yoffset + crop_y
                pixel = '0'
                if (use_x >= 0) and (use_x < self.width) and (use_y >= 0) and (use_y < self.height):
                    if img.getpixel((use_x + self.x, use_y + self.y)) > 127:
                        pixel = '1'

                s += pixel
            print(s)

    def makeBitmapCode(self, img, width, height, crop_x = 0, crop_y = 0):
        s = '\n    // ASCII: %d, char width: %d' % (self.id, self.xadvance)
        for y in range(0, height):
            comment = ""
            bytestring = ""
            byte = 0
            mask = 128
            for x in range(0, width):
                use_x = x - self.xoffset + crop_x
                use_y = y - self.yoffset + crop_y
                pixel = 0
                if (use_x >= 0) and (use_x < self.width) and (use_y >= 0) and (use_y < self.height):
                    if img.getpixel((use_x + self.x, use_y + self.y)) > 127:
                        pixel = 1

                if pixel != 0:
                    comment += 'O'
                    byte |= mask
                else:
                    if x >= self.xadvance:
                        comment += '.'
                    else:
                        comment += '-'

                mask = mask // 2

                if mask == 0:
                    bytestring += "0x%02x, " % byte
                    mask = 128
                    byte = 0

            if mask != 128:
                bytestring += "0x%02x, " % byte

            s += "\n    " + bytestring + " // " + comment

        return s + "\n"

    def makeWidthCode(self):
        return '%2d, ' % (self.xadvance)

if __name__ == "__main__":
    print("BMFont to C source converter by Lars Ole Pontoppidan, %s\n" % script_revision)

    if len(sys.argv) == 2:
        cfgfile = sys.argv[1]
    elif len(sys.argv) == 1:
        cfgfile = 'bmfont2c.cfg'
    else:
        print("ERROR: Invalid command line arguments\n")
        exit()

    if os.path.isfile(cfgfile):
        print("Reading configuration file: " + cfgfile)
        cfg = configparser.ConfigParser()
        cfg.read(cfgfile)
        processConfig(cfg)
    else:
        print("ERROR: Configuration file '%s' not found\n" % cfgfile)

