#!/bin/env python
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
    return [layouts.Sprite(f) for fn in filenames for f in glob(fn)]

def mask_sprites(sprites, color):
    for i, spr in enumerate(sprites):
        w, h = spr.image.size

        try:
            ## If color is a tuple, use it directly
            color[0]
            bg = color
        except TypeError:
            ## Determine background color from corners
            A = spr.image.getpixel((0,  0  ))
            B = spr.image.getpixel((w-1,0  ))
            C = spr.image.getpixel((0,  h-1))
            D = spr.image.getpixel((w-1,h-1))

            ## TODO: there must be a less ugly way to do this
            AB = A == B
            AC = A == C
            AD = A == D
            BC = B == C
            BD = B == D
            CD = C == D

            if AB and (BC or BD):
                bg = A
            elif (AC or BC) and CD:
                bg = D
            else:
                ## no matches, skip it
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
        palette = []
    else:
        palette = []

    return texture.quantize(colors=colors, method=method, palette=palette)

################################################################################

def main():
    import argparse

    parser = argparse.ArgumentParser(usage='%(prog)s prefix sprites... [options]')

    parser.add_argument('prefix',
                        help="Prefix for output sheet textures")
    parser.add_argument('sprites', nargs='+',
                        help="Sprite images / folders / wildcards")

    parser.add_argument('--debug', action='store_true', default=False,
                        help="Save textures with debug markup.")

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
    sprite_group.add_argument('--mask', type=ImageColor.getrgb, nargs='?',
                              default=False, const=True, metavar='COLOR',
                              help="Mask sprites against background color. "
                              "If %(metavar)s is omitted, detects background color automatically.")

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

    sprites.sort(key=lambda s: s.rect.w * s.rect.h, reverse=True)

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
        if path: os.makedirs(path)

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
                line = ImageColor.getrgb('lime')

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

            print '\t', texname

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

