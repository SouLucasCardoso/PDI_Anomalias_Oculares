"""Reconstroi o primeiro lote predefinido do cache variado, sem escolher por escore."""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
import torch
from oclusao_diversa_polar import paint
from preparar_encoder_espacial import ROOT,file_hash
from encoder_polar_espacial import prefix_model,prefix_features
from treinar_identidade_iris import IdentityEncoder
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from textura_polar import prepare_texture
NAME='diversidade_oclusao_treino_2026-10-24'

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME;protocol=json.loads((folder/'protocolo.json').read_text());record=json.loads((folder/'CACHE_DIVERSO_CONCLUIDO.json').read_text());assert file_hash(folder/'cache_diverso.npy')==record['sha256'];rows=json.loads((folder/'rows.json').read_text());manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());native={Path(r['image']).name:r for r in manifest['train']};plan=protocol['augmentation_plan'][:32];torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device='cuda' if torch.cuda.is_available() else 'cpu';photos=[];counts=[]
    for v in plan:
        row=rows[v['index']];assert row['subject'] in protocol['fit_people'] and row['session']==2;r=native[Path(row['image']).name]
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(r['image']).name) as im:rgb=im.convert('RGB')
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(r['mask']).name) as im:reference=decode_mask(im)==1
        im,support=paint(rgb,reference,v['kind'],v['level'],v['value']);assert int(support.sum())==round(int(reference.sum())*v['level']/100);assert (np.asarray(im)[support]==v['value']).all();np.testing.assert_array_equal(np.asarray(im)[~support],np.asarray(rgb)[~support]);photos.append(im);counts.append(int(support.sum()))
    unet=MulticlassUNet(8).to(device).eval();uf=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert file_hash(uf)==protocol['unet_sha256'];unet.load_state_dict(torch.load(uf,map_location='cpu',weights_only=True)['model']);x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
    with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
    textures=[];valid=[]
    for photo,small in zip(photos,masks):
        mask=np.asarray(Image.fromarray(small).resize(photo.size,Image.Resampling.NEAREST),bool)
        try:texture=prepare_texture(np.asarray(photo),mask)[0];valid.append(True)
        except ValueError:texture=np.full((64,512,3),127,np.uint8);valid.append(False)
        textures.append(texture)
    encoder=IdentityEncoder().to(device).eval();ef=ROOT/protocol['encoder_relative_path'];assert file_hash(ef)==protocol['encoder_sha256'];encoder.load_state_dict(torch.load(ef,map_location='cpu',weights_only=True)['model']);expected=prefix_features(prefix_model(encoder).to(device),np.stack(textures),device);saved=np.load(folder/'cache_diverso.npy',mmap_mode='r')[:32];difference=float(np.max(np.abs(expected-saved)));np.testing.assert_allclose(expected,saved,rtol=1e-5,atol=1e-5)
    with np.load(folder/'cache_diverso_valid.npz') as z:np.testing.assert_array_equal(valid,z['valid'][:32])
    report=dict(status='first_registered_diverse_batch_replayed',cases=32,selection='first32bycacheorder_not_selected_by_score',native_support_counts_and_fill_exact=True,automatic_segmentation_validity_exact=True,maximum_feature_absolute_difference=difference,feature_rtol=1e-5,feature_atol=1e-5,scope='Sampled cache audit only,not full3222map regeneration or new recognition evaluation')
    (folder/'AUDITORIA_AMOSTRA_NATIVA.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
