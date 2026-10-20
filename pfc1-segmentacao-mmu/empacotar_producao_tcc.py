"""Arquiva fontes, pesos treinados e resultados compactos com SHA256 verificavel."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
EXPERIMENTS=['cnn/ubipr_retreino_2026-10-20','biometria_area_completa_2026-10-20',
    'hdbif_slpvld_validacao_completa_2026-10-20','hdbif_slpvld_ablacao_validacao_2026-10-20',
    'hdbif_slpvld_teste_congelado_2026-10-20','identidade_arcface_ubipr_2026-10-20',
    'area_encoder_ubipr_2026-10-20','tolerancia_condicional_exploratoria_2026-10-20',
    'consolidacao_biometria_2026-10-20','nuclear_biometria_protocolo_2026-10-20',
    'nuclear_identidade_arcface_2026-10-20','nuclear_area_condicional_2026-10-20']

def main():
    paths=set(ROOT.glob('*.py'))|set(ROOT.glob('*.ps1'))|set(ROOT.glob('requirements*.txt'))
    for name in ['README.md','INSTALACAO_LOCAL.md','PLANO_ARTIGO_2026-11-09.md',
                 'PROTOCOLO_AREA_IRIS_2026-10-20.md','PESQUISA_BASES_PUBLICAS_2026-10-20.md',
                 'AVALIACAO_RECONHECEDORES_2026-10-20.md']:
        paths.add(ROOT/name)
    paths.update((ROOT/'artigo').glob('*.md'))
    for relative in EXPERIMENTS:
        folder=ROOT/'outputs'/relative
        for path in folder.iterdir():
            if not path.is_file() or path.suffix not in ('.json','.csv','.md','.pt','.npz','.py','.txt','.png','.svg'): continue
            if path.name.startswith('embeddings') or '.part' in path.name: continue
            paths.add(path)
    for relative in ['data/auditoria_instalacao.json','data/catscreen/auditoria.json','data/slid/auditoria.json',
                     'data/nuclear/auditoria.json','data/slpvld/auditoria.json',
                     'data/modelos/cvrl_hdbif/fontes.json','data/modelos/cvrl_hdbif/pesos.json']:
        if (ROOT/relative).exists(): paths.add(ROOT/relative)
    for relative in ['data/qa_biometria/nuclear/calibracao_inicial.png',
                     'data/qa_biometria/hdbif_slpvld_normalizacao_validacao.jpg']:
        if (ROOT/relative).exists(): paths.add(ROOT/relative)
    out=ROOT/'backups'; out.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination=out/f'producao_tcc_{stamp}.zip'; temporary=destination.with_suffix('.zip.part')
    hashes={}; total_bytes=0
    with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
        for path in sorted(paths):
            if not path.is_file(): raise FileNotFoundError(path)
            relative=path.relative_to(ROOT).as_posix(); content=path.read_bytes()
            hashes[relative]=hashlib.sha256(content).hexdigest(); total_bytes+=len(content)
            bundle.writestr(relative,content)
        bundle.writestr('SHA256.json',json.dumps(hashes,indent=2))
        bundle.writestr('ESCOPO.txt','Fontes, pesos treinados, resultados compactos e duas pranchas de QA. Datasets completos, caches de embeddings e caches de autenticacao nao incluidos. Pesos publicos pre-treinados devem ser obtidos conforme a documentacao e hashes registrados.\n')
    with zipfile.ZipFile(temporary) as bundle:
        for name,expected in hashes.items():
            if hashlib.sha256(bundle.read(name)).hexdigest()!=expected: raise ValueError('Archive integrity failure: '+name)
    temporary.replace(destination)
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.sha256').write_text(digest+'  '+destination.name+'\n',encoding='utf-8')
    report={'archive':str(destination),'files':len(hashes),'source_bytes':total_bytes,
            'archive_bytes':destination.stat().st_size,'sha256':digest,'verified_sha256_each_entry':True}
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
