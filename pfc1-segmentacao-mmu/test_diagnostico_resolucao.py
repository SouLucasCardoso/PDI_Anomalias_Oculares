import unittest
import numpy as np
from diagnosticar_resolucao_geometria import shortside,dice_reference,bin_label


class GeometryDiagnosticTests(unittest.TestCase):
    def test_native_bbox_and_empty_annotations(self):
        a=np.zeros((12,20),bool);a[2:7,3:15]=True
        self.assertEqual(shortside(a),5);self.assertEqual(dice_reference(a,a),1.)
        self.assertIsNone(shortside(np.zeros_like(a)));self.assertIsNone(dice_reference(a,np.zeros_like(a)))
        self.assertEqual(dice_reference(np.zeros_like(a),a),0.)

    def test_bins_partition_boundaries_and_undefined(self):
        edges=[0,64,96,128,float('inf')]
        self.assertEqual(bin_label(64,edges),'[64,96)');self.assertEqual(bin_label(0,edges),'[0,64)')
        self.assertEqual(bin_label(None,edges),'undefined')
        with self.assertRaises(ValueError):bin_label(-1,edges)


if __name__=='__main__':unittest.main()
