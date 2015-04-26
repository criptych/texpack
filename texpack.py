#!/bin/env python
# -*- encoding: utf-8 -*-
################################################################################
## TexPack - Free and open-source TexturePacker alternative
## Copyright (c) 2015 criptych
##
## Released under the MIT License.  See LICENSE file for terms.
##
## Disclaimer:  This tool was not developed from TexturePacker source or by
## reverse engineering of any kind; but through inspection of the TexturePacker
## documentation and independent research and implementation of the features
## advertised therein.
##
################################################################################

import logging
log = logging.getLogger('TexPack')

import math
import os

from PIL import Image
from PIL import ImageChops
from PIL import ImageColor
from PIL import ImageDraw
from PIL import ImageOps

import layouts

################################################################################

import datetime

class Timer(object):
    def __init__(self, name='Timer', callback=None):
        self.name = name
        if callback is not None:
            self.callback = callback

    def callback(self, dt):
        print("%s: %s" % (self.name, dt))

    def __enter__(self):
        self.start = datetime.datetime.now()
        return self

    def __exit__(self, *exc_info):
        self.finish = datetime.datetime.now()
        if self.callback is not None:
            self.callback(self.finish - self.start)

################################################################################

def load_sprites(filenames):
    from glob import glob

    r = []

    for fn in filenames:
        for f in glob(fn):
            f = os.path.abspath(f)
            if os.path.isdir(f):
                for root, dirs, files in os.walk(f):
                    for ff in files:
                        try:
                            r.append(layouts.Sprite(os.path.join(root, ff)))
                        finally:
                            ## Not an image file?
                            pass

            else:
                try:
                    r.append(layouts.Sprite(f))
                finally:
                    ## Not an image file?
                    pass

    return r

def _mask_topleft(A,B,C,D):
    return A

def _mask_topright(A,B,C,D):
    return B

def _mask_bottomleft(A,B,C,D):
    return C

def _mask_bottomright(A,B,C,D):
    return D

def _mask_2of4(A,B,C,D):
    if A == B and C != D:
        return A
    if A == C and B != D:
        return A
    if A == D and B != C:
        return A
    if B == C and A != D:
        return B
    if B == D and A != C:
        return B
    if C == D and A != B:
        return C
    return None

def _mask_3of4(A,B,C,D):
    if A == B and (B == C or B == D):
        return A
    if (A == C or B == C) and C == D:
        return D
    return None

def _mask_auto(A,B,C,D):
    r = _mask_3of4(A,B,C,D)
    s = _mask_2of4(A,B,C,D)
    return r or s

def mask_sprites(sprites, color):
    mask_func = {
        'tl': _mask_topleft,
        'ul': _mask_topleft,
        'tr': _mask_topright,
        'ur': _mask_topright,
        'bl': _mask_bottomleft,
        'll': _mask_bottomleft,
        'br': _mask_bottomright,
        'lr': _mask_bottomright,
        '2of4': _mask_2of4,
        '3of4': _mask_3of4,
        'auto': _mask_auto,
    }.get(color.lower())

    if mask_func is None:
        ## Check color codes
        color = ImageColor.getrgb(color)
        mask_func = lambda A,B,C,D: color

    for i, spr in enumerate(sprites):
        w, h = spr.image.size

        ## Get corner colors
        A = spr.image.getpixel((0,  0  ))
        B = spr.image.getpixel((w-1,0  ))
        C = spr.image.getpixel((0,  h-1))
        D = spr.image.getpixel((w-1,h-1))

        bg = mask_func(A, B, C, D)

        if bg is None:
            continue

        ## based on:
        ## <https://mail.python.org/pipermail/image-sig/2002-December/002092.html>

        outbands = [srcband.point(lambda p: (p != level) and 255)
                    for srcband, level in zip(spr.image.split(), bg)]
        tband = ImageChops.lighter(
            ImageChops.lighter(outbands[0], outbands[1]),
            outbands[2]).convert('1')
        spr.image.putalpha(tband)

    return sprites

def trim_sprites(sprites):
    for i, spr in enumerate(sprites):
        box = spr.image.getbbox()
        spr.image = spr.image.crop(box)
    return sprites

