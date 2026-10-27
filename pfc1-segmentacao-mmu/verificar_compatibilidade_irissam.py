"""Confere formas do checkpoint remoto contra SAM ViT-H sem alocar seus pesos."""
from pathlib import Path
import json,sys,tempfile
import torch
def main():
    folder=Path(tempfile.gettempdir())/'pfc-irissam';sys.path.insert(0,str(folder/'runtime'))
    from segment_anything import sam_model_registry
    source=json.loads((folder/'INSPECAO_CHECKPOINT_REMOTO.json').read_text());metadata=source['iris_metadata']
    with torch.device('meta'):model=sam_model_registry['vit_h'](checkpoint=None)
    expected=model.state_dict();assert set(metadata)==set(expected)
    for k,v in expected.items():assert list(v.shape)==metadata[k]['shape'],k
    result=dict(status='checkpoint_tensor_shapes_match_SAM_ViT_H',tensors=len(expected),parameters=sum(p.numel() for p in model.parameters()),image_size=model.image_encoder.img_size,weights_allocated=False,comparison=source.get('comparison'),checkpoint_dataset_metadata_available=False)
    (folder/'COMPATIBILIDADE_RUNTIME.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='comparison'},indent=2))
if __name__=='__main__':main()
