"""Servidor LAN privado. Execute pelo launcher; nenhum serviço de nuvem."""
from __future__ import annotations
import argparse
import collections
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import ipaddress
import json
import logging
from pathlib import Path
import queue
import secrets
import socket
import sys
import threading
import time
import traceback
from urllib.parse import urlsplit

APP_ROOT = Path(__file__).resolve().parents[1]
ROOT = APP_ROOT.parent / 'pfc1-segmentacao-mmu'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(APP_ROOT / '.runtime/iris_mobile_deps'))
from PIL import Image, ImageOps
from app_celular.store import Store, uid
from app_celular.motor import IrisEngine

Image.MAX_IMAGE_PIXELS = 32_000_000
MAX_BODY = 16 * 1024 * 1024


class App:
    def __init__(self, data, addresses, port, engine=None):
        self.store = Store(data)
        self.engine = engine or IrisEngine()
        self.addresses = list(dict.fromkeys(['127.0.0.1', 'localhost'] + addresses))
        self.port = port
        self.code = f'{secrets.randbelow(100000000):08}'
        self.jobs = {}
        self.lock = threading.RLock()
        self.mutations = threading.RLock()
        self.queue = queue.Queue(maxsize=4)
        self.attempts = collections.defaultdict(list)
        self.stopped = threading.Event()
        threading.Thread(target=self.worker, daemon=True).start()

    def update(self, key, **data):
        with self.lock:
            self.jobs[key].update(data)

    def worker(self):
        while not self.stopped.is_set():
            try:
                item = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            key, digest, side, mode = item
            folder = self.store.capture_dir(key)
            try:
                self.update(key, status='running')
                result = self.engine.analyze(folder / 'input.jpg', folder,
                    lambda stage, message: self.update(key, stage=stage, message=message))
                result.update(id=key, side=side, mode=mode)
                with self.mutations:
                    if mode == 'recognize':
                        duplicate = self.store.duplicate(digest)
                        groups = [] if duplicate else self.store.groups(side, result['engine_id'])
                        import numpy as np
                        with np.load(folder / 'features.npz', allow_pickle=False) as arrays:
                            query_features = {k: arrays[k] for k in arrays.files}
                        result['matching'] = self.engine.identify(query_features, groups)
                        result['matching']['duplicate_image'] = duplicate
                    self.store.save_capture(key, digest, side, result)
                (self.store.root / 'motor_proveniencia.json').write_text(json.dumps(self.engine.provenance, indent=2), encoding='utf-8')
                self.update(key, status='done', stage='concluido', message='Análise concluída', result=result)
                logging.info('Captura %s concluida em %ss', key, result['elapsed_seconds'])
            except Exception as error:
                logging.exception('Falha na captura %s', key)
                message = str(error) if isinstance(error, ValueError) else 'O processamento falhou no PC. Consulte execucao.log e tente novamente.'
                self.update(key, status='error', message=message)
            finally:
                self.queue.task_done()

    def submit(self, body, side, mode):
        if side not in ('L', 'R') or mode not in ('enroll', 'recognize'):
            raise ValueError('Olho ou modo inválido')
        if self.queue.full():
            raise ValueError('A fila do PC está cheia. Aguarde a análise atual.')
        if len(body) > MAX_BODY:
            raise ValueError('Foto muito grande. Recorte um olho antes de enviar.')
        try:
            with Image.open(io.BytesIO(body)) as opened:
                if opened.format not in ('JPEG', 'PNG', 'WEBP'):
                    raise ValueError('Envie uma foto JPEG, PNG ou WebP')
                if opened.width * opened.height > Image.MAX_IMAGE_PIXELS:
                    raise ValueError('Foto muito grande. Recorte um olho.')
                photo = ImageOps.exif_transpose(opened).convert('RGB')
                if min(photo.size) < 64:
                    raise ValueError('O recorte está pequeno demais')
                photo.thumbnail((2560, 2560), Image.Resampling.LANCZOS)
                digest = hashlib.sha256(str(photo.size).encode() + photo.tobytes()).hexdigest()
        except (OSError, Image.DecompressionBombError) as error:
            raise ValueError('Arquivo de foto inválido') from error
        key = uid()
        folder = self.store.capture_dir(key)
        folder.mkdir()
        photo.save(folder / 'input.jpg', quality=95, subsampling=0)
        with self.lock:
            self.jobs[key] = dict(id=key, status='queued', stage='fila', message='Aguardando o PC', created=time.time())
        try:
            self.queue.put_nowait((key, digest, side, mode))
        except queue.Full:
            self.store.discard(key)
            with self.lock:
                self.jobs.pop(key, None)
            raise ValueError('Fila cheia. Tente novamente em instantes.')
        return key


