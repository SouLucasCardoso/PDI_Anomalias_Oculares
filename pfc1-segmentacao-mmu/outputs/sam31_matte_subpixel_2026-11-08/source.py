"""Reexecuta os mesmos seis recortes SAM3.1 e preserva suas máscaras binárias."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,time,traceback
import cv2,numpy as np,torch
from PIL import Image,ImageDraw,ImageFont,ImageOps
from recorte_iris_sam31_alta_res import Sam31HighResolution,antialiased_crop
from matte_subpixel_iris import subpixel_crop
from comparar_recortes_alta_res import NAMES
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


class CapturedSam31(Sam31HighResolution):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.calls=[]
    def predict(self,*args,**kwargs):
        result=super().predict(*args,**kwargs);self.calls.append(result[0].copy());return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--baseline-run',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False);pause=a.baseline_run.resolve()/'PAUSAR_PARA_REFINO'
    old=ROOT/'outputs/refino_recorte_sam31_final_2026-11-08';oldprotocol=json.loads((old/'protocolo.json').read_text())
    assert oldprotocol['sources_sha256']['recorte_iris_sam31_alta_res.py']==sha(ROOT/'recorte_iris_sam31_alta_res.py')
    versions_file=ROOT/'outputs/tecnologias_grade_densa_2026-11-08.json';versions=json.loads(versions_file.read_text(encoding='utf-8-sig'))
    assert versions['code_revision']=='f1647e8d0c1d280991f4d1b7d974c2704537fe66'
    assert versions['checkpoint_revision']=='daa63191845a41281374e725f4c9e51c7a824460'
    sources={n:sha(ROOT/n) for n in ('refinar_matte_sam31_entrega.py','matte_subpixel_iris.py','recorte_iris_sam31_alta_res.py')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'images':NAMES,'sources_sha256':sources,
        'official_versions':versions,'prior_protocol_sha256':sha(old/'protocolo.json'),
        'scope':'Display-only matte refinement of same six fixed clinical examples; binary masks must match previous SAM3.1 results exactly. No measured clinical or recognition improvement.',
        'method':'Capture native iris/pupil logits, combine min(iris,-pupil), local gradient normalizes zero-crossing for one-native-pixel opacity coverage. Interior alpha255, support outside1pixel alpha0, original RGB exact. Previously empty case remains empty.'}
    (run/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(run/'source.py').write_bytes(Path(__file__).read_bytes())
    def stage(name,**extra):(run/'estado.json').write_text(json.dumps({'stage':name,'utc':datetime.now(timezone.utc).isoformat(),**extra}),encoding='utf-8')
    owns=False;sam=None
    try:
        # The validation owns its own pause marker; wait until it has released it.
        val=ROOT/'outputs/contorno_componentes_identidade_2026-11-08'
        while not (val/'CONCLUIDO.json').exists() or pause.exists():stage('aguardando_validacao');time.sleep(2)
        pause.write_text('Exportação curta SAM3.1; liberação automática no finally.',encoding='utf-8');owns=True
        while True:
            state=json.loads((a.baseline_run/'estado.json').read_text())
            if state['stage'] in ('aguardando_refino_validacao','concluido','parcial_por_limite_horario','falha'):break
            stage('aguardando_fronteira_segura_gpu');time.sleep(2)
        torch.set_num_threads(2);cv2.setNumThreads(1);stage('carregando_sam31');sam=CapturedSam31('cuda')
        (run/'SAM_ESTRITO.json').write_text(json.dumps(sam.audit,indent=2),encoding='utf-8')
        rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'));records=[]
        for i,name in enumerate(NAMES):
            stage('refinando_alpha',completed=i,total=6,image=name);row=next(r for r in rows if Path(r['image']).name==name)
            photo=Image.open(row['image']).convert('RGB');prior=old/Path(name).stem;folder=run/Path(name).stem;folder.mkdir()
            mask=np.asarray(Image.open(prior/'mask_nativa.png').convert('L'))>0
            margin=np.full(mask.shape,-32.,np.float32);detail={};sam.calls=[]
            if mask.any():
                seed=np.asarray(Image.open(prior/'mask_localizacao.png').convert('L'))>0
                calculated,detail=sam.refine(photo,seed);np.testing.assert_array_equal(calculated,mask)
                x0,y0,x1,y1=detail['roi_xyxy'];local=sam.calls[0][detail['selected_index']].copy()
                pupil=detail['pupil_refinement']
                if pupil.get('status')=='sam31_refined':
                    px0,py0,px1,py1=pupil['zoom_xyxy_in_roi'];pm=np.full(local.shape,-32.,np.float32)
                    pm[py0:py1,px0:px1]=sam.calls[1][pupil['selected_index']]
                    local=np.minimum(local,-pm)
                margin[y0:y1,x0:x1]=local
            new,box=subpixel_crop(photo,mask,margin);new.save(folder/'recorte_subpixel.png')
            Image.fromarray(mask.astype(np.uint8)*255).save(folder/'mask_nativa.png');np.savez_compressed(folder/'margem_nativa.npz',margin=margin)
            previous=antialiased_crop(photo,mask);canvas=Image.new('RGB',(1800,760),'white');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
            for col,(crop,label) in enumerate(((previous,'Anterior: borda binária'),(new,'Novo: cobertura subpixel'))):
                bg=Image.new('RGBA',crop.size,'black');bg.alpha_composite(crop)
                canvas.paste(ImageOps.pad(bg.convert('RGB'),(870,660),method=Image.Resampling.LANCZOS),(col*900+15,70));draw.text((col*900+15,18),label,font=font,fill='black')
                if not mask.any():draw.text((col*900+80,370),'SEM SUPORTE / REVISAR',font=font,fill='#ffb34b')
            canvas.save(folder/'comparacao.png')
            records.append({'image':name,'photo_sha256':sha(row['image']),'binary_mask_equal_previous':True,
                'mask_pixels':int(mask.sum()),'native_rgb_exact':True,'display_only':True,'bbox_xyxy':list(box),
                'mask_sha256':sha(folder/'mask_nativa.png'),'crop_sha256':sha(folder/'recorte_subpixel.png'),
                'clinical_review_required':True,'clinical_accuracy_measured':False})
        sam.close();sam=None;pause.unlink();owns=False
        for n,expected in sources.items():assert sha(ROOT/n)==expected
        result={'status':'concluido','records':records,'recognition_mask_changed':False,'recognition_recalculated':False,'clinical_accuracy_claimed':False}
        (run/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');stage('concluido',completed=6,total=6)
        (run/'RELATORIO_ATUAL.md').write_text('# Recortes SAM3.1 com cobertura subpixel\n\nSeis casos fixos, com máscaras binárias idênticas às anteriores. RGB nativo preservado; apenas a transparência de até um pixel na borda foi alterada. O caso sem suporte permanece pendente de revisão. Não há novo ganho de segmentação clínica ou reconhecimento atribuído a esta apresentação.\n',encoding='utf-8')
        print(json.dumps(result),flush=True)
    except BaseException as error:
        stage('falha',error=str(error));(run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
    finally:
        if sam is not None:sam.close()
        if owns:pause.unlink(missing_ok=True)


if __name__=='__main__':main()
