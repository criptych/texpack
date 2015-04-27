# -*- encoding: utf-8 -*-
################################################################################
## TexPack layout engine
##
## Implements selected versions of the Shelf, MaxRects, and Skyline algorithms
## detailed in the paper "A Thousand Ways to Pack the Bin" by Jukka Jylänki[1],
## as well as a transpose variant of Shelf here called "Stack".
##
## [1] http://clb.demon.fi/files/RectangleBinPack.pdf
################################################################################

__all__ = ['get_layout']

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

class Sprite(object):
    def __init__(self, filename, *args, **kwargs):
        self.image = Image.open(filename).convert('RGBA')
        self.pixels = self.image.load()
        self.filename = filename
        self.name = os.path.basename(filename)
        self.rotated = False

    def rotate(self):
        if self.rotated:
            self.image = self.image.transpose(Image.ROTATE_270)
        else:
            self.image = self.image.transpose(Image.ROTATE_90)
        self.rect.width, self.rect.height = self.rect.height, self.rect.width
        self.rotated = not self.rotated

    @property
    def rect(self):
        rect = vars(self).setdefault('_rect', Rect())
        rect.width, rect.height = self.image.size
        return rect

class Sheet(object):
    def __init__(
        self,
        layout=None,
        min_size=None,
        max_size=None,
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
            layout = self.layout_type(self)
            for spr in sprites:
                if layout.add(spr):
                    placed.append(spr)
                else:
                    remain.append(spr)

        return placed, remain

    def add(self, sprites):
        temp = self.sprites + sprites

        placed, remain = self.do_layout(temp)

        while remain:
            print "\tcouldn't add all sprites, try growing"

            if self.grow():
                print "\tgrowing to %dx%d" % (self.size)
            else:
                print "\tcan't grow any bigger"
                break

            placed, remain = self.do_layout(temp)

        self.sprites = placed

        return remain

    def prepare(self, debug=None):
        texture = Image.new('RGBA', self.size) # args.color_depth

        for sprite in self.sprites:
            texture.paste(sprite.image, (sprite.rect.x, sprite.rect.y), sprite.image)

        if debug:
            draw = ImageDraw.Draw(texture)
            fill = None
            line = debug

            for sprite in self.sprites:
                rect = sprite.rect
                x0, y0, x1, y1 = rect.x, rect.y, rect.w, rect.h
                x1, y1 = x1 + x0, y1 + y0
                draw.rectangle((x0, y0, x1, y1), fill, line)

        return texture

################################################################################

class Layout(object):
    """
    Base class for rectangle layout algorithms.
    """

    def __init__(self, sheet):
        self.sheet = sheet
        self.clear()

    def clear(self):
        pass

    def add(self, *sprites):
        raise NotImplementedError('use a subclass of Layout')

################################################################################

class ShelfLayout(Layout):
    """
    A basic layout that arranges rects in order on progressively higher rows or
    "shelves".  When each rect is placed, if it does not fit on the current
    shelf, a new shelf is created at the top of the tallest item.
    """

    class Shelf(object):
        def __init__(self, start=0, size=0):
            self.start = start
            self.size = size
            self.max = 0
            self.rects = []

        def place(self, rect):
            self.rects.append(rect)
            rect.left = self.size
            rect.top = self.start
            self.size += rect.width
            if self.max < rect.height:
                self.max = rect.height
            return rect

    def clear(self):
        self.size = 0
        self.shelves = []

    def add(self, spr):
        rect = spr.rect

        w, h = rect.width, rect.height
        maxw, maxh = self.sheet.size

        if w > maxw or h > maxh:
            return False

        best = None
        shelf = None
        rotated = False

        for sh in self.shelves:
            tw, th = w, h
            if self.sheet.rotate and (tw > th) and (tw <= sh.max):
                tw, th = th, tw
                rotated = not rotated
            if sh.size + tw <= maxw and th <= sh.max:
                score = (maxw - sh.size - tw) * sh.max + tw * (sh.max - th)
                if best is None or score < best:
                    best = score
                    shelf = sh

        if rotated:
            tw, th = w, h
        else:
            tw, th = h, w

        if shelf is None:
            ## No room on existing shelves

            if self.size + th > maxh:
                ## No room for new shelf
                return False

            shelf = self.Shelf(self.size)
            self.shelves.append(shelf)

        if rotated:
            spr.rotate()

        shelf.place(spr.rect)

        self.size = max(self.size, shelf.start + shelf.max)

        return True

################################################################################

class StackLayout(Layout):
    """
    Like ShelfLayout, but arranges rects in columns.
    """

    class Stack(object):
        def __init__(self, start=0, size=0):
            self.start = start
            self.size = size
            self.max = 0
            self.rects = []

        def place(self, rect):
            self.rects.append(rect)
            rect.left = self.start
            rect.top = self.size
            self.size += rect.height
            if self.max < rect.width:
                self.max = rect.width
            return rect

    def clear(self):
        self.size = 0
        self.stacks = []

    def add(self, spr):
        rect = spr.rect

        w, h = rect.width, rect.height
        maxw, maxh = self.sheet.size

        if w > maxw or h > maxh:
            return False

        best = None
        stack = None
        rotated = False

        for st in self.stacks:
            tw, th = w, h
            if self.sheet.rotate and (th > tw) and (th <= st.max):
                tw, th = th, tw
                rotated = not rotated
            if st.size + th <= maxh and tw <= st.max:
                score = (maxh - st.size - th) * st.max + th * (st.max - tw)
                if best is None or score < best:
                    best = score
                    stack = st

        if rotated:
            tw, th = w, h
        else:
            tw, th = h, w

        if stack is None:
            ## No room in existing stacks

            if self.size + tw > maxw:
                ## No room for new stack
                return False

            stack = self.Stack(self.size)
            self.stacks.append(stack)

        if rotated:
            spr.rotate()

        stack.place(spr.rect)

        self.size = max(self.size, stack.start + stack.max)

        return True

################################################################################

class MaxRectsLayout(Layout):
    """
    A layout that arranges rects by subdividing free space into overlapping
    regions.  When each rect is placed, its area is removed from the remaining
    free-space rects.
    """

    def clear(self):
        w, h = self.sheet.size
        self.free_rects = [Rect(w, h)]

    def split(self, rect):
        # for free in self.free_rects:
            # if free.intersects(rect):
                # self.free_rects.remove( free )
                # self.free_rects.append( split1 )
                # self.free_rects.append( split2 )

        # for free1 in self.free_rects:
            # for free2 in self.free_rects:
                # if free1 != free2 and free1.contains(free2):
                    # self.free_rects.remove(free2)

        pass

    def add(self, *rects):
        raise NotImplementedError('MaxRectsLayout is not implemented')

################################################################################

class SkylineLayout(Layout):
    """
    """

    def add(self, *rects):
        raise NotImplementedError('SkylineLayout is not implemented')

################################################################################

LAYOUTS = {
    'shelf': ShelfLayout,
    'stack': StackLayout,
    'max-rects': MaxRectsLayout,
    'skyline': SkylineLayout,
}

def get_layout(name):
    return LAYOUTS.get(name)

################################################################################
## EOF
################################################################################