class Handler(BaseHTTPRequestHandler):
    server_version = 'IrisLocal/1'

    @property
    def app(self):
        return self.server.app

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, fmt, *args):
        logging.info('%s %s', self.client_address[0], fmt % args)

    def send(self, value, status=200, content_type='application/json; charset=utf-8'):
        body = json.dumps(value, ensure_ascii=False).encode() if not isinstance(value, bytes) else value
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def guard(self, auth=True):
        host = self.headers.get('Host', '')
        allowed = {f'{x}:{self.app.port}' for x in self.app.addresses}
        if host not in allowed:
            self.send({'error': 'Host não permitido'}, 403)
            return False
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + host:
            self.send({'error': 'Origem não permitida'}, 403)
            return False
        if auth:
            token = self.headers.get('Authorization', '').removeprefix('Bearer ')
            if not token or not self.app.store.authorize(token):
                self.send({'error': 'Conecte o celular com o código exibido no PC'}, 401)
                return False
        return True

    def body(self, limit=MAX_BODY):
        if self.headers.get('Transfer-Encoding'):
            raise ValueError('Formato de envio não suportado')
        try:
            length = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            raise ValueError('Tamanho inválido')
        if length < 0 or length > limit:
            raise ValueError('Arquivo ou requisição grande demais')
        result = self.rfile.read(length)
        if len(result) != length:
            raise ValueError('Envio interrompido. Tente novamente.')
        return result

    def do_GET(self):
        path = urlsplit(self.path).path
        public = path in ('/', '/app.js', '/style.css', '/api/status', '/api/pairing', '/api/qr.svg', '/favicon.ico')
        if not self.guard(auth=not public):
            return
        try:
            if path in ('/', '/app.js', '/style.css'):
                filename, kind = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}[path]
                self.send((APP_ROOT / 'app_celular/web' / filename).read_bytes(), content_type=kind)
            elif path == '/favicon.ico':
                self.send(b'', 204, 'image/x-icon')
            elif path == '/api/status':
                self.send(dict(online=True, model='SAM3.1 + descritores de íris', local_only=True, phone_validated=False,
                    transport=getattr(self.server,'transport','pc')))
            elif path in ('/api/pairing', '/api/qr.svg'):
                if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                    self.send({'error': 'Código disponível somente no PC'}, 403)
                    return
                address = next((x for x in self.app.addresses if x not in ('localhost', '127.0.0.1')), '127.0.0.1')
                url = f'http://{address}:{self.app.port}/'
                if path.endswith('.svg'):
                    import qrcode
                    import qrcode.image.svg
                    qr = qrcode.make(url + '#pair=' + self.app.code, image_factory=qrcode.image.svg.SvgPathFillImage)
                    self.send(qr.to_string(), content_type='image/svg+xml')
                else:
                    self.send(dict(url=url, code=self.app.code, lan_enabled=self.server.server_address[0]!='127.0.0.1',
                        transport=getattr(self.server,'transport','pc'), expires='ao reiniciar o aplicativo'))
            elif path == '/api/gallery':
                self.send(self.app.store.people())
            elif path == '/api/trials':
                self.send(self.app.store.trials())
            elif path.startswith('/api/jobs/'):
                key = path.rsplit('/', 1)[-1]
                with self.app.lock:
                    job = self.app.jobs.get(key)
                    if not job:
                        try:
                            saved = self.app.store.capture(key)
                            result = json.loads(saved['result'])
                            result['already_enrolled'] = bool(saved['person'])
                            self.send(dict(id=key,status='done',stage='concluido',message='Análise salva no PC',result=result))
                        except ValueError:
                            self.send({'error': 'Análise não encontrada. Faça uma nova captura.'}, 404)
                    else:
                        self.send(dict(job))
            elif path.startswith('/api/assets/'):
                parts = path.split('/')
                if len(parts) != 5 or parts[4] not in ('overlay.jpg', 'polar.png', 'input.jpg', 'mask.png'):
                    raise ValueError('Imagem não disponível')
                folder = self.app.store.capture_dir(parts[3])
                self.send((folder / parts[4]).read_bytes(), content_type='image/png' if parts[4].endswith('.png') else 'image/jpeg')
            else:
                self.send({'error': 'Rota não encontrada'}, 404)
        except (ValueError, FileNotFoundError) as error:
            self.send({'error': str(error)}, 400)
        except Exception:
            logging.exception('Falha HTTP GET')
            self.send({'error': 'Falha no PC. Consulte execucao.log'}, 500)

    def do_POST(self):
        path = urlsplit(self.path).path
        if not self.guard(auth=path != '/api/pair'):
            return
        try:
            if path == '/api/analyze':
                key = self.app.submit(self.body(), self.headers.get('X-Eye-Side'), self.headers.get('X-Mode'))
                self.send({'id': key}, 202)
                return
            data = json.loads(self.body(8192))
            if not isinstance(data, dict):
                raise ValueError('Requisição inválida')
            if path == '/api/pair':
                now = time.time()
                with self.app.lock:
                    attempts = [x for x in self.app.attempts[self.client_address[0]] if now - x < 300]
                    attempts.append(now)
                    self.app.attempts[self.client_address[0]] = attempts
                if len(attempts) > 10:
                    self.send({'error': 'Muitas tentativas. Aguarde cinco minutos.'}, 429)
                    return
                if not secrets.compare_digest(str(data.get('code', '')), self.app.code):
                    self.send({'error': 'Código incorreto. Veja o código na tela do PC.'}, 403)
                    return
                token = secrets.token_urlsafe(32)
                self.app.store.add_device(token)
                self.send({'token': token})
            elif path == '/api/enroll':
                if data.get('reviewed') is not True:
                    raise ValueError('Confira o recorte verde antes de cadastrar')
                with self.app.mutations:
                    capture = self.app.store.capture(str(data.get('capture', '')))
                    if json.loads(capture['result'])['mode'] != 'enroll':
                        raise ValueError('Use o modo cadastro para adicionar uma pessoa')
                    person = self.app.store.enroll(capture['id'], data.get('name', ''), data.get('person_id'), self.app.engine.engine_id)
                self.send({'person_id': person})
            elif path == '/api/trials':
                with self.app.mutations:
                    try:
                        correct = self.app.store.trial(str(data.get('capture', '')), str(data.get('expected', '')))
                    except __import__('sqlite3').IntegrityError:
                        raise ValueError('Este teste já foi registrado')
                self.send({'top1_correct': correct})
            elif path == '/api/delete-person':
                with self.app.mutations:
                    removed = self.app.store.delete_person(str(data.get('person_id', '')))
                with self.app.lock:
                    for key in removed:
                        self.app.jobs.pop(key, None)
                self.send({'deleted': True})
            elif path == '/api/discard':
                key = str(data.get('capture', ''))
                with self.app.lock, self.app.mutations:
                    job = self.app.jobs.get(key)
                    if job and job['status'] in ('running', 'queued'):
                        raise ValueError('Aguarde o processamento terminar')
                    self.app.store.discard(key)
                    self.app.jobs.pop(key, None)
                self.send({'deleted': True})
            else:
                self.send({'error': 'Rota não encontrada'}, 404)
        except (ValueError, KeyError) as error:
            self.send({'error': str(error)}, 400)
        except Exception:
            logging.exception('Falha HTTP POST')
            self.send({'error': 'Falha no PC. Consulte execucao.log'}, 500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--address', action='append', default=[])
    parser.add_argument('--transport', choices=('pc','usb'), default='pc')
    parser.add_argument('--data', type=Path, default=APP_ROOT / 'dados_app_celular')
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=args.data / 'execucao.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    app = App(args.data, args.address, args.port)
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    server.app = app
    server.transport = args.transport
    (args.data / 'servidor.json').write_text(json.dumps(dict(pid=__import__('os').getpid(), port=args.port,
        addresses=args.address, started=time.time(), data=str(args.data.resolve()))), encoding='utf-8')
    logging.info('Servidor ativo na porta %s; pareamento disponivel em http://localhost:%s', args.port, args.port)
    try:
        server.serve_forever()
    finally:
        app.stopped.set()
        server.server_close()


if __name__ == '__main__':
    main()
