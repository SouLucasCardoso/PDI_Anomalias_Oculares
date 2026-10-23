"""Backup local verificavel dos pesos, escores e codigos de desenvolvimento."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, zipfile

ROOT = Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path);parser.add_argument('--confirmation-only',action='store_true',help='Backup incremental de codigo, relatorios, avaliacao e novos modelos; sem conjunto completo de pesos originais');args=parser.parse_args()
    files = set(ROOT.glob('*.py')) | set(ROOT.glob('*.md'))
    files.update(ROOT/n for n in ('requirements-windows.lock.txt','executar.ps1') if (ROOT/n).is_file())
    files.update((ROOT/'artigo').glob('*.md'))
    files.update((ROOT.parent / 'Relatórios-de-Avanço').glob('*2026-10-20.md'))
    files.update((ROOT.parent / 'Relatórios-de-Avanço').glob('*2026-10-21.*'))
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
                 'fusao_probabilidades_5_2026-10-21','fusao_probabilidades_6_2026-10-21',
                 'confirmacao_congelada_val_2026-10-21','confirmacao_congelada_test_2026-10-21']:
        folder=ROOT/'outputs'/name
        files.update(p for p in folder.glob('*') if p.suffix in {'.json','.csv','.md','.pt','.npz','.png','.py'})
    files.update((ROOT/'data/cache_encoder_polar_2026-10-20').glob('*auditoria.json'))
    for pattern in ['confirmacao_congelada_*2026-10-21','analise_confirmacao_congelada_2026-10-21','curva_oclusao_congelada_2026-10-21','refinamento_oclusao_congelada_2026-10-21','diagnostico_oclusao_congelada_2026-10-21','auditoria_oclusao_congelada_2026-10-21','diagnostico_geometria_fixa_2026-10-21','segmentacao_oclusao_2026-10-21','validacao_segmentacao_oclusao_identidade_2026-10-21','qa_segmentacao_oclusao_2026-10-21','dupla_segmentacao_val_2026-10-21']:
        for folder in (ROOT/'outputs').glob(pattern):
            files.update(p for p in folder.glob('*') if p.suffix in {'.json','.csv','.md','.npz','.py','.png'})
    new_segmenter=ROOT/'outputs/segmentacao_oclusao_2026-10-21/melhor_modelo.pt'
    if new_segmenter.exists():files.add(new_segmenter)
    for name in ['identidade_oclusao_segmentacao_2026-10-21','identidade_residual_oclusao_2026-10-21','fusao_identidade_adaptada_val_2026-10-21','fusao_identidade_residual_val_2026-10-21']:
        files.update(p for p in (ROOT/'outputs'/name).glob('*') if p.suffix in {'.json','.csv','.md','.npz','.py','.pt'})
    if args.confirmation_only:
        files={p for p in files if not p.is_relative_to(ROOT/'outputs') or p.parent.name.startswith(('confirmacao_congelada_','analise_confirmacao_congelada_','curva_oclusao_congelada_','refinamento_oclusao_congelada_','diagnostico_oclusao_congelada_','auditoria_oclusao_congelada_','diagnostico_geometria_fixa_','segmentacao_oclusao_','validacao_segmentacao_oclusao_identidade_','qa_segmentacao_oclusao_','dupla_segmentacao_val_','identidade_oclusao_segmentacao_','identidade_residual_oclusao_','fusao_identidade_adaptada_val_','fusao_identidade_residual_val_'))}
    hashes = {str(p.relative_to(ROOT.parent)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    out = args.output_dir or ROOT/'backups'; out.mkdir(exist_ok=True,parents=True)
    target = out / ('pf_' + datetime.now(timezone.utc).strftime('%m%dT%H%M%S') + '.zip')
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(files): archive.write(p, str(p.relative_to(ROOT.parent)).replace('\\','/'))
        archive.writestr('SHA256_MANIFEST.json', json.dumps(hashes, indent=2))
        archive.writestr('BACKUP_SCOPE.json',json.dumps({'incremental_confirmation_only':args.confirmation_only,'weights_included':any(p.suffix=='.pt' for p in files),'original_candidate_weights_included':not args.confirmation_only,'base_weights_backup_if_incremental':'pf_1021T042052.zip','base_backup_sha256_if_incremental':'b0d7fffd947e8bef696568b20bd118b69ba1c14098e243a9529b15556384d445'},indent=2))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name, expected in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n', encoding='utf-8')
    print(json.dumps({'file':str(target),'verified_files':len(hashes),'bytes':target.stat().st_size,'sha256':digest}, indent=2))

if __name__ == '__main__': main()
