"""Um limiar global calibrado em dominios internos predefinidos."""
import numpy as np
from avaliar_robustez_reconhecimento import operating_threshold

def calibrate_robust(internal,target=.005):
    if set(internal)!={'clean','upper10','lower10'}:raise ValueError('Exactly three predefined INTERNAL domains required')
    thresholds={}
    for tag,data in internal.items():
        scores=np.asarray(data['scores'],np.float64);labels=data['labels'];valid=data['valid'];mask=np.ones_like(scores,bool);mask[np.arange(len(scores)),labels]=False
        values=scores[mask&valid[:,None]&(scores>-2)]
        if not len(values):raise ValueError('No valid internal impostors')
        thresholds[tag]=operating_threshold(values,target)
    return max(thresholds.values()),thresholds
