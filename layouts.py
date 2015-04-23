################################################################################
## TexPack layout engine
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

    def intersect(self, rect):
        r = Rect()
        r.left   = max(self.left,   rect.left  )
        r.top    = max(self.top,    rect.top   )
        r.right  = min(self.right,  rect.right )
        r.bottom = min(self.bottom, rect.bottom)
        return r

    def union(self, rect):
        return

################################################################################

from PIL import Image
import os

class Sprite(object):
    def __init__(self, filename, *args, **kwargs):
        self.image = Image.open(filename).convert('RGBA')
        self.pixels = self.image.load()
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
        rect = vars(self).get('_rect')
        if rect is None:
            rect = self._rect = Rect(*self.image.size)
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
                get_next_power_of_2(max_size[0]),
                get_next_power_of_2(max_size[1])
                )
            max_size = (
                get_next_power_of_2(max_size[0]),
                get_next_power_of_2(max_size[1])
                )

        self.layout = layout(self)
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
        w = max(1, oldw * 2)
        h = max(1, oldh * 2)
        if maxw > 0: w = min(w, maxw)
        if maxh > 0: h = min(h, maxh)
        if not self.npot:
            w = get_next_power_of_2(w)
            h = get_next_power_of_2(h)
        self.size = w, h
        return w > oldw or h > oldh

    def check(self, rect):
        w, h = self.size
        rw, rh = rect.x + rect.w, rect.y + rect.h
        return rw <= w and rh <= h

    def add(self, sprites):
        remain = []

        if self.layout:
            for s in sprites:
                while not self.check(s.rect):
                    if not self.grow():
                        break
                if self.check(s.rect) and self.layout.add(s):
                    self.sprites.append(s)
                else:
                    remain.append(s)
            return remain
        else:
            return sprites

################################################################################

class Layout(object):
    """
    Base class for rectangle layout algorithms.
    """

    def __init__(self, sheet):
        self.sheet = sheet

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
        def __init__(self, top, height):
            self.top = top
            self.height = height
            self.width = 0
            self.rects = []

        def place(self, rect):
            self.rects.append(rect)
            rect.left = self.width
            rect.top = self.top
            self.width += rect.width
            if self.height < rect.height:
                self.height = rect.height
            return rect

    def __init__(self, *args, **kwargs):
        Layout.__init__(self, *args, **kwargs)
        self.shelves = []

    def add(self, spr):
        rect = spr.rect

        shelf = vars(self).setdefault('shelf')

        if shelf is None:
            shelf = ShelfLayout.Shelf(0, 0)
            self.shelves.append(shelf)

        if self.sheet.rotate and rect.width > rect.height and rect.width <= shelf.height:
            spr.rotate()

        if self.sheet.max_size[0] > 0 and shelf.width + rect.width > self.sheet.max_size[0]:
            shelf = ShelfLayout.Shelf(shelf.top + shelf.height, 0)
            self.shelves.append(shelf)

        self.shelf = shelf

        if self.sheet.max_size[1] > 0 and shelf.top + rect.height > self.sheet.max_size[1]:
            return False

        shelf.place(rect)
        return True

################################################################################

class StackLayout(Layout):
    """
    Like ShelfLayout, but arranges rects in columns.
    """

    class Stack(object):
        def __init__(self, left, width):
            self.left = left
            self.width = width
            self.height = 0
            self.rects = []

        def place(self, rect):
            self.rects.append(rect)
            rect.left = self.left
            rect.top = self.height
            self.height += rect.height
            if self.width < rect.width:
                self.width = rect.width
            return rect

    def __init__(self, *args, **kwargs):
        Layout.__init__(self, *args, **kwargs)
        self.stacks = []

    def add(self, spr):
        rect = spr.rect

        stack = vars(self).setdefault('stack')

        if stack is None:
            stack = StackLayout.Stack(0, 0)
            self.stacks.append(stack)

        if self.sheet.rotate and rect.height > rect.width and rect.height <= stack.width:
            spr.rotate()

        if self.sheet.max_size[1] > 0 and stack.height + rect.height > self.sheet.max_size[1]:
            stack = StackLayout.Stack(stack.left + stack.width, 0)
            self.stacks.append(stack)

        self.stack = stack

        if self.sheet.max_size[0] > 0 and stack.left + rect.width > self.sheet.max_size[0]:
            return False

        stack.place(rect)
        return True

################################################################################

class MaxRectsLayout(Layout):
    """
    A layout that arranges rects by subdividing free space into overlapping
    regions.  When each rect is placed, its area is removed from the remaining
    free-space rects.
    """

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

