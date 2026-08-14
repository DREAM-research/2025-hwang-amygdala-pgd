import os
import sys
import glob
import numpy as np
import pandas as pd
import nibabel as nib
from nilearn import masking


if len(sys.argv) != 7:
    print(
        'Usage: python 01_extract_roi_signals.py '
        'CLINICAL_CSV IMAGE_DIR IMAGE_SUFFIX MASK SIGNAL_LABEL OUTPUT_CSV'
    )
    sys.exit(1)

clinical_path = sys.argv[1]
img_path = sys.argv[2]
img_path_suffix = sys.argv[3]
mask_path = sys.argv[4]
signal_label = sys.argv[5]
save_path = sys.argv[6]

df = pd.read_csv(clinical_path)
df_roi = df[['ID_long']].copy()
img_mask = nib.load(mask_path)

for i, id_long in enumerate(df['ID_long']):
    img_paths = glob.glob(f'{img_path}/{id_long}_{img_path_suffix}')
    if len(img_paths) != 1:
        raise RuntimeError(
            f'Expected one image for {id_long}, found {len(img_paths)}'
        )
    img = nib.load(img_paths[0])
    df_roi.loc[i, signal_label] = np.mean(masking.apply_mask(img, img_mask))

os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
df_roi.to_csv(save_path, index=False)
print('Saved to', save_path)