def hash_sprites(sprites):
    return sprites

def alias_sprites(sprites):
    return sprites

def extrude_sprites(sprites, size):
    if size:
        for i, spr in enumerate(sprites):
            w, h = spr.image.size
            image = Image.new(spr.image.mode, (w+size*2, h+size*2), (0,0,0,0))
            A = spr.image.crop((0,  0,  1,1)).resize((size,size))
            B = spr.image.crop((0,  0,  w,1)).resize((w,   size))
            C = spr.image.crop((w-1,0,  w,1)).resize((size,size))
            D = spr.image.crop((0,  0,  1,h)).resize((size,h   ))
            E = spr.image.crop((w-1,0,  w,h)).resize((size,h   ))
            F = spr.image.crop((0,  h-1,1,h)).resize((size,size))
            G = spr.image.crop((0,  h-1,w,h)).resize((w,   size))
            H = spr.image.crop((w-1,h-1,w,h)).resize((size,size))
            image.paste(A, (0,     0     ), A)
            image.paste(B, (size,  0     ), B)
            image.paste(C, (size+w,0     ), C)
            image.paste(D, (0,     size  ), D)
            image.paste(E, (size+w,size  ), E)
            image.paste(F, (0,     size+h), F)
            image.paste(G, (size,  size+h), G)
            image.paste(H, (size+w,size+h), H)
            image.paste(spr.image, (size,size), spr.image)
            spr.image = image
    return sprites

def pad_sprites(sprites, size):
    if size:
        for i, spr in enumerate(sprites):
            w, h = spr.image.size
            image = Image.new(spr.image.mode, (w+size, h+size), (0,0,0,0))
            image.paste(spr.image, (0, 0), spr.image)
            spr.image = image
    return sprites

## Halftone matrix derived, and Bayer matrix copied, from figures in:
## https://engineering.purdue.edu/~bouman/ece637/notes/pdf/Halftoning.pdf

## Void-and-cluster matrix generated using algorithm described in:
## http://home.comcast.net/~ulichney/CV/papers/1993-void-cluster.pdf

BAYER = [
    15, 7,13, 5,
     3,11, 1, 9,
    12, 4,14, 6,
     0, 8, 2,10,
]
HALFTONE = [
    14,10,11,15,
     9, 3, 0, 4,
     8, 2, 1, 5,
    13, 7, 6,12,
]
VOID_CLUSTER = [
]

def quantize_texture(texture, quantize, palette_type, palette_depth, dither):
    colors = 2**int(palette_depth)

    if quantize == 'median-cut':
        method = 0
    elif quantize == 'octree':
        method = 2
    else:
        ## unsupported method
        return texture

    if palette_type == 'web-safe':
        colors = 216
        palette = ''.join([
            '%c%c%c' % (0x33*r, 0x33*g, 0x33*b)
            for r in xrange(6)
                for g in xrange(6)
                    for b in xrange(6)
            ])

    else:
        palette = [0,0,0]*colors
        ## TODO: generate palette

    palimg = Image.new('P', (1,1))
    palimg.putpalette(palette, 'RGB')

    bands = texture.split()

    rgb = Image.merge('RGB', bands[:3])
    alpha = bands[3]

    texture = rgb.quantize(colors, method, 0, palimg)
    texture.putalpha(alpha)
    return texture

################################################################################

