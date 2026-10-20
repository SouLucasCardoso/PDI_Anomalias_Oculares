"""Recupera/audita os datasets usados pelo projeto sem iniciar treinamento."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from treinar_segmentacao_mmu import (
    prepare_data as prepare_mmu, build_manifest as manifest_mmu,
)
from treinar_segmentacao_ubipr import (
    prepare_data as prepare_ubipr, build_manifest as manifest_ubipr,
    split_by_subject, audit, sha256,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-download', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    data = root / 'data'
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'datasets': {}}
    for name in ('mmu', 'ubipr'):
        try:
            if name == 'mmu':
                images, masks = prepare_mmu(data, not args.no_download)
                rows = manifest_mmu(images, masks)
                detail = {'pairs': len(rows), 'subjects': len({r.subject for r in rows})}
                archive_paths = [data / 'archives/mmu-iris-dataset.zip',
                                 data / 'archives/mmu-masks-main.zip']
            else:
                images, archive = prepare_ubipr(data, not args.no_download)
                rows = manifest_ubipr(images)
                detail = audit(rows)
                splits = split_by_subject(rows, 42)
                detail['split_counts'] = {k: len(v) for k, v in splits.items()}
                # Manifesto local novo: nunca substitui checkpoints/resultados historicos.
                (data / 'manifesto_ubipr.json').write_text(json.dumps(
                    {k: [asdict(r) for r in v] for k, v in splits.items()},
                    ensure_ascii=False, indent=2), encoding='utf-8')
                archive_paths = [archive]
            detail['archives'] = [{
                'file': str(p.relative_to(root)), 'bytes': p.stat().st_size,
                'sha256': sha256(p),
            } for p in archive_paths]
            report['datasets'][name] = {'status': 'ok', **detail}
        except Exception as exc:
            report['datasets'][name] = {'status': 'error', 'error': str(exc)}
        print(name, report['datasets'][name]['status'], flush=True)
    data.mkdir(parents=True, exist_ok=True)
    (data / 'auditoria_instalacao.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if any(r['status'] != 'ok' for r in report['datasets'].values()):
        raise SystemExit('Ha datasets pendentes; consulte data/auditoria_instalacao.json')


if __name__ == '__main__':
    main()
