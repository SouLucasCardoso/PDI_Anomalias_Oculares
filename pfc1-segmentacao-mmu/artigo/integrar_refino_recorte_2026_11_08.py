"""Atualiza figuras e descreve o refino sem substituir ensaios congelados."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageOps,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=False)
    run=ROOT/'outputs/refino_recorte_sam31_final_2026-11-08'
    evidence=json.loads((run/'CONCLUIDO.json').read_text(encoding='utf-8'))
    rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    records=evidence['records'];fig=out/'figuras_2026-11-08';fig.mkdir()
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    for indices,filename in (([0,1],'recortes_normais.png'),([2,3],'recortes_anomalias.png'),([4,5],'recortes_limites_clinicos.png')):
        canvas=Image.new('RGB',(2100,1040),'white');draw=ImageDraw.Draw(canvas)
        for x,title in zip([0,710,1420],['Fotografia original','SAM3.1 experimental','Recorte em pixels nativos']):draw.text((x+12,12),title,font=font(40),fill='black')
        for line,index in enumerate(indices):
            record=records[index];row=next(r for r in rows if Path(r['image']).name==record['filename'])
            photo=Image.open(row['image']).convert('RGB');folder=run/Path(record['filename']).stem
            mask=np.asarray(Image.open(folder/'mask_nativa.png'))>0
            rgb=np.asarray(photo);overlay=rgb.copy();overlay[mask]=(.65*rgb[mask]+.35*np.array([0,220,100])).astype(np.uint8)
            crop=Image.open(folder/'recorte_nativo.png').convert('RGBA');black=Image.new('RGBA',crop.size,'black');black.alpha_composite(crop)
            top=90+line*465;draw.text((12,top-38),Path(row['image']).stem,font=font(38),fill='black')
            display=black.convert('RGB') if mask.any() else Image.new('RGB',(680,400),'black')
            for x,item in zip([0,710,1420],[photo,Image.fromarray(overlay),display]):
                canvas.paste(ImageOps.pad(item,(680,400),method=Image.Resampling.LANCZOS,color='white'),(x+10,top+10))
            if not mask.any():
                draw.text((1770,top+175),'LOCALIZAÇÃO INSUFICIENTE',font=font(34),fill='white',anchor='mm')
                draw.text((1770,top+225),'Requer revisão da máscara',font=font(32),fill='white',anchor='mm')
        canvas.save(fig/filename,dpi=(300,300))
    provenance={'method':'SAM3.1 official interactive image heads, native contour/pupil refinement; separate binary mask and display alpha; exact protocol and sources retained in run',
        'run':str(run),'run_protocol_sha256':sha(run/'protocolo.json'),'native_rgb_unchanged':True,
        'clinical_reference_masks_available':False,'recognition_reevaluated':False,'manual_mask_review_completed':False,
        'license':'SLP-VLD v3, Qian2026, CC BY4.0, doi10.6084/m9.figshare.32576697.v3',
        'records':records,'figure_sha256':{f.name:sha(f) for f in fig.glob('*.png')}}
    (fig/'PROVENIENCIA_FIGURAS.json').write_text(json.dumps(provenance,indent=2,ensure_ascii=False),encoding='utf-8')
    source=(ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-11-08.md').read_text(encoding='utf-8')
    def replace_paragraph(prefix,new):
        nonlocal source
        paragraphs=source.split('\n\n');matches=[i for i,s in enumerate(paragraphs) if s.startswith(prefix)]
        assert len(matches)==1,(prefix,len(matches));paragraphs[matches[0]]=new;source='\n\n'.join(paragraphs)
    replace_paragraph('As figuras clínicas foram escolhidas',
        'As seis fotografias ilustrativas foram mantidas no refino posterior com a cabeça interativa oficial SAM3.1. A U-Net forneceu pontos iniciais, sem diagnóstico ou referência manual. Íris e pupila foram previstas separadamente, com encoder de 1.008 pixels e segunda janela para a pupila. A confiança contínua foi interpolada antes do rótulo na resolução nativa. Componentes sem pontos de íris foram descartados; não se impôs círculo nem se preencheram lacunas. A transição alfa de um pixel afeta apenas a apresentação, preservando RGB e máscara binária. O cadastro inicialmente vazio permaneceu pendente de revisão. As métricas clínicas históricas foram preservadas.')
    replace_paragraph('A Figura 3 apresenta',
        'A Figura 3 apresenta os mesmos dois controles do SLP-VLD rotulados como Normal eye, agora com o refino interativo SAM3.1. Os contornos eliminam os grandes degraus da ampliação binária de uma entrada clínica de apenas 106 × 80 pixels. Os pontos foram obtidos automaticamente; nenhuma textura foi gerada e nenhuma borda foi corrigida manualmente.')
    replace_paragraph('Os exemplos mostram que o enquadramento',
        'A sobreposição verde representa uma previsão experimental, sem referência anatômica especializada. A pupila recebeu uma previsão local separada. Reflexos e bordas ainda exigem revisão: um contorno visualmente contínuo não demonstra que todos os pixels internos sejam íris utilizável, nem que o reconhecimento tenha melhorado.')
    replace_paragraph('Os recortes preservam uma porção',
        'O refino recupera um contorno externo mais contínuo e reduz a aparência em blocos. Persistem regiões que podem incluir pupila, reflexos ou ausência de tecido, especialmente na iridodiálise. Sem referência especializada, a apresentação não comprova Dice clínico, área anatômica preservada ou adequação biométrica. Essas falhas não foram escondidas com preenchimento ou ajuste elíptico.')
    replace_paragraph('A Figura 5 contrasta',
        'A Figura 5 mantém os dois casos difíceis: P0114, com cisto de íris e alterações corneanas, e P0803, com laceração e outras lesões. No segundo, a tentativa de localizar uma região a partir da entrada RGB produziu um fragmento inadequado junto à pupila. O candidato foi preservado para auditoria e o recorte final permaneceu vazio, exigindo revisão.')
    source=source.replace('Figura 5 - Ganho local e falha persistente no controle de escala','Figura 5 - Limites do refino e falha de localização mantida')
    replace_paragraph('No caso recuperado,',
        'A borda externa mais contínua do caso P0114 ainda não resolve a separação entre textura iridiana, reflexos e opacidade. No P0803, a indisponibilidade histórica não foi convertida em sucesso pelo simples aparecimento de pixels em um candidato. As figuras refinadas não foram usadas para recalcular a Tab. 12.')
    result=json.loads((ROOT/'outputs/refino_recorte_validacao_final_2026-11-08/CONCLUIDO.json').read_text())
    continuous=json.loads((ROOT/'outputs/contorno_continuo_2026-11-08/CONCLUIDO.json').read_text())
    fmt=lambda value:f'{100*value:.2f}'.replace('.',',')
    paragraph=f"Um controle posterior usou 78 imagens de validação, uma por lado de cada uma das 39 pessoas, sorteadas com semente fixa e sem filtrar resultados. A referência foi aberta somente após a inferência. O Dice médio da U-Net foi de {fmt(result['mean_dice_previous'])}%, contra {fmt(result['mean_dice_refined'])}% do refino SAM3.1. A interpolação da margem contínua da U-Net alcançou {fmt(continuous['mean_dice_continuous'])}%, com melhora em {continuous['improved']} imagens. Trata-se de desenvolvimento, sem teste independente ou nova avaliação de identidade. O refino SAM permaneceu ilustrativo e não substituiu o reconhecedor congelado."
    source=source.replace('<!-- pagina:28 -->',paragraph+'\n\n<!-- pagina:28 -->')
    source=source.replace('figuras_2026-11-05/recortes_','figuras_2026-11-08/recortes_')
    source=source.replace('Fonte: Qian (2026), SLP-VLD v3, CC BY 4.0. Máscaras, recortes e composição do autor.','Fonte: Qian (2026), SLP-VLD v3, CC BY 4.0. Refino SAM3.1 experimental e composição do autor.')
    (out/'ARTIGO_CONSOLIDADO_2026-11-08.md').write_text(source,encoding='utf-8')
    print(json.dumps({'figures':3,'validation_n':result['n'],'dice_unet':result['mean_dice_previous'],'dice_sam':result['mean_dice_refined'],'dice_continuous':continuous['mean_dice_continuous']}))

if __name__=='__main__':main()