def main():
    import argparse

    parser = argparse.ArgumentParser(usage='%(prog)s prefix sprites... [options]')

    parser.add_argument('prefix',
                        help="Prefix for output sheet textures")
    parser.add_argument('sprites', nargs='+',
                        help="Sprite images / folders / wildcards")

    parser.add_argument('--debug', type=ImageColor.getrgb, nargs='?',
                        default=False, const='#00ff00', metavar='COLOR',
                        help="Save textures with debug markup. "
                        "If %(metavar)s is omitted, defaults to '%(const)s'.")

    ########################################################################

    sprite_group = parser.add_argument_group('sprite options')
    sprite_group.add_argument('--trim', action='store_true', default=False,
                              help="Trim sprites to visible area.")
    sprite_group.add_argument('--pad', type=int, default=0, nargs='?', const=1, metavar='SIZE',
                              help="Insert %(metavar)s pixels of padding between sprites. "
                              "If %(metavar)s is omitted, defaults to `%(const)s'.")
    sprite_group.add_argument('--extrude', type=int, default=0, nargs='?', const=1, metavar='SIZE',
                              help="Extrude sprite edges %(metavar)s pixels to avoid color bleed. "
                              "If %(metavar)s is omitted, defaults to `%(const)s'.")
    sprite_group.add_argument('--alias', action='store_true', default=False,
                              help="Find and remove duplicate sprites.")
    sprite_group.add_argument('--mask', nargs='?', default=False, const='3of4', metavar='MASK',
                              help="Mask sprites against background (color or detection method). "
                              "If %(metavar)s is omitted, defaults to `%(const)s'.")

    ########################################################################

    layout_group = parser.add_argument_group('layout options')
    layout_group.add_argument('--layout', type=str.lower, default='shelf', metavar='TYPE',
                              choices=['shelf','stack','max-rects','skyline'],
                              help="Select layout algorithm. (default: %(default)s)")
    layout_group.add_argument('--rotate', action='store_true', default=False,
                              help="Allow layout engine to rotate sprites.")
    layout_group.add_argument('--npot', action='store_true', default=False,
                              help="Allow non-power-of-two sheet dimensions.")
    layout_group.add_argument('--square', action='store_true', default=False,
                              help="Constrain sheet dimensions to a square.")
    layout_group.add_argument('--min-size', type=int, default=0, metavar='SIZE',
                              help="Set minimum sheet dimensions.")
    layout_group.add_argument('--max-size', type=int, default=0, metavar='SIZE',
                              help="Set maximum sheet dimensions.")

    ########################################################################

    texture_group = parser.add_argument_group('texture options')
    texture_group.add_argument('--scale', action='store_true', default=False,
                               help="Produce full- and half-scale images.")
    texture_group.add_argument('--color-depth', type=str.lower, default='RGBA8', metavar='DEPTH',
                               choices=['RGB4','RGBA4','RGB5','RGB565','RGBA5551','RGB8','RGBA8'],
                               help="Select color bit-depth. (default: %(default)s)")
    texture_group.add_argument('--compress', type=str.lower, nargs='?', const='S3TC', metavar='TYPE',
                               choices=['S3TC','ETC','PVRTC','ATITC'], help=
                               "Set texture compression. If %(metavar)s is omitted, defaults to `%(const)s'. "
                               "Overrides --depth, --format, and quantization options.")
    texture_group.add_argument('--quantize', type=str.lower, nargs='?', const='median-cut', metavar='TYPE',
                               choices=['median-cut','histogram','octree','k-means','kohonen','spatial'],
                               help="Select quantization method for indexed textures. "
                               "If %(metavar)s is omitted, defaults to `%(const)s'. Overrides --depth.")
    texture_group.add_argument('--palette-type', type=str.lower, default='adaptive', metavar='TYPE',
                               choices=['web-safe','adaptive'],
                               help="Select palette type. (default: %(default)s)")
    texture_group.add_argument('--palette-depth', type=int, default=8, choices=[1,2,4,8], metavar='DEPTH',
                               help="Select palette bit-depth. (default: %(default)s)")
    texture_group.add_argument('--dither', type=str.lower, nargs='?', const='void-cluster', metavar='TYPE',
                               choices=['random','halftone','bayer','void-cluster','diffusion'],
                               help="Select dithering method for indexed textures. "
                               "If %(metavar)s is omitted, defaults to `%(const)s'.")

    ########################################################################

    data_group = parser.add_argument_group('data options')
    data_group.add_argument('--format', type=str.lower, default='png',
                            help="Select default output texture format.")
    data_group.add_argument('--index', default='default',
                            help="Select output sprite index format.")
    data_group.add_argument('--encrypt', type=str.lower, metavar='TYPE',
                            choices=['xor','aes-ecb','aes-cbc'],
                            help="Select algorithm used to encrypt output textures.")
    data_group.add_argument('--key', metavar='KEY',
                            help="Provide encryption key directly.")
    data_group.add_argument('--key-hash', type=str.lower, metavar='HASH',
                            choices=['MD5','SHA-1','SHA-128','SHA-256','SHA-512','SHA-1024'],
                            help="Select hash algorithm for value of --key.")
    data_group.add_argument('--key-file', metavar='FILE',
                            help="Provide encryption key from %(metavar)s. Overrides --key.")

    ########################################################################

    args = parser.parse_args()

    ########################################################################
    ## Phase 1 - Load and process individual sprites

    with Timer('load sprites'):
        sprites = load_sprites(args.sprites)

    if not sprites:
        parser.error('No sprites found.')

    if args.mask:
        ## Mask sprites against background color
        sprites = mask_sprites(sprites, args.mask)

    if args.trim:
        ## Trim sprites to visible area
        sprites = trim_sprites(sprites)
    else:
        ## Generate hashes of trimmed sprites
        sprites = hash_sprites(sprites)

    if args.alias:
        ## Find and remove duplicate sprites
        sprites = alias_sprites(sprites)

    if args.extrude:
        ## Extrude sprite edges to avoid color bleed
        sprites = extrude_sprites(sprites, args.extrude)

    if args.pad:
        ## Insert transparent padding between sprites
        sprites = pad_sprites(sprites, args.pad)

    ########################################################################
    ## Phase 2 - Arrange sprites in sheets

    sheets = []

    layout = layouts.get_layout(args.layout)

    oldlen = 0

    with Timer('generate sheet layouts'):
        while sprites and len(sprites) != oldlen:
            oldlen = len(sprites)

            sheet = layouts.Sheet(
                min_size = args.min_size,
                max_size = args.max_size,
                rotate = args.rotate,
                npot = args.npot,
                square = args.square,
                layout = layout
            )

            sprites = sheet.add(sprites)

            if sheet.sprites:
                sheets.append(sheet)

    if sprites:
        print "Could not place:"
        for spr in sprites:
            print '\t', spr.name

    ########################################################################
    ## Phase 3 - Scale, quantize, and compress textures

    if args.scale:
        ## do main process twice:
        ##   first with filename suffix '@2x',
        ##   then with sheets at half scale
        pass

    if args.compress:
        ## ignore most of the other options and generate compressed textures
        pass

    numsheets = len(sheets)

    if numsheets > 0:
        digits = int(math.floor(math.log10(numsheets))+1)

        print numsheets, 'sheet(s):'

        path = os.path.dirname(args.prefix)
        if path and not os.path.isdir(path):
            os.makedirs(path)

    else:
        digits = 0

    with Timer('save sheets'):
        for i, sheet in enumerate(sheets):
            if not sheet.sprites:
                continue

            texture = Image.new('RGBA', sheet.size) # args.color_depth

            for sprite in sheet.sprites:
                texture.paste(sprite.image, (sprite.rect.x, sprite.rect.y), sprite.image)

            if args.debug:
                draw = ImageDraw.Draw(texture)
                fill = None
                line = args.debug

                for sprite in sheet.sprites:
                    rect = sprite.rect
                    x0, y0, x1, y1 = rect.x, rect.y, rect.w, rect.h
                    x1, y1 = x1 + x0, y1 + y0
                    draw.rectangle((x0, y0, x1, y1), fill, line)

            texture = quantize_texture(texture, args.quantize, args.palette_type, args.palette_depth, args.dither)

    ########################################################################
    ## Phase 4 - Output texture data; create index

            outname = '%s%0*d' % (args.prefix, digits, i)
            texname = outname + '.' + args.format
            idxname = outname + '.' + 'idx'

            print '\t', texname, '(%dx%d, %d sprites)' % (
                sheet.size[0], sheet.size[1], len(sheet.sprites))

            texture.save(texname)

            if args.encrypt:
                encrypt_data(texname, args.encrypt, args.key, args.key_hash, args.key_file)
                encrypt_data(idxname, args.encrypt, args.key, args.key_hash, args.key_file)

################################################################################

if __name__ == '__main__':
    main()

################################################################################
## EOF
################################################################################

