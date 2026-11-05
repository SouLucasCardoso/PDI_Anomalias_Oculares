"""Primeira revisao humana de mascaras clinicas; servidor somente em127.0.0.1."""
from __future__ import annotations
import argparse
import base64
from datetime import datetime,timezone
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import io
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit
import uuid

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parent
DEFAULT=ROOT/'outputs/revisao_clinica_2026-11-03'
ALLOWED={0,1,2,3,255}
LOCK=threading.Lock()


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,value):
    temporary=path.with_suffix('.json.part')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');temporary.replace(path)


def prepare(out):
    out.mkdir(parents=True,exist_ok=True)
    if (out/'manifesto.json').exists():return json.loads((out/'manifesto.json').read_text(encoding='utf-8'))
    source=ROOT/'data/slpvld/manifesto.json'
    rows=[r for r in json.loads(source.read_text(encoding='utf-8-sig')) if r['source_split']=='development']
    anomalies=sorted([r for r in rows if 'iris' in r['diagnosis_raw'].lower()],key=lambda r:r['image'])
    excluded={r['subject'] for r in anomalies}
    normal=[r for r in rows if r['diagnosis_raw'].strip().lower()=='normal eye' and r['subject'] not in excluded]
    fixed=('P0005_OD20241206.JPG','P0007_OS20250306.JPG')
    chosen=[next(r for r in normal if Path(r['image']).name==n) for n in fixed]
    people=sorted({r['subject'] for r in normal}-{r['subject'] for r in chosen})
    rng=np.random.default_rng(20261103)
    for person in rng.choice(people,30-len(chosen),replace=False):
        candidates=sorted([r for r in normal if r['subject']==person],key=lambda r:r['image'])
        chosen.append(candidates[int(rng.integers(len(candidates)))])
    tasks=[]
    for group,selected in (('normal',chosen),('iris_anomaly',anomalies)):
        for row in selected:
            file=Path(row['image'])
            if sha(file)!=row['sha256']:raise ValueError('Fotografia alterada: '+file.name)
            with Image.open(file) as photo:width,height=photo.size
            tasks.append({'id':file.stem,'image':str(file),'image_sha256':row['sha256'],
                          'subject':row['subject'],'side':row['side'],'group':group,
                          'diagnosis_raw_metadata_only':row['diagnosis_raw'],'width':width,'height':height})
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'source_manifest_sha256':sha(source),
              'selection':'Seed20261103,30normalimages/30people incl2previousfixedcontrols; ALLdevelopment iris-diagnosis images, no visual/score filtering, external split excluded',
              'schema':{'0':'background','1':'visible_iris','2':'pupil','3':'occluder','255':'uncertain'},
              'review_level':'user_initial; not expert-confirmed clinical ground truth',
              'model_predictions_are_reference':False,'tasks':tasks}
    write_json(out/'manifesto.json',manifest)
    return manifest


