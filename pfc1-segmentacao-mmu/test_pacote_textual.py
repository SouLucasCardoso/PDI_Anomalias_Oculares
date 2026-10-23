from pathlib import Path
import base64,hashlib,io,json,tempfile,unittest,zipfile
from restaurar_pacote_textual import restore


class TextPackageTests(unittest.TestCase):
    def build(self,root,member='MODELO.json'):
        source=root/'source';source.mkdir();buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(member,b'{"weights": [0.5, 0.5]}\r\n')
        data=buffer.getvalue();parts=[]
        for i,start in enumerate(range(0,len(data),32)):
            part=data[start:start+32];name=f'parte{i:04d}.b64';(source/name).write_text(base64.b64encode(part).decode(),encoding='ascii')
            parts.append(dict(name=name,sha256=hashlib.sha256(part).hexdigest()))
        (source/'MANIFESTO.json').write_text(json.dumps(dict(parts=parts,zip_bytes=len(data),zip_sha256=hashlib.sha256(data).hexdigest())))
        return source

    def test_roundtrip_exact_bytes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.build(root);result=restore(source,root/'dest')
            self.assertEqual(result['files'],1);self.assertEqual((root/'dest/resultados/MODELO.json').read_bytes(),b'{"weights": [0.5, 0.5]}\r\n')
            with self.assertRaises(ValueError):restore(source,root/'dest')

    def test_corruption_and_unsafe_member_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.build(root,'../escape.txt')
            with self.assertRaises(ValueError):restore(source,root/'dest')
            self.assertFalse((root/'dest/escape.txt').exists())
            (source/'parte0000.b64').write_text(base64.b64encode(b'corrupt').decode())
            with self.assertRaises(ValueError):restore(source,root/'other')


if __name__=='__main__':unittest.main()
