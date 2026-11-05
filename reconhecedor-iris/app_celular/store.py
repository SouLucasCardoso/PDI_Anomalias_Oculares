"""Cadastro privado do demonstrador; nunca grava nos conjuntos de pesquisa."""
from __future__ import annotations
import contextlib
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import time
import uuid

import numpy as np


def uid():
    return uuid.uuid4().hex


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / '.gitignore').write_text('*\n', encoding='utf-8')
        (self.root / 'captures').mkdir(exist_ok=True)
        self.db = self.root / 'gallery.sqlite3'
        with self.connect() as db:
            db.executescript('''
              PRAGMA journal_mode=WAL;
              CREATE TABLE IF NOT EXISTS devices (hash TEXT PRIMARY KEY, expires REAL);
              CREATE TABLE IF NOT EXISTS people (id TEXT PRIMARY KEY, name TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS captures (
                id TEXT PRIMARY KEY, hash TEXT, side TEXT, engine TEXT, result TEXT,
                created REAL, person TEXT REFERENCES people(id));
              CREATE UNIQUE INDEX IF NOT EXISTS enrolled_hash ON captures(hash) WHERE person IS NOT NULL;
              CREATE TABLE IF NOT EXISTS trials (id TEXT PRIMARY KEY, capture TEXT UNIQUE,
                expected TEXT, ranking TEXT, top1_correct INTEGER, created REAL);
            ''')

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def capture_dir(self, key):
        if len(key) != 32 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('Captura inválida')
        path = (self.root / 'captures' / key).resolve()
        if path.parent != self.root / 'captures':
            raise ValueError('Caminho inválido')
        return path

    def authorize(self, token):
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            row = db.execute('SELECT expires FROM devices WHERE hash=?', (digest,)).fetchone()
        return bool(row and row['expires'] > time.time())

    def add_device(self, token):
        with self.connect() as db:
            db.execute('INSERT INTO devices VALUES (?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), time.time() + 7 * 86400))

    def save_capture(self, key, digest, side, result):
        with self.connect() as db:
            db.execute('INSERT INTO captures VALUES (?,?,?,?,?,?,NULL)',
                       (key, digest, side, result['engine_id'], json.dumps(result), time.time()))

    def capture(self, key):
        with self.connect() as db:
            row = db.execute('SELECT * FROM captures WHERE id=?', (key,)).fetchone()
        if not row:
            raise ValueError('Captura não encontrada')
        return dict(row)

    def duplicate(self, digest):
        with self.connect() as db:
            return bool(db.execute('SELECT 1 FROM captures WHERE hash=? AND person IS NOT NULL', (digest,)).fetchone())

    def people(self):
        with self.connect() as db:
            rows = db.execute('''SELECT p.id,p.name,c.side,count(c.id) samples
              FROM people p JOIN captures c ON c.person=p.id GROUP BY p.id,c.side ORDER BY p.name,c.side''').fetchall()
        return [dict(x) for x in rows]

    def enroll(self, key, name, person_id, engine):
        capture = self.capture(key)
        if capture['person'] or capture['engine'] != engine:
            raise ValueError('Captura já cadastrada ou produzida por outra versão do motor')
        name = str(name).strip()
        if not person_id and not 1 <= len(name) <= 60:
            raise ValueError('Informe um nome de até 60 caracteres')
        with self.connect() as db:
            if person_id:
                if not db.execute('SELECT 1 FROM people WHERE id=?', (person_id,)).fetchone():
                    raise ValueError('Pessoa não encontrada')
            else:
                person_id = uid()
                db.execute('INSERT INTO people VALUES (?,?)', (person_id, name))
            try:
                db.execute('UPDATE captures SET person=? WHERE id=? AND person IS NULL', (person_id, key))
            except sqlite3.IntegrityError as error:
                raise ValueError('Essa mesma imagem já está no cadastro. Use outra foto.') from error
        return person_id

    def groups(self, side, engine):
        with self.connect() as db:
            rows = db.execute('''SELECT c.id,p.id person_id,p.name,c.side FROM captures c
                JOIN people p ON p.id=c.person WHERE c.side=? AND c.engine=? ORDER BY c.created''', (side, engine)).fetchall()
        groups = {}
        for row in rows:
            key = row['person_id']
            if key not in groups:
                groups[key] = dict(person_id=key, name=row['name'], side=side, features=[])
            with np.load(self.capture_dir(row['id']) / 'features.npz', allow_pickle=False) as data:
                groups[key]['features'].append({name: data[name] for name in data.files})
        return list(groups.values())

    def trial(self, capture_id, expected):
        capture = self.capture(capture_id)
        result = json.loads(capture['result'])
        if capture['person'] or 'matching' not in result or result['matching'].get('duplicate_image'):
            raise ValueError('Use uma nova captura de reconhecimento')
        ranking = result['matching']['ranking']
        if expected != 'unknown' and expected not in {x['person_id'] for x in ranking}:
            raise ValueError('Selecione a pessoa fotografada ou não cadastrada')
        # Unknown trials cannot become false-acceptance statistics: no decision threshold exists.
        correct = None if expected == 'unknown' or not ranking else int(ranking[0]['person_id'] == expected)
        with self.connect() as db:
            db.execute('INSERT INTO trials VALUES (?,?,?,?,?,?)',
                       (uid(), capture_id, expected, json.dumps(ranking), correct, time.time()))
        return correct

    def trials(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,expected,top1_correct,created FROM trials ORDER BY created DESC').fetchall()
        return [dict(x) for x in rows]

    def delete_person(self, person_id):
        with self.connect() as db:
            rows = db.execute('SELECT id FROM captures WHERE person=? OR person IS NULL', (person_id,)).fetchall()
            # Trial rankings include names and component scores: delete them with the participant.
            db.execute('DELETE FROM trials')
            db.execute('DELETE FROM captures WHERE person=? OR person IS NULL', (person_id,))
            db.execute('DELETE FROM people WHERE id=?', (person_id,))
        for row in rows:
            path = self.capture_dir(row['id'])
            if path.exists():
                shutil.rmtree(path)
        return [row['id'] for row in rows]

    def discard(self, key):
        with self.connect() as db:
            row = db.execute('SELECT person FROM captures WHERE id=?', (key,)).fetchone()
            if row and row['person']:
                raise ValueError('Remova a pessoa pela galeria para excluir uma foto cadastrada')
            db.execute('DELETE FROM trials WHERE capture=?', (key,))
            db.execute('DELETE FROM captures WHERE id=?', (key,))
        path = self.capture_dir(key)
        if path.exists():
            shutil.rmtree(path)
