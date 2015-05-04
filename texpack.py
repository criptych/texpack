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
log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

import math
import os

from PIL import Image
from PIL import ImageChops
from PIL import ImageColor

from layouts import get_layout
from spritesheet import Sprite, Sheet

################################################################################

import datetime

def strfdelta(dt, fmt=None):
    dy = dt.days
    ts = dt.seconds

    hr = (ts // 3600)
    mn = (ts //   60) % 60
    sc = (ts        ) % 60

    us = dt.microseconds
    ms = us // 1000

    if fmt is None:
        if dy:
            return '%dd%02d:%02d:%02d.%06d' % (dy, hr, mn, sc, us)
        elif hr:
            return '%d:%02d:%02d.%06d' % (hr, mn, sc, us)
        elif mn:
            return '%d:%02d.%06d' % (mn, sc, us)
        else:
            return '%d.%06ds' % (sc, us)

    return (fmt
        .replace('%d', '%d' % dy)
        .replace('%S', '%d' % ts)
        .replace('%h', '%02d' % hr)
        .replace('%m', '%02d' % mn)
        .replace('%s', '%02d' % sc)
        .replace('%f', '%06d' % us)
        .replace('%F', '%03d' % ms)
    )

class Timer(object):
    def __init__(self, name='Timer', callback=None):
        self.name = name
        self.callback = callback
        self.start = None
        self.finish = None

    def __enter__(self):
        self.start = datetime.datetime.now()
        log.debug("%s: start: %s", self.name, self.start.strftime('%H:%M:%S'))
        return self

    def __exit__(self, *exc_info):
        self.finish = datetime.datetime.now()
        dt = self.finish - self.start
        log.debug("%s: end: %s", self.name, self.finish.strftime('%H:%M:%S'))
        log.debug("%s: duration: %s", self.name, strfdelta(dt))
        if self.callback is not None:
            self.callback(dt)

################################################################################

def load_sprites(filenames):
    from glob import glob

    r = []

    with Timer('load sprites'):
        for fn in filenames:
            for f in glob(fn):
                f = os.path.abspath(f)
                if os.path.isdir(f):
                    for root, _, files in os.walk(f):
                        for ff in files:
                            try:
                                r.append(Sprite(os.path.join(root, ff)))
                            except IOError:
                                ## Not an image file?
                                pass

                else:
                    try:
                        r.append(Sprite(f))
                    except IOError:
                        ## Not an image file?
                        pass

    return r

################################################################################

def _mask_topleft(A,B,C,D):
    return A

def _mask_topright(A,B,C,D):
    return B

def _mask_bottomleft(A,B,C,D):
    return C

def _mask_bottomright(A,B,C,D):
    return D

def _mask_2of4(A,B,C,D):
    if (A == B and C != D) or (A == C and B != D) or (A == D and B != C):
        return A
    if (B == C and A != D) or (B == D and A != C):
        return B
    if (C == D and A != B):
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

    with Timer('mask sprites'):
        for spr in sprites:
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

            outbands = [srcband.point(lambda p, l=level: (p != l) and 255)
                        for srcband, level in zip(spr.image.split(), bg)]
            tband = ImageChops.lighter(
                ImageChops.lighter(outbands[0], outbands[1]),
                outbands[2]).convert('1')
            spr.image.putalpha(tband)

    return sprites

################################################################################

def trim_sprites(sprites):
    with Timer('trim sprites'):
        for spr in sprites:
            box = spr.image.getbbox()
            spr.image = spr.image.crop(box)

    return sprites

################################################################################

def hash_sprites(sprites):
    return sprites

################################################################################

def alias_sprites(sprites, tolerance=0):
    aliased = []

    with Timer('alias sprites'):
        if tolerance > 0:
            def is_alias(spr1, spr2):
                if spr1.image.size != spr2.image.size:
                    return False

                area = spr1.image.size[0] * spr1.image.size[1]
                diff = ImageChops.difference(spr1.image, spr2.image)
                hist = diff.histogram()
                total = sum(v*(i%256)**2 for i,v in enumerate(hist))
                rms = math.sqrt(total/area/65536.0)
                return rms <= tolerance

        else:
            def is_alias(spr1, spr2):
                if spr1.image.size != spr2.image.size:
                    return False
                diff = ImageChops.difference(spr1.image, spr2.image)
                for mn, mx in diff.getextrema():
                    if (mn > 0) or (mx > 0):
                        return False
                return True

        for i, spr1 in enumerate(sprites):
            for j in reversed(range(len(sprites))):
                if j <= i:
                    break
                spr2 = sprites[j]

                if is_alias(spr1, spr2):
                    sprites.pop(j)
                    spr2.alias = spr1
                    aliased.append(spr2)

    return sprites, aliased

################################################################################

def extrude_sprites(sprites, size):
    if size:
        with Timer('extrude sprites'):
            for spr in sprites:
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

################################################################################

def pad_sprites(sprites, size):
    if size:
        with Timer('pad sprites'):
            for spr in sprites:
                w, h = spr.image.size
                image = Image.new(spr.image.mode, (w+size, h+size), (0,0,0,0))
                image.paste(spr.image, (0, 0), spr.image)
                spr.image = image

    return sprites

################################################################################

def sort_sprites(sprites, attr, rotate=False):
    with Timer('sort sprites'):
        def key_width(s):
            return s.width

        def key_height(s):
            return s.height

        def key_area(s):
            return s.width * s.height

        def key_name(s):
            return s.name

        def rotate_width():
            if rotate:
                for spr in sprites:
                    if spr.h > spr.w:
                        spr.rotate()

        def rotate_height():
            if rotate:
                for spr in sprites:
                    if spr.w > spr.h:
                        spr.rotate()

        sorters = {
            'width': (key_width, rotate_width, True),
            'width-desc': (key_width, rotate_width, True),
            'width-asc': (key_width, rotate_width, False),
            'height': (key_height, rotate_height, True),
            'height-desc': (key_height, rotate_height, True),
            'height-asc': (key_height, rotate_height, False),
            'area': (key_area, None, True),
            'area-desc': (key_area, None, True),
            'area-asc': (key_area, None, False),
            'name': (key_name, None, False),
            'name-asc': (key_name, None, False),
            'name-desc': (key_name, None, True),
        }

        key, rotator, reverse = sorters[attr]

        if rotator is not None:
            rotator()

        sprites.sort(key=key, reverse=reverse)

    return sprites

################################################################################

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

    with Timer('quantize texture'):
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

def encrypt_data(filename, method, key=None, key_hash=None, key_file=None):
    pass

################################################################################

def build_arg_parser():
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

    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help="Print more detailed messages.")

    ########################################################################

    sprite_group = parser.add_argument_group('sprite options')
    sprite_group.add_argument('--mask', nargs='?', default=False, const='3of4', metavar='MASK',
                              help="Mask sprites against background (color or detection method). "
                              "If %(metavar)s is omitted, defaults to `%(const)s'.")
    sprite_group.add_argument('--trim', action='store_true', default=False,
                              help="Trim sprites to visible area.")
    sprite_group.add_argument('--alias', type=float, nargs='?', const=0.0, metavar='TOLERANCE',
                              help="Find and remove duplicate sprites. "
                              "If %(metavar)s is omitted, defaults to %(const)s.")
    sprite_group.add_argument('--extrude', type=int, default=0, nargs='?', const=1, metavar='SIZE',
                              help="Extrude sprite edges %(metavar)s pixels to avoid color bleed. "
                              "If %(metavar)s is omitted, defaults to `%(const)s'.")
    sprite_group.add_argument('--pad', type=int, default=0, nargs='?', const=1, metavar='SIZE',
                              help="Insert %(metavar)s pixels of padding between sprites. "
                              "If %(metavar)s is omitted, defaults to `%(const)s'.")
    sprite_group.add_argument('--sort', metavar='ATTR',
                              choices=['width','height','area','name',
                                       'width-asc','height-asc','area-asc','name-asc',
                                       'width-desc','height-desc','area-desc','name-desc',
                                       ],
                              help="Sort sprites by attibute %(metavar)s.")

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
    texture_group.add_argument('--compress', type=str.upper, nargs='?', const='S3TC', metavar='TYPE',
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

    return parser

################################################################################

def load_and_process_sprites(args):

    sprites = load_sprites(args.sprites)

    if not sprites:
        raise ValueError('No sprites found.')

    if args.mask:
        ## Mask sprites against background color
        sprites = mask_sprites(sprites, args.mask)

    if args.trim:
        ## Trim sprites to visible area
        sprites = trim_sprites(sprites)
    else:
        ## Generate hashes of trimmed sprites
        sprites = hash_sprites(sprites)

    if args.alias is not None:
        ## Find and remove duplicate sprites
        sprites, aliased = alias_sprites(sprites, args.alias)

        if aliased:
            sheet = Sheet(npot=True, layout=get_layout('stack'))
            sheet.add(aliased)
            texture = sheet.prepare(args.debug)
            texname = '%salias.png' % args.prefix
            texture.save(texname)

    if args.extrude:
        ## Extrude sprite edges to avoid color bleed
        sprites = extrude_sprites(sprites, args.extrude)

    if args.pad:
        ## Insert transparent padding between sprites
        sprites = pad_sprites(sprites, args.pad)

    if args.sort:
        sprites = sort_sprites(sprites, args.sort, args.rotate)

    return sprites

################################################################################

def build_sprite_sheets(args, sprites):

    sheets = []

    layout = get_layout(args.layout)

    oldlen = 0

    with Timer('generate sheet layouts'):
        while sprites and len(sprites) != oldlen:
            oldlen = len(sprites)

            sheet = Sheet(
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
        log.warn("Could not place:")
        for spr in sprites:
            log.warn("\t%s", spr.name)

    return sheets

################################################################################

def main(*argv):
    parser = build_arg_parser()

    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    ########################################################################
    ## Phase 1 - Load and process individual sprites

    sprites = load_and_process_sprites(args)

    ########################################################################
    ## Phase 2 - Arrange sprites in sheets

    sheets = build_sprite_sheets(args, sprites)

    ########################################################################
    ## Phase 3 - Scale, quantize, and compress textures

    if args.scale:
        ## do main process twice:
        ##   first with filename suffix '@2x',
        ##   then with sheets at half scale
        log.warn("Warning: --scale is not implemented")

    if args.compress:
        ## ignore most of the other options and generate compressed textures
        log.warn("Warning: --compress is not implemented")

    numsheets = len(sheets)

    if numsheets > 0:
        digits = int(math.floor(math.log10(numsheets))+1)

        log.info('%d sheet%s', numsheets, ':' if numsheets == 1 else 's:')

        path = os.path.dirname(args.prefix)
        if path and not os.path.isdir(path):
            os.makedirs(path)

    else:
        log.warning('%d sheets', numsheets)
        digits = 0

    with Timer('save sheets'):
        for i, sheet in enumerate(sheets):
            if not sheet.sprites:
                continue

            texture = sheet.prepare(args.debug)

            texture = quantize_texture(texture, args.quantize, args.palette_type, args.palette_depth, args.dither)

    ########################################################################
    ## Phase 4 - Output texture data; create index

            outname = '%s%0*d' % (args.prefix, digits, i)
            texname = outname + '.' + args.format
            idxname = outname + '.' + 'idx'

            texture.save(texname)

            if args.encrypt:
                encrypt_data(texname, args.encrypt, args.key, args.key_hash, args.key_file)
                encrypt_data(idxname, args.encrypt, args.key, args.key_hash, args.key_file)

            log.info("\t%s (%dx%d, %d sprites, %.1f%% coverage)",
                texname, texture.size[0], texture.size[1], len(sheet.sprites),
                100*sheet.coverage)

            if sheet.coverage > 1.0:
                log.warning('coverage > 1.0, overlapping sprites?')

################################################################################

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])

################################################################################
## EOF
################################################################################