def decode_mask(encoded,size):
    raw=base64.b64decode(encoded.split(',')[-1],validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        if image.format!='PNG' or image.size!=size:raise ValueError('PNG deve ter exatamente o tamanho da fotografia')
        values=np.asarray(image)
        if values.ndim==3:
            if values.shape[2] not in (3,4) or not np.array_equal(values[:,:,0],values[:,:,1]) or not np.array_equal(values[:,:,0],values[:,:,2]):
                raise ValueError('PNG deve codificar indices de classe, nao cores da fotografia')
            if values.shape[2]==4 and not (values[:,:,3]==255).all():raise ValueError('Mascara deve ser opaca')
            values=values[:,:,0]
        if values.ndim!=2 or not set(np.unique(values)).issubset(ALLOWED):raise ValueError('Classes permitidas:0,1,2,3,255')
        return values.astype(np.uint8)


def save_review(out,task,body):
    reviewer=str(body.get('reviewer','')).strip()[:128]
    complete=body.get('complete') is True
    iris_visible=body.get('iris_visible') is True
    pupil_visible=body.get('pupil_visible') is True
    values=decode_mask(body['png'],(task['width'],task['height']))
    if complete:
        if not reviewer:raise ValueError('Informe quem fez a primeira revisao')
        if iris_visible!=bool((values==1).any()):raise ValueError('Confira a opcao iris visivel e a classe iris')
        if pupil_visible!=bool((values==2).any()):raise ValueError('Confira a opcao pupila visivel e a classe pupila')
    folder=out/'revisoes'/task['id'];folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_'+uuid.uuid4().hex[:6]
    mask_file=folder/(stamp+'.png')
    image=Image.fromarray(values).convert('P')
    palette=[0]*768
    for label,color in {0:(0,0,0),1:(0,230,0),2:(0,140,255),3:(255,60,60),255:(255,210,0)}.items():
        palette[3*label:3*label+3]=color
    image.putpalette(palette);image.save(mask_file)
    metadata={'case_id':task['id'],'status':'reviewed_initial' if complete else 'draft',
              'review_level':'user_initial','reviewer':reviewer,'saved_utc':datetime.now(timezone.utc).isoformat(),
              'image_sha256':task['image_sha256'],'mask':str(mask_file.relative_to(out)),
              'mask_sha256':sha(mask_file),'iris_visible':iris_visible,'pupil_visible':pupil_visible,
              'class_counts':{str(v):int((values==v).sum()) for v in sorted(ALLOWED)},
              'reference_created_by_model':False,'annotation_tool_sha256':sha(Path(__file__))}
    write_json(folder/(stamp+'.json'),metadata);write_json(folder/'latest.json',metadata)
    return metadata


def handler(out,manifest,port):
    tasks={r['id']:r for r in manifest['tasks']}
    class Handler(BaseHTTPRequestHandler):
        def respond(self,value,status=200,content_type='application/json'):
            payload=json.dumps(value,ensure_ascii=False).encode() if content_type=='application/json' else value
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/':return self.respond((ROOT/'revisao_clinica.html').read_bytes(),content_type='text/html; charset=utf-8')
            if path=='/api/tasks':
                public=[]
                for task in tasks.values():
                    latest=out/'revisoes'/task['id']/'latest.json'
                    review=json.loads(latest.read_text(encoding='utf-8')) if latest.exists() else None
                    public.append({k:task[k] for k in ('id','subject','side','width','height')}|{'review':review})
                return self.respond({'application':'pfc-iris-human-review','tasks':public})
            pieces=path.strip('/').split('/')
            if len(pieces)==2 and pieces[1] in tasks:
                task=tasks[pieces[1]]
                if pieces[0]=='image':
                    file=Path(task['image'])
                    if sha(file)!=task['image_sha256']:return self.respond({'error':'Fotografia mudou desde a preparacao'},409)
                    return self.respond(file.read_bytes(),content_type='image/jpeg')
                if pieces[0]=='mask':
                    latest=out/'revisoes'/task['id']/'latest.json'
                    if latest.exists():
                        review=json.loads(latest.read_text(encoding='utf-8'))
                        with Image.open(out/review['mask']) as image:
                            values=np.asarray(image).astype(np.uint8)
                        buf=io.BytesIO();Image.fromarray(values).save(buf,format='PNG')
                        return self.respond(buf.getvalue(),content_type='image/png')
            self.respond({'error':'Nao encontrado'},404)
        def do_POST(self):
            if self.path!='/api/save':return self.respond({'error':'Nao encontrado'},404)
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://127.0.0.1:{port}':return self.respond({'error':'Origem nao permitida'},403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.respond({'error':'Usar JSON'},415)
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=32*1024**2:return self.respond({'error':'Tamanho invalido'},413)
            try:
                body=json.loads(self.rfile.read(length));task=tasks[body['case_id']]
                with LOCK:review=save_review(out,task,body)
                return self.respond(review)
            except (ValueError,KeyError,TypeError) as error:return self.respond({'error':str(error)},400)
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=DEFAULT)
    p.add_argument('--prepare',action='store_true');p.add_argument('--port',type=int,default=8766)
    a=p.parse_args();manifest=prepare(a.out)
    if a.prepare:
        print(json.dumps({'cases':len(manifest['tasks']),'normal':sum(t['group']=='normal' for t in manifest['tasks']),
                          'anomaly_images':sum(t['group']=='iris_anomaly' for t in manifest['tasks'])}));return
    from contextlib import redirect_stdout,redirect_stderr
    with (a.out/'servidor.log').open('a',encoding='utf-8',buffering=1) as log,redirect_stdout(log),redirect_stderr(log):
        print('Human annotation server, loopback only',flush=True)
        ThreadingHTTPServer(('127.0.0.1',a.port),handler(a.out,manifest,a.port)).serve_forever()


if __name__=='__main__':main()
