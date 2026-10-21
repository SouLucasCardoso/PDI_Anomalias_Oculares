import unittest
from validar_prototipos_escala import partition

class ScalePrototypeTests(unittest.TestCase):
    def test_all_valid_references_retained_in_disjoint_ordered_groups(self):
        result=partition(list(range(8)),[9,1,8,2,7,3,6,4],[True,True,True,False,True,True,True,True])
        flattened=[i for part in result for i in part]
        self.assertEqual(len(result),3);self.assertEqual(len(flattened),len(set(flattened)))
        self.assertEqual(sorted(flattened),[0,1,2,4,5,6,7]);self.assertEqual(flattened,[1,5,7,6,4,2,0])

if __name__=='__main__':unittest.main()
