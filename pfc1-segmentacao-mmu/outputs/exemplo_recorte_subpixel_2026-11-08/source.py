"""Exporta recorte em pixels nativos, máscara separada e borda subpixel."""
from pathlib import Path
import argparse,hashlib,json
import cv2,numpy as np,torch
from PIL import Image
from treinar_segmentacao_ubipr import MulticlassUNet
from contorno_multiescala_iris import margin_at_size
from contorno_componentes_iris import filter_mask
from matte_subpixel_iris import subpixel_crop
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--clinical-scale',action='store_true')
    p.add_argument('--sam3',action='store_true',help='Refino SAM3.1 experimental; requer GPU livre e revisão clínica.')
    a=p.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2);cv2.setNumThreads(1);photo=Image.open(a.image).convert('RGB')
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    model=MulticlassUNet(8).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    margin,_=margin_at_size(model,photo,320,a.clinical_scale);del model
    selection=ROOT/'outputs/contorno_fragmentos_entrega_2026-11-08/CANDIDATO_SEGMENTACAO.json'
    selected=json.loads(selection.read_text());assert selected['segmentation_gain']
    mask=filter_mask(margin>0,selected['spec']);detail={'segmentation':'continuous_native_margin_then_small_component_filter','spec':selected['spec']}
    if a.sam3 and mask.any():
        from refinar_matte_sam31_entrega import CapturedSam31
        sam=CapturedSam31('cuda')
        try:
            mask,refinement=sam.refine(photo,mask);x0,y0,x1,y1=refinement['roi_xyxy']
            local=sam.calls[0][refinement['selected_index']].copy();pupil=refinement['pupil_refinement']
            if pupil.get('status')=='sam31_refined':
                px0,py0,px1,py1=pupil['zoom_xyxy_in_roi'];pm=np.full(local.shape,-32.,np.float32)
                pm[py0:py1,px0:px1]=sam.calls[1][pupil['selected_index']];local=np.minimum(local,-pm)
            margin=np.full(mask.shape,-32.,np.float32);margin[y0:y1,x0:x1]=local
            detail.update(sam31=refinement,strict_model_audit=sam.audit)
        finally:sam.close()
    crop,box=subpixel_crop(photo,mask,margin);crop.save(out/'recorte_subpixel.png')
    Image.fromarray(mask.astype(np.uint8)*255).save(out/'mascara_nativa.png')
    np.savez_compressed(out/'margem_nativa.npz',margin=margin)
    detail.update(photo_sha256=sha(a.image),script_sha256=sha(__file__),unet_sha256=sha(checkpoint),
        selection_sha256=sha(selection),bbox_xyxy=list(box),native_rgb_exact=True,
        display_alpha_separate_from_binary_mask=True,review_required=bool(a.sam3 or not mask.any()),
        clinical_accuracy_claimed=False,recognition_approval=False)
    (out/'proveniencia.json').write_text(json.dumps(detail,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'output':str(out),'mask_pixels':int(mask.sum()),'bbox':list(box),'review_required':detail['review_required']}))


if __name__=='__main__':main()
