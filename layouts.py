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

import logging
log = logging.getLogger(__name__)

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

    def get_best(self, sprites):
        raise NotImplementedError('use a subclass of Layout')

    def place(self, sprite, position, rotate=False):
        raise NotImplementedError('use a subclass of Layout')

    def add(self, *sprites):
        placed = []
        remain = list(sprites)

        while remain:
            i, pos, rot = self.get_best(remain)
            if i is not None and self.place(remain[i], pos, rot):
                placed.append(remain.pop(i))
            else:
                break ## No remaining sprites could be placed

        return placed, remain

    def debug_draw(self, image, draw):
        pass

################################################################################

class ShelfLayout(Layout):
    """
    A basic layout that arranges rects in order on progressively higher rows or
    "shelves".  When each rect is placed, if it does not fit on the current
    shelf, a new shelf is created at the top of the tallest item.
    """

    class Slice(object):
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
        self.slices = []

    def should_rotate(self, spr, shelf):
        if shelf:
            return self.sheet.rotate and (spr.w > spr.h) and (spr.w <= shelf.max)
        else:
            return self.sheet.rotate and (spr.h > spr.w)

    def score(self, spr, shelf, max):
        if shelf:
            if shelf.size + spr.w <= max and spr.h <= shelf.max:
                return (max - shelf.size - spr.w) * shelf.max + \
                        spr.w * (shelf.max - spr.h)
        else:
            if self.size + spr.h <= max:
                return (max - spr.w) * spr.h

    def score_rotate(self, spr, shelf, max):
        rotate = self.should_rotate(spr, shelf)
        if rotate: spr.rotate()
        return self.score(spr, shelf, max), rotate

    def get_best(self, sprites):
        maxw, maxh = self.sheet.size

        best = None, None, None
        best_score = None

        for i, spr in enumerate(sprites):
            if spr.w > maxw or spr.h > maxh:
                continue

            best_shelf = None

            for shelf in self.slices:
                score, rotate = self.score_rotate(spr, shelf, maxw)

                if score is not None and (
                    best_shelf is None or score < best_shelf[1]
                ):
                    best_shelf = shelf, score

            if best_shelf is None:
                ## No room on existing shelves

                score, rotate = self.score_rotate(spr, None, maxh)

                if self.slices and score is None:
                    ## No room for new shelf
                    continue

                best_shelf = self.Slice(self.size), score

            if best_score is None or best_shelf[1] < best_score:
                best = i, best_shelf[0], rotate ^ spr.rotated
                best_score = best_shelf[1]

        return best

    def place(self, sprite, shelf, rotate=False):
        if sprite.rotated ^ rotate:
            sprite.rotate()

        shelf.place(sprite)

        self.size = max(self.size, shelf.start + shelf.max)

        if shelf not in self.slices:
            self.slices.append(shelf)

        return True

################################################################################

class StackLayout(ShelfLayout):
    """
    Like ShelfLayout, but arranges rects in columns.
    """

    class Slice(object):
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
        self.slices = []

    def should_rotate(self, spr, shelf):
        if shelf:
            return self.sheet.rotate and (spr.h > spr.w) and (spr.h <= shelf.max)
        else:
            return self.sheet.rotate and (spr.w > spr.h)

    def score(self, spr, shelf, max):
        if shelf:
            if shelf.size + spr.h <= max and spr.w <= shelf.max:
                return (max - shelf.size - spr.h) * shelf.max + \
                        spr.h * (shelf.max - spr.w)
        else:
            if self.size + spr.w <= max:
                return (max - spr.h) * spr.w

################################################################################

from PIL import Image, ImageDraw
import os

if not os.path.isdir('maxdbg'):
    os.makedirs('maxdbg')

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

        self.debug_image_count = 0

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

        return best, bssf, blsf, rotate

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

    def get_best(self, sprites):
        maxw, maxh = self.sheet.size

        best = None, None, None
        best_score = None

        for i, spr in enumerate(sprites):
            ## find position
            pos, bssf, blsf, rotate = self.search(spr)

            if not (pos and self.sheet.check(pos)):
                continue

            if rotate:
                if self.sheet.rotate:
                    spr.rotate()
                else:
                    continue

            if best_score is None or (bssf, blsf) < best_score:
                best = i, pos, spr.rotated
                best_score = bssf, blsf

        return best

    def place(self, sprite, position, rotate=False):
        sprite.x, sprite.y = position.x, position.y

        if not self.sheet.check(sprite):
            return False

        if sprite.rotated ^ rotate:
            sprite.rotate()

        ## split free nodes
        for i, free in reversed(list(enumerate(self.free_rects))):
            if free.intersects(sprite) and self.split(free, sprite):
                self.free_rects.pop(i)

        ## prune free list
        self.free_rects[:] = [
            free2 for free2 in self.free_rects if not any(
                free1 != free2 and free1.contains(free2)
                for free1 in self.free_rects)
            ]

        log.debug('%r', sprite)
        self.used_rects.append(sprite)
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

