import pandas as pd
import numpy as np
from sklearn.metrics import make_scorer

def optimize_ppv_npv(y_true, y_predict_proba):
    ppv_list = []
    npv_list = []
    min_ppv_npv_list = []
    for th in np.linspace(0, 1, 100):
        y_predict = 1 * (y_predict_proba > th)
        tn, fp, fn, tp = confusion_matrix(y_true, y_predict).ravel()
        ppv = tp / (tp + fp) 
        npv = tn / (fn + tn)
        min_ppv_npv = np.nanmin(np.array(ppv, npv))
#         ppv_list.append(ppv)
#         npv_list.append(npv)
        min_ppv_npv_list.append(min_ppv_npv)
    return np.nanmax(np.array(min_ppv_npv_list))

optimize_ppv_npv_scorer = make_scorer(optimize_ppv_npv, greater_is_better=True)