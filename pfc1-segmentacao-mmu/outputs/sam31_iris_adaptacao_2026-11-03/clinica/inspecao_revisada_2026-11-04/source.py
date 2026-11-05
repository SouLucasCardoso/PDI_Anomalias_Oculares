"""Prancha cientifica das predicoes ja salvas e de TODAS as primeiras revisoes normais."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

from avaliar_prontidao_anomalias import clinical_normals

ROOT = Path(__file__).resolve().parent
BASE = ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
PACK = ROOT/'outputs/revisao_clinica_2026-11-03'
OUT = BASE/'clinica/inspecao_revisada_2026-11-04'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise ValueError('Preservar inspecao existente; registrar outra revisao')
    final = read(BASE/'CONCLUIDO.json')
    prediction_final = read(BASE/'clinica/normal/CONCLUIDO.json')
    if prediction_final['checkpoint_sha256'] != final['checkpoint_sha256']:
        raise ValueError('Predicoes de outro candidato')
    metrics = clinical_normals(final['checkpoint_sha256'])
    records = {r['id']: r for r in metrics['records']}
    tasks = [t for t in read(PACK/'manifesto.json')['tasks'] if t['group'] == 'normal' and t['id'] in records]
    if not tasks:
        raise ValueError('Nenhuma primeira revisao concluida para inspecionar')
    os.environ.setdefault('MPLCONFIGDIR', str(Path(os.environ['TEMP'])/'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig, axes = plt.subplots(len(tasks), 4, figsize=(16, 4.6*len(tasks)), squeeze=False, layout='constrained')
    cases = []
    for row, task in enumerate(tasks):
        latest = read(PACK/'revisoes'/task['id']/'latest.json')
        if latest['status'] != 'reviewed_initial':
            raise ValueError('Revisao mudou durante a inspecao')
        photo = Path(task['image']);reference = PACK/latest['mask']
        prediction = BASE/'clinica/normal'/(task['id']+'.npz')
        if (sha(photo) != task['image_sha256'] or sha(reference) != records[task['id']]['mask_sha256'] or
                sha(prediction) != prediction_final['prediction_hashes'][task['id']]):
            raise ValueError('Fotografia, revisao ou predicao alterada')
        with Image.open(photo) as image:
            if image.getexif().get(274, 1) != 1:
                raise ValueError('Conferir orientacao EXIF antes de interpretar mascaras')
            rgb = image.convert('RGB').copy()
        with Image.open(reference) as image:
            target = np.asarray(image)
        with np.load(prediction, allow_pickle=False) as saved:
            shape = tuple(saved['shape'])
            predicted = np.unpackbits(saved['predicted'], count=int(np.prod(shape))).reshape(shape).astype(bool)
        if target.shape != predicted.shape or target.shape != (rgb.height, rgb.width):
            raise ValueError('Dimensoes nao alinhadas')
        # Zoom e somente apresentacao: uniao de referencia e predicao inclui os fragmentos externos.
        y, x = np.where((target == 1) | (target == 2) | predicted)
        margin = max(10, int(.08*max(int(np.ptp(x))+1, int(np.ptp(y))+1)))
        box = (max(0, int(x.min())-margin), max(0, int(y.min())-margin),
               min(rgb.width, int(x.max())+margin+1), min(rgb.height, int(y.max())+margin+1))
        x0,y0,x1,y1 = box
        zoom = rgb.crop(box)
        # Reduzir apenas a prancha, com classes/predicoes em vizinho mais proximo.
        factor = min(1., 600/max(zoom.size));size = tuple(max(1, round(s*factor)) for s in zoom.size)
        display = zoom.resize(size, Image.Resampling.BILINEAR)
        t = np.asarray(Image.fromarray(target[y0:y1,x0:x1]).resize(size, Image.Resampling.NEAREST))
        p = np.asarray(Image.fromarray(predicted[y0:y1,x0:x1]).resize(size, Image.Resampling.NEAREST), bool)
        truth = np.zeros((*t.shape, 4));truth[t == 1] = (0, 1, 0, .35);truth[t == 2] = (0, .4, 1, .5);truth[t == 255] = (1, .8, 0, .25)
        proposal = np.zeros((*t.shape, 4));proposal[p] = (0, 1, 1, .4)
        error = np.zeros((*t.shape, 4));error[p & (t != 1) & (t != 255)] = (1, 0, 0, .65)
        error[(~p) & (t == 1)] = (.8, 0, 1, .65);error[t == 255] = (1, .8, 0, .25)
        full = rgb.copy();full.thumbnail((600, 600))
        axes[row,0].imshow(full);axes[row,0].set_title(task['id']+'\nFotografia completa', fontsize=10)
        for col in (1, 2, 3):axes[row,col].imshow(display)
        axes[row,1].imshow(truth);axes[row,1].set_title('Primeira revisão do usuário\nVerde: íris; azul: pupila; amarelo: incerto', fontsize=10)
        axes[row,2].imshow(proposal);axes[row,2].set_title('Íris prevista: ciano\nModelo da época 15, sem consulta à referência', fontsize=10)
        axes[row,3].imshow(error)
        m = records[task['id']]
        axes[row,3].set_title(f"FP vermelho; FN roxo; incerto amarelo\nDice {100*m['dice']:.1f}%; pupila incluída {100*m['pupil_leak']:.1f}%", fontsize=10)
        for axis in axes[row]:axis.axis('off')
        cases.append({'id': task['id'], 'image_sha256': sha(photo), 'reference_sha256': sha(reference),
                      'prediction_sha256': sha(prediction), 'presentation_crop_xyxy': list(box), 'metrics': m})
    fig.suptitle('Inspeção preliminar de todos os controles normais com primeira revisão concluída\nReferências do usuário; confirmação por especialista separada. O zoom não foi usado na inferência.', fontsize=13)
    fig.savefig(OUT/'comparacao_revisada.png', dpi=160)
    plt.close(fig)
    record = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sha(Path(__file__)),
              'checkpoint_sha256': final['checkpoint_sha256'], 'cases': cases, 'metrics': metrics,
              'case_selection': 'All normal controls with completed initial user review and saved predictions; no score filtering',
              'references_used_in_inference': False, 'no_new_inference': True, 'expert_confirmed': False,
              'unknown_pixels_excluded_from_dice': True, 'sufficient_for_clinical_gate': False,
              'figure_sha256': sha(OUT/'comparacao_revisada.png')}
    (OUT/'INSPECAO.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    lines = ['# Primeiras referências clínicas e candidato SAM3', '',
             '**Inspeção preliminar; não libera o piloto com anomalias.**', '',
             '![Comparação](comparacao_revisada.png)', '',
             '| Controle | Dice em pixels conhecidos | Pupila incluída na íris prevista | Incerteza na região anotada |',
             '|---|---:|---:|---:|']
    for item in cases:
        m=item['metrics']
        lines.append(f"| {item['id']} | {100*m['dice']:.2f}% | {100*m['pupil_leak']:.2f}% | {100*m['uncertain_fraction']:.2f}% |")
    lines += ['', 'Todas as primeiras revisões concluídas dos controles normais foram incluídas. A amostra atual tem duas fotografias e as referências mantêm regiões incertas; o Dice exclui esses pixels. São revisões iniciais do usuário, sem confirmação anatômica por especialista.', '',
              'A inclusão da pupila persiste nos dois controles e excede a meta média de 2% registrada. A incerteza também supera o limite de 5% na região de íris/pupila. Ainda são necessárias as demais referências e avaliação completa; estas duas fotografias não estimam desempenho populacional ou efeito clínico.', '',
              'As máscaras, os pesos e as revisões permaneceram intactos. A prancha usa previsões já preservadas, sem nova inferência ou seleção de checkpoint.']
    (OUT/'RELATORIO.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'cases': len(cases), 'macro_dice': metrics['macro_dice'],
                      'macro_pupil_leak': metrics['macro_pupil_leak'], 'clinical_pilot_ready': False}))


if __name__ == '__main__':
    main()
