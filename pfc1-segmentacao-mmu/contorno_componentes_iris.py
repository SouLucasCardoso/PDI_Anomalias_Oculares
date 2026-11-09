"""Remove fragmentos pequenos sem acrescentar pixels nem preencher oclusões."""
import cv2,numpy as np
from contorno_multiescala_iris import margin_at_size
SPECS={'continuous':{'relative_area':0.,'opening_radius':0}}
for fraction in (.001,.005,.01,.02):
    SPECS[f'components_{fraction}']={'relative_area':fraction,'opening_radius':0}
SPECS['opening1']={'relative_area':0.,'opening_radius':1}
SPECS['components005_opening1']={'relative_area':.005,'opening_radius':1}


def filter_mask(mask,spec):
    result=np.asarray(mask,bool).copy()
    if spec['opening_radius']:
        radius=spec['opening_radius']
        kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1))
        result=cv2.morphologyEx(result.astype(np.uint8),cv2.MORPH_OPEN,kernel).astype(bool)&mask
    if spec['relative_area'] and result.any():
        n,labels,stats,_=cv2.connectedComponentsWithStats(result.astype(np.uint8),8)
        areas=stats[1:,cv2.CC_STAT_AREA];keep=np.zeros(n,bool)
        keep[1:]=areas>=max(1.,float(areas.max())*spec['relative_area'])
        result=keep[labels]
    assert not (result&~mask).any()
    return result


def predict_mask(model,photo,spec,clinical=False):
    margin,_=margin_at_size(model,photo,320,clinical)
    return filter_mask(margin>0,spec)
