import unittest
import cv2
import numpy as np
from auditar_alvos_pupila import inside_fraction,ellipse_geometry

class GeometryAuditTests(unittest.TestCase):
    def test_rotated_nested_ellipses(self):
        self.assertEqual(inside_fraction(((30.,40.),(8.,4.),73.),((30.,40.),(30.,16.),73.)),1.)
    def test_center_inside_does_not_imply_containment(self):
        fraction=inside_fraction(((0.,0.),(16.,16.),0.),((0.,0.),(20.,8.),0.))
        self.assertGreater(fraction,0.);self.assertLess(fraction,1.)
    def test_annotation_hole_fits_inner_contour(self):
        mask=np.zeros((120,160),np.uint8)
        cv2.ellipse(mask,((80.,60.),(100.,80.),20.),1,-1)
        cv2.ellipse(mask,((80.,60.),(40.,20.),20.),0,-1)
        outer,inner=ellipse_geometry(mask)
        self.assertLess(min(inner[1])/max(inner[1]),.6)
        self.assertEqual(inside_fraction(inner,outer),1.)

if __name__=='__main__':unittest.main()
