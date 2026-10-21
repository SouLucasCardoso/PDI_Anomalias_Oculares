"""Backup local verificavel dos pesos, escores e codigos de desenvolvimento."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, zipfile

ROOT = Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path);args=parser.parse_args()
    files = set(ROOT.glob('*.py')) | set(ROOT.glob('*.md'))
    files.update(ROOT/n for n in ('requirements-windows.lock.txt','executar.ps1') if (ROOT/n).is_file())
    files.update((ROOT/'artigo').glob('*.md'))
    files.update((ROOT.parent / 'Relatórios-de-Avanço').glob('*2026-10-20.md'))
    names = ['encoder_polar', 'loggabor_polar_val', 'espacial_polar_val',
             'fusao_polar_rgb_val', 'fusao_espacial_val', 'encoder_polar_denso',
             'fusao_densa_val', 'metrica_intra_val']
    names += ['resnet50_sessoes','normalizacao_consulta','multivista_foto_unica',
              'espacial_capturas_val','normalizacao_cadastro','fusao_resnet50_val',
              'classificador_cadastro','convnext_contraste','lateralidade_resnet50',
              'fusao_lateral_4','fusao_lateral_5','classificador_lateral','fusao_convnext_val']
    for name in names:
        folder = ROOT / 'outputs' / (name + '_2026-10-20')
        files.update(p for p in folder.glob('*') if p.suffix in {'.json','.csv','.md','.pt','.npz','.png','.py'})
    for name in ['backbone_resnet50_2026-10-21','backbone_convnext_2026-10-21','resnet50_nativo224_2026-10-21','fusao_lateral_6_2026-10-21',
                 'transformer_polar_2026-10-21','fusao_lateral_7_2026-10-21','selecao_cadastro_2026-10-21','prototipos_escala_2026-10-21',
                 'alinhamento_transformer_2026-10-21','alinhamento_fotometrico_2026-10-21','arciris_polar_2026-10-21','arciris_red_2026-10-21','arciris_duas_vistas_2026-10-21','candidato_congelado_2026-10-21',
                 'dino_local6_2026-10-21','adaptacao_cadastro_2026-10-21','adaptacao_cadastro_v2_2026-10-21',
                 'fusao_probabilidades_5_2026-10-21','fusao_probabilidades_6_2026-10-21']:
        folder=ROOT/'outputs'/name
        files.update(p for p in folder.glob('*') if p.suffix in {'.json','.csv','.md','.pt','.npz','.png','.py'})
    files.update((ROOT/'data/cache_encoder_polar_2026-10-20').glob('*auditoria.json'))
    hashes = {str(p.relative_to(ROOT.parent)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    out = args.output_dir or ROOT/'backups'; out.mkdir(exist_ok=True,parents=True)
    target = out / ('pf_' + datetime.now(timezone.utc).strftime('%m%dT%H%M%S') + '.zip')
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(files): archive.write(p, str(p.relative_to(ROOT.parent)).replace('\\','/'))
        archive.writestr('SHA256_MANIFEST.json', json.dumps(hashes, indent=2))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name, expected in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n', encoding='utf-8')
    print(json.dumps({'file':str(target),'verified_files':len(hashes),'bytes':target.stat().st_size,'sha256':digest}, indent=2))

if __name__ == '__main__': main()
