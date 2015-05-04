# -*- encoding: utf-8 -*-
################################################################################
## TexPack Sprite and Sheet classes
################################################################################

__all__ = ['Rect', 'Sprite', 'Sheet']

import logging
log = logging.getLogger(__name__)

################################################################################

def get_next_power_of_2(n):
    n = int(n) & 0x7fffffffffffffff
    n -= 1
    n |= n >> 32
    n |= n >> 16
    n |= n >>  8
    n |= n >>  4
    n |= n >>  2
    n |= n >>  1
    n += 1
    return n

################################################################################

class Rect(object):
    def __init__(self, w=0, h=0, x=0, y=0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __repr__(self):
        return 'Rect<x=%s,y=%s,w=%s,h=%s>' % (self.x, self.y, self.w, self.h)

    @property
    def left(self):
        return self.x
    @left.setter
    def left(self, value):
        self.x = value

    @property
    def top(self):
        return self.y
    @top.setter
    def top(self, value):
        self.y = value

    @property
    def right(self):
        return self.x + self.w
    @right.setter
    def right(self, value):
        self.w = max(0, value - self.x)

    @property
    def bottom(self):
        return self.y + self.h
    @bottom.setter
    def bottom(self, value):
        self.h = max(0, value - self.y)

    @property
    def width(self):
        return self.w
    @width.setter
    def width(self, value):
        self.w = max(0, value)

    @property
    def height(self):
        return self.h
    @height.setter
    def height(self, value):
        self.h = max(0, value)

    @property
    def empty(self):
        return self.w <= 0 and self.h <= 0

    def copy(self):
        return Rect(self.w, self.h, self.x, self.y)

    def intersects(self, rect):
        return self.x + self.w > rect.x and self.x < rect.x + rect.w and \
               self.y + self.h > rect.y and self.y < rect.y + rect.h

    def contains(self, rect):
        return rect.x >= self.x and rect.x + rect.w <= self.x + self.w and \
               rect.y >= self.y and rect.y + rect.h <= self.y + self.h

    def intersect(self, rect):
        r = Rect()
        r.left   = max(self.left,   rect.left  )
        r.top    = max(self.top,    rect.top   )
        r.right  = min(self.right,  rect.right )
        r.bottom = min(self.bottom, rect.bottom)
        return r

    def union(self, rect):
        r = Rect()
        r.left   = min(self.left,   rect.left  )
        r.top    = min(self.top,    rect.top   )
        r.right  = max(self.right,  rect.right )
        r.bottom = max(self.bottom, rect.bottom)
        return r

################################################################################

from PIL import Image
from PIL import ImageDraw
import os

class Sprite(Rect):
    def __init__(self, image, *args, **kwargs):
        if str(image) == image:
            self.filename = image
            kwargs.setdefault('name', os.path.basename(image))
            image = Image.open(image).convert('RGBA')

        self.name = kwargs.get('name')
        self.image = image
        self.pixels = image.load() if image else None
        self.rotated = False
        self.x, self.y = 0, 0

    @property
    def image(self):
        if self.rotated:
            try:
                return self._rimage
            except AttributeError:
                self._rimage = self._image.transpose(Image.ROTATE_90)
                return self._rimage
        else:
            return self._image

    @image.setter
    def image(self, value):
        self._image = value
        self._rimage = None
        self.w, self.h = value.size
        self.rotated = False

    def rotate(self):
        self.rotated = not self.rotated
        self.w, self.h = self.h, self.w

class Sheet(object):
    def __init__(
        self,
        layout=None,
        min_size=0,
        max_size=0,
        rotate=False,
        npot=False,
        square=False,
    ):
        try:
            min_size = int(min_size)
            min_size = min_size, min_size
        finally:
            pass

        try:
            max_size = int(max_size)
            max_size = max_size, max_size
        finally:
            pass

        if not npot:
            min_size = (
                get_next_power_of_2(min_size[0]),
                get_next_power_of_2(min_size[1])
                )
            max_size = (
                get_next_power_of_2(max_size[0]),
                get_next_power_of_2(max_size[1])
                )

        self.layout_type = layout
        self.min_size = min_size
        self.max_size = max_size
        self.rotate = rotate
        self.npot = npot
        self.square = square

        self.clear()

    def clear(self):
        self.sprites = []
        self.size = self.min_size

    def grow(self):
        maxw, maxh = self.max_size
        oldw, oldh = self.size

        w = oldw * 2
        h = oldh * 2

        if maxw > 0 and w > maxw:
            w = maxw
        elif w < 1:
            w = 1
        if maxh > 0 and h > maxh:
            h = maxh
        elif h < 1:
            h = 1

        if not self.npot:
            w = get_next_power_of_2(w)
            h = get_next_power_of_2(h)

        self.size = w, h
        return w > oldw or h > oldh

    def checkw(self, rect):
        w, h = self.size
        rw = rect.x + rect.w
        return rw <= w

    def checkh(self, rect):
        w, h = self.size
        rh = rect.y + rect.h
        return rh <= h

    def check(self, rect):
        return self.checkw(rect) and self.checkh(rect)

    def do_layout(self, sprites=None):
        placed = []
        remain = []

        if self.layout_type:
            if sprites is None:
                sprites = self.sprites
            self.layout = self.layout_type(self)
            placed, remain = self.layout.add(*sprites)

        return placed, remain

    def add(self, sprites):
        temp = self.sprites + sprites

        placed, remain = self.do_layout(temp)

        while remain:
            if not self.grow():
                break

            placed, remain = self.do_layout(temp)

        self.sprites = placed

        return remain

    def prepare(self, debug=None):
        texture = Image.new('RGBA', self.size) # args.color_depth

        for spr in self.sprites:
            texture.paste(spr.image, (spr.x, spr.y), spr.image)

        if debug:
            draw = ImageDraw.Draw(texture)
            color = debug

            for spr in self.sprites:
                x0, y0, x1, y1 = spr.left, spr.top, spr.right, spr.bottom
                draw.rectangle((x0, y0, x1, y1), None, color)
                draw.text((x0+2, y0+2), spr.name, color)
                if hasattr(spr, 'alias'):
                    y0 += draw.textsize(spr.alias.name)[1]
                    draw.text((x0+2, y0+2), spr.alias.name, color)

            self.layout.debug_draw(texture, draw)

        return texture

    @property
    def coverage(self):
        area = self.size[0] * self.size[1]
        used = 0
        for spr in self.sprites:
            used += spr.w * spr.h
        return float(used) / float(area)

################################################################################
## EOF
################################################################################

