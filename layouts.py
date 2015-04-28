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
        w, h = spr.width, spr.height
        maxw, maxh = self.sheet.size

        if w > maxw or h > maxh:
            return False

        best = None
        shelf = None

        for sh in self.shelves:
            if self.sheet.rotate and (w > h) and (w <= sh.max):
                tw, th = h, w
                rotated = True
            else:
                tw, th = w, h
                rotated = False
            if sh.size + tw <= maxw and th <= sh.max:
                score = (maxw - sh.size - tw) * sh.max + tw * (sh.max - th)
                if best is None or score < best:
                    best = score
                    shelf = sh

        if shelf is None:
            ## No room on existing shelves

            rotated = False

            if self.shelves and self.size + h > maxh:
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

    def add(self, spr):
        raise NotImplementedError('MaxRectsLayout is not implemented')

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

