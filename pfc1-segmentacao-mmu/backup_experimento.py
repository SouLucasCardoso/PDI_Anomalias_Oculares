"""Cria copia ZIP verificavel de pesos e registros, sem copiar datasets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile
import time

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=Path)
    parser.add_argument('--wait-for',help='Nome do marcador de conclusao a aguardar por ate seis horas')
    args = parser.parse_args()
    experiment = args.experiment.resolve()
    if not experiment.is_relative_to((ROOT / 'outputs').resolve()):
        raise ValueError('O experimento deve estar dentro de outputs/')
    if args.wait_for:
        if Path(args.wait_for).name!=args.wait_for: raise ValueError('Marcador deve ser apenas um nome de arquivo')
        deadline=time.monotonic()+6*3600
        while not (experiment/args.wait_for).is_file():
            if time.monotonic()>deadline: raise TimeoutError('Marcador de conclusao nao encontrado')
            time.sleep(30)
    files = [p for p in experiment.iterdir() if p.is_file() and p.suffix in ('.pt', '.json', '.csv')]
    if not any(p.name == 'melhor_modelo.pt' for p in files):
        raise FileNotFoundError('Checkpoint ausente')
    out = ROOT / 'backups'
    out.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = out / f'{experiment.name}_{stamp}.zip'
    hashes = {}
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            content = path.read_bytes()
            hashes[path.name] = hashlib.sha256(content).hexdigest()
            bundle.writestr(f'{experiment.name}/{path.name}', content)
        source = experiment/'source.py' if (experiment/'source.py').exists() else ROOT/'treinar_segmentacao_ubipr.py'
        content = source.read_bytes()
        bundle.writestr('source/'+source.name, content)
        hashes['source/'+source.name] = hashlib.sha256(content).hexdigest()
        dependencies=['requirements-windows.lock.txt','executar.ps1']
        if source.name=='source.py':
            dependencies+=['treinar_identidade_iris.py','avaliar_dinov3_ubipr.py',
                           'avaliar_robustez_reconhecimento.py','treinar_segmentacao_ubipr.py',
                           'preparar_nuclear_biometria.py','avaliar_identidade_nuclear.py',
                           'avaliar_area_nuclear_condicional.py','relatar_area_preservada.py']
        for name in dependencies:
            path=ROOT/name
            if path.is_file():
                content=path.read_bytes(); entry='dependencies/'+name
                bundle.writestr(entry,content); hashes[entry]=hashlib.sha256(content).hexdigest()
        bundle.writestr('SHA256.json', json.dumps(hashes, indent=2))
    with zipfile.ZipFile(target) as bundle:
        if bundle.testzip():
            raise ValueError('Falha na verificacao do ZIP')
    print(target)
    print('Backup local criado. Para protecao contra falha de disco, mantenha tambem copia externa.')


if __name__ == '__main__':
    main()
