"""Diagnostico pareado dos componentes e entradas reais, sem nova selecao."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'diagnostico_oclusao_congelada_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    baseline=a.output_root/'confirmacao_congelada_test_2026-10-21';names=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red'];records=[]
    for orientation in ['oclusao_superior','oclusao_inferior']:
        altered=a.output_root/f'confirmacao_congelada_test_{orientation}_10_2026-10-21'
        for name in names:
            with np.load(baseline/f'scores_{name}.npz') as z:b={k:z[k] for k in ['scores','labels','valid']}
            with np.load(altered/f'scores_{name}.npz') as z:c={k:z[k] for k in ['scores','labels','valid']}
            np.testing.assert_array_equal(b['labels'],c['labels']);labels=b['labels'];i=np.arange(len(labels));valid=b['valid']&c['valid']
            records.append(dict(component=name,orientation=orientation,original_rank1=float(((b['scores'].argmax(1)==labels)&b['valid']).mean()),altered_rank1=float(((c['scores'].argmax(1)==labels)&c['valid']).mean()),genuine_score_change_mean_on_paired_valid=float((c['scores'][i,labels]-b['scores'][i,labels])[valid].mean()),prediction_changed_queries=int((b['scores'].argmax(1)!=c['scores'].argmax(1)).sum())))
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['test'];selected=[];seen=set()
    for i,r in enumerate(rows):
        if r.session==2 and r.subject not in seen:selected.append(i);seen.add(r.subject)
        if len(selected)==4:break
    conditions=['original','oclusao_superior','oclusao_inferior'];cache={}
    for condition in conditions:
        suffix='' if condition=='original' else '_'+condition+'_10';folder=a.output_root.parent/f'cache_confirmacao_test{suffix}_2026-10-21';cache[condition]={k:np.load(folder/(k+'.npy'),mmap_mode='r') for k in ['rgb','polar']}
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    canvas=Image.new('RGB',(1420,1530),'#f3f5f7');draw=ImageDraw.Draw(canvas);draw.text((25,20),'Efeito da oclusão sobre os recortes e a normalização polar',font=font(29),fill='#172333')
    draw.text((25,65),'UBIPr teste • primeiras consultas de quatro pessoas • segmentação e geometria recalculadas',font=font(21),fill='#425369')
    for x,label in zip([25,495,965],['Original, sem oclusão adicional','10% de oclusão superior','10% de oclusão inferior']):draw.text((x,110),label,font=font(21),fill='#172333')
    samples=[]
    for j,i in enumerate(selected):
        top=160+j*315;draw.text((25,top),Path(rows[i].image).name,font=font(20),fill='#172333')
        for x,condition in zip([25,495,965],conditions):
            rgb=Image.fromarray(np.asarray(cache[condition]['rgb'][i]));polar=Image.fromarray(np.asarray(cache[condition]['polar'][i]));canvas.paste(ImageOps.pad(rgb,(440,200),color='white'),(x,top+30));canvas.paste(polar.resize((440,55)),(x,top+239))
        samples.append({'manifest_index':i,'image':Path(rows[i].image).name,'subject':rows[i].subject})
    draw.text((25,1450),'Faixas polares: entrada com CLAHE. As diferenças incluem perda de pixels e resposta do pré-processamento.',font=font(20),fill='#425369')
    draw.text((25,1480),'A prancha não isola o efeito da textura nem prova que uma doença cause a mesma alteração.',font=font(20),fill='#425369')
    canvas.save(out/'recortes_sob_oclusao.png')
    final={'scope':'Paired component diagnosis at10% occlusion; no model/threshold changes, no causal isolation of texture versus preprocessing','records':records,'visual_selection':'First session2 query per first4 distinct test subjects in manifest order, no score selection','samples':samples,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'DIAGNOSTICO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print(json.dumps({'samples':samples,'directory':str(out)},indent=2))

if __name__=='__main__':main()
