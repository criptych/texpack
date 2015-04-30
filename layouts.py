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

from spritesheet import Rect

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

    def add(self, spr):
        raise NotImplementedError('use a subclass of Layout')

    def debug_draw(self, image, draw):
        pass

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
        maxw, maxh = self.sheet.size

        if spr.w > maxw or spr.h > maxh:
            return False

        best = None
        shelf = None

        for sh in self.shelves:
            if self.sheet.rotate and (spr.w > spr.h) and (spr.w <= sh.max):
                tw, th = spr.h, spr.w
                rotated = True
            else:
                tw, th = spr.w, spr.h
                rotated = False

            if sh.size + tw <= maxw and th <= sh.max:
                score = (maxw - sh.size - tw) * sh.max + tw * (sh.max - th)
                if best is None or score < best:
                    best = score
                    shelf = sh

        if shelf is None:
            ## No room on existing shelves

            rotated = False

            if self.shelves and self.size + spr.h > maxh:
                ## No room for new shelf
                return False

            shelf = self.Shelf(self.size)
            self.shelves.append(shelf)

        if rotated:
            spr.rotate()

        shelf.place(spr)

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
        w, h = spr.width, spr.height
        maxw, maxh = self.sheet.size

        if w > maxw or h > maxh:
            return False

        best = None
        stack = None

        for st in self.stacks:
            if self.sheet.rotate and (h > w) and (h <= sh.max):
                tw, th = h, w
                rotated = True
            else:
                tw, th = w, h
                rotated = False
            if st.size + th <= maxh and tw <= st.max:
                score = (maxh - st.size - th) * st.max + th * (st.max - tw)
                if best is None or score < best:
                    best = score
                    stack = st

        if stack is None:
            ## No room in existing stacks

            rotated = False

            if self.stacks and self.size + tw > maxw:
                ## No room for new stack
                return False

            stack = self.Stack(self.size)
            self.stacks.append(stack)

        if rotated:
            spr.rotate()

        stack.place(spr)

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
        self.used_rects = []
        self.free_rects = [Rect(w, h)]

    def search(self, rect):
        bssf, blsf = None, None
        rotate = False
        best = None

        for free in self.free_rects:
            if free.w >= rect.w and free.h >= rect.h:
                dx, dy = free.w - rect.w, free.h - rect.h
                ssf, lsf = min(dx, dy), max(dx, dy)

                if best is None or ssf < bssf or (ssf == bssf and lsf < blsf):
                    best = Rect(rect.w, rect.h, free.x, free.y)
                    bssf, blsf = ssf, lsf

            if self.sheet.rotate and free.h >= rect.w and free.w >= rect.h:
                dx, dy = free.w - rect.h, free.h - rect.w
                ssf, lsf = min(dx, dy), max(dx, dy)

                if best is None or ssf < bssf or (ssf == bssf and lsf < blsf):
                    best = Rect(rect.h, rect.w, free.x, free.y)
                    bssf, blsf = ssf, lsf
                    rotate = True

        return best, rotate

    def split(self, free, rect):
        if (rect.x >= free.x + free.w or rect.x + rect.w <= free.x or
            rect.y >= free.y + free.h or rect.y + rect.h <= free.y):
            return False;

        if (rect.x < free.x + free.w and rect.x + rect.w > free.x):
            ## New node at the top side of the used node.
            if (rect.y > free.y and rect.y < free.y + free.h):
                new = free.copy();
                new.h = rect.y - new.y;
                self.free_rects.append(new);

            ## New node at the bottom side of the used node.
            if (rect.y + rect.h < free.y + free.h):
                new = free.copy();
                new.y = rect.y + rect.h;
                new.h = free.y + free.h - (rect.y + rect.h);
                self.free_rects.append(new);

        if (rect.y < free.y + free.h and rect.y + rect.h > free.y):
            ## New node at the left side of the used node.
            if (rect.x > free.x and rect.x < free.x + free.w):
                new = free.copy();
                new.w = rect.x - new.x;
                self.free_rects.append(new);

            ## New node at the right side of the used node.
            if (rect.x + rect.w < free.x + free.w):
                new = free.copy();
                new.x = rect.x + rect.w;
                new.w = free.x + free.w - (rect.x + rect.w);
                self.free_rects.append(new);

        return True


    def add(self, spr):
        # raise NotImplementedError('MaxRectsLayout is not implemented')

        ## find position

        ## split free nodes
        for free in self.free_rects:
            if free.intersects(spr):
                if self.split(free, spr):
                    self.free_rects.remove( free )

        ## prune free list
        for free1 in self.free_rects:
            for free2 in self.free_rects:
                if free1 != free2 and free1.contains(free2):
                    self.free_rects.remove(free2)

        self.used_rects.append(spr)
        return True

    def debug_draw(self, image, draw):
        for r in self.free_rects:
            x0, y0, x1, y1 = r.left, r.top, r.right, r.bottom
            draw.rectangle((x0, y0, x1, y1), None, '#0000ff')

################################################################################

class SkylineLayout(Layout):
    """
    """

    def add(self, spr):
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

