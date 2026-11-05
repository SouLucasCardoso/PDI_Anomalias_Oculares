import base64,io,json,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from revisar_mascaras_clinicas import decode_mask,save_review


class HumanReviewTests(unittest.TestCase):
    def encoded(self,values):
        stream=io.BytesIO();Image.fromarray(values).save(stream,format='PNG')
        return base64.b64encode(stream.getvalue()).decode()
    def test_wrong_classes_and_wrong_image_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):decode_mask(self.encoded(np.full((8,8),5,np.uint8)),(8,8))
        with self.assertRaises(ValueError):decode_mask(self.encoded(np.zeros((8,8),np.uint8)),(9,8))
    def test_no_reference_without_named_human_and_visible_structure_masks(self):
        task={'id':'test','width':8,'height':8,'image_sha256':'synthetic'}
        values=np.zeros((8,8),np.uint8);values[2:6,2:6]=1;values[3:5,3:5]=2
        body={'png':self.encoded(values),'complete':True,'iris_visible':True,'pupil_visible':True}
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):save_review(Path(temp),task,body)
            result=save_review(Path(temp),task,{**body,'reviewer':'synthetic test reviewer'})
            self.assertEqual(result['status'],'reviewed_initial')
            with Image.open(Path(temp)/result['mask']) as mask:np.testing.assert_array_equal(np.asarray(mask),values)
            saved=json.loads((Path(temp)/'revisoes/test/latest.json').read_text())
            self.assertFalse(saved['reference_created_by_model'])
            self.assertEqual(saved['review_level'],'user_initial')


if __name__=='__main__':unittest.main()
