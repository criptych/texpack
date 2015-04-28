#!/bin/env python
# -*- encoding: utf-8 -*-
################################################################################
## TexPack test suite
################################################################################

import texpack

import unittest

################################################################################

class DirTest(unittest.TestCase):
    def test_dirs(self):
        texpack.main("test/test_dirs_", "test-sprites")

class GlobTest(unittest.TestCase):
    def test_glob_gif(self):
        texpack.main("test/test_glob_gif_", "test-sprites/*.gif")

    def test_glob_jpg(self):
        texpack.main("test/test_glob_jpg_", "test-sprites/*.jpg")

    def test_glob_noth_gif(self):
        texpack.main("test/test_glob_noth_gif_", "test-sprites/[!h]*.gif")

class MaskTest(unittest.TestCase):
    def test_mask_default(self):
        texpack.main("test/test_mask_default_", "test-sprites", "--mask")

    def test_mask_hexcode(self):
        texpack.main("test/test_mask_hexcode_", "test-sprites", "--mask=#fff")

    def test_mask_cssname(self):
        texpack.main("test/test_mask_cssname_", "test-sprites", "--mask=white")

class TrimTest(unittest.TestCase):
    def test_trim(self):
        texpack.main("test/test_trim_", "test-sprites", "--trim")

class AliasTest(unittest.TestCase):
    def test_alias_default(self):
        texpack.main("test/test_alias_default_", "test-sprites", "--alias")

    def test_alias_custom(self):
        texpack.main("test/test_alias_custom_", "test-sprites", "--alias=0.5")

class ExtrudeTest(unittest.TestCase):
    def test_extrude_default(self):
        texpack.main("test/test_extrude_default_", "test-sprites", "--extrude")

    def test_extrude_custom(self):
        texpack.main("test/test_extrude_custom_", "test-sprites", "--extrude=4")

class PadTest(unittest.TestCase):
    def test_pad_default(self):
        texpack.main("test/test_pad_default_", "test-sprites", "--pad")

    def test_pad_custom(self):
        texpack.main("test/test_pad_custom_", "test-sprites", "--pad=4")

class SortTest(unittest.TestCase):
    def test_sort_default(self):
        with self.assertRaises(SystemExit): # "expected argument"
            texpack.main("test/test_sort_default_", "test-sprites", "--sort")

    def test_sort_width(self):
        texpack.main("test/test_sort_width_", "test-sprites", "--sort=width")

    def test_sort_height(self):
        texpack.main("test/test_sort_height_", "test-sprites", "--sort=height")

    def test_sort_area(self):
        texpack.main("test/test_sort_area_", "test-sprites", "--sort=area")

    def test_sort_name(self):
        texpack.main("test/test_sort_name_", "test-sprites", "--sort=name")

class LayoutTest(unittest.TestCase):
    def test_layout_default(self):
        with self.assertRaises(SystemExit): # "expected argument"
            texpack.main("test/test_layout_default_", "test-sprites", "--layout")

    def test_layout_shelf(self):
        texpack.main("test/test_layout_shelf_", "test-sprites", "--layout=shelf")

    def test_layout_stack(self):
        texpack.main("test/test_layout_stack_", "test-sprites", "--layout=stack")

    @unittest.expectedFailure # remove when implemented
    def test_layout_maxrects(self):
        texpack.main("test/test_layout_maxrects_", "test-sprites", "--layout=max-rects")

    @unittest.expectedFailure # remove when implemented
    def test_layout_skyline(self):
        texpack.main("test/test_layout_skyline_", "test-sprites", "--layout=skyline")

class RotateTest(unittest.TestCase):
    def test_rotate(self):
        texpack.main("test/test_rotate_", "test-sprites", "--rotate")

class NpotTest(unittest.TestCase):
    def test_npot(self):
        texpack.main("test/test_npot_", "test-sprites", "--npot")

class SquareTest(unittest.TestCase):
    def test_square(self):
        texpack.main("test/test_square_", "test-sprites", "--square")

class MinSizeTest(unittest.TestCase):
    def test_minsize_default(self):
        with self.assertRaises(SystemExit): # "expected argument"
            texpack.main("test/test_minsize_default_", "test-sprites", "--min-size")

    def test_minsize_custom(self):
        texpack.main("test/test_minsize_custom_", "test-sprites", "--min-size=4096")

class MaxSizeTest(unittest.TestCase):
    def test_maxsize_default(self):
        with self.assertRaises(SystemExit): # "expected argument"
            texpack.main("test/test_maxsize_default_", "test-sprites", "--max-size")

    def test_maxsize_custom(self):
        texpack.main("test/test_maxsize_custom_", "test-sprites", "--max-size=1024")

class ScaleTest(unittest.TestCase):
    def test_scale(self):
        texpack.main("test/test_scale_", "test-sprites", "--scale")

class CompressTest(unittest.TestCase):
    def test_compress(self):
        texpack.main("test/test_compress_", "test-sprites", "--compress")

################################################################################

if __name__ == '__main__':
    import sys
    unittest.main(*sys.argv[1:])

################################################################################
## EOF
################################################################################

