"""Fronteiras HTTP, isolamento e reconhecimento sem decisão automática."""
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import numpy as np
from PIL import Image
from app_celular.motor import COMPONENTS, rank_candidates
from app_celular.servidor import App, Handler, ThreadingHTTPServer


class FakeEngine:
    initialized=True
    engine_id='test-engine'
    provenance={'test_double':True}
    def analyze(self,photo,folder,progress):
        progress('segmentacao','Teste de fila')
        features={c:np.ones((2,2,2) if c=='spatial' else (4,)) for c in COMPONENTS}
        np.savez_compressed(folder/'features.npz',**features)
        return dict(engine_id=self.engine_id,quality={},warnings=[],elapsed_seconds=0)
    def identify(self,query,groups):
        return rank_candidates(query,groups,[[dict(mean=0,std=1)]*8]*2)


class MobileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.app=App(Path(self.temp.name),['192.0.2.2'],0,FakeEngine())
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.app.port=self.server.server_address[1]
        self.server.app=self.app
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.token=''
    def tearDown(self):
        self.app.stopped.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()
    def request(self,path,data=None,extra=None,raw=False):
        conn=http.client.HTTPConnection('127.0.0.1',self.app.port,timeout=5)
        headers={'Authorization':'Bearer '+self.token};headers.update(extra or {})
        body=data if raw else json.dumps(data).encode() if data is not None else None
        conn.request('POST' if data is not None else 'GET',path,body,headers)
        response=conn.getresponse();payload=response.read();status=response.status;conn.close()
        try:return status,json.loads(payload)
        except ValueError:return status,payload
    def pair(self):
        status,data=self.request('/api/pair',{'code':self.app.code})
        self.assertEqual(status,200);self.token=data['token']
    def capture(self,side='R',mode='enroll'):
        image=io.BytesIO();Image.new('RGB',(128,100),(70,90,110)).save(image,'JPEG')
        status,result=self.request('/api/analyze',image.getvalue(),{'X-Eye-Side':side,'X-Mode':mode},raw=True)
        self.assertEqual(status,202)
        for _ in range(50):
            _,job=self.request('/api/jobs/'+result['id'])
            if job['status'] in ('done','error'):break
            time.sleep(.02)
        self.assertEqual(job['status'],'done',job)
        return result['id'],job['result']
    def test_access_controls_and_no_repo_static(self):
        self.assertEqual(self.request('/api/gallery')[0],401)
        self.assertEqual(self.request('/api/status',extra={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('/api/pair',{'code':self.app.code},{'Origin':'https://evil.example'})[0],403)
        self.pair()
        self.assertEqual(self.request('/../../AGENTS.md')[0],404)
        self.assertEqual(self.request('/api/assets/../gallery.sqlite3')[0],400)
        self.assertEqual(self.request('/api/gallery')[1],[])
    def test_independent_gallery_side_review_and_duplicate(self):
        self.pair();capture,_=self.capture()
        self.assertEqual(self.request('/api/enroll',dict(capture=capture,name='A',reviewed=False))[0],400)
        status,person=self.request('/api/enroll',dict(capture=capture,name='<b>A</b>',reviewed=True))
        self.assertEqual(status,200)
        self.assertEqual(self.request('/api/gallery')[1][0]['name'],'<b>A</b>')
        self.app.jobs.pop(capture)
        restored_status,restored=self.request('/api/jobs/'+capture)
        self.assertEqual(restored_status,200)
        self.assertTrue(restored['result']['already_enrolled'])
        self.assertEqual(restored['result']['engine_id'],'test-engine')
        _,duplicate=self.capture(mode='recognize')
        self.assertTrue(duplicate['matching']['duplicate_image'])
        self.assertIsNone(duplicate['matching']['accepted'])
        self.assertEqual(len(self.app.store.groups('L','test-engine')),0)
        self.assertEqual(len(self.app.store.groups('R','other-engine')),0)
        self.assertEqual(self.request('/api/discard',{'capture':capture})[0],400)
        self.assertEqual(self.request('/api/delete-person',person)[0],200)
        self.assertEqual(self.request('/api/gallery')[1],[])
        self.assertFalse(self.app.store.capture_dir(capture).exists())
    def test_corrupt_photo_and_pair_rate_limit(self):
        self.pair()
        self.assertEqual(self.request('/api/analyze',b'not an image',{'X-Eye-Side':'R','X-Mode':'enroll'},raw=True)[0],400)
        for _ in range(10):status,_=self.request('/api/pair',{'code':'wrong'})
        self.assertEqual(status,429)
    def test_small_gallery_retains_information_without_accepting(self):
        query={k:np.array([1.,0.]) if k!='spatial' else np.array([[[1.]],[[0.]]]) for k in COMPONENTS}
        other={k:-v for k,v in query.items()}
        groups=[dict(person_id='a',name='A',side='R',features=[query]),dict(person_id='b',name='B',side='R',features=[other])]
        calibration=[[dict(mean=0.,std=1.)]*8]*2
        result=rank_candidates(query,groups,calibration)
        self.assertEqual(result['ranking'][0]['person_id'],'a')
        self.assertGreater(result['margin'],1.)
        self.assertIsNone(result['accepted']);self.assertFalse(result['benchmark_threshold_transferred'])
        single=rank_candidates(query,groups[:1],calibration)
        self.assertEqual(single['candidate_count'],1);self.assertIsNone(single['margin'])


if __name__=='__main__':unittest.main()
