import os
import sys
import glob
import numpy as np
import nibabel as nib
from nilearn import masking


if len(sys.argv) != 5:
    print(
        'Usage: python 01_prepare_gPPI.py '
        'IMAGE_DIR SEED_MASK HRF_DIR OUT_PATH'
    )
    sys.exit(1)

image_dir = sys.argv[1]
seed_path = sys.argv[2]
hrf_dir = sys.argv[3]
out_path = sys.argv[4]
seed_label = 'amygR'

if not os.path.exists(seed_path):
    print(seed_path, 'is not there!')
    sys.exit(1)

img_seed = nib.load(seed_path)
os.makedirs(out_path, exist_ok=True)

# Interaction terms for 02_run_gPPI.sh
contrasts = ['Neutral', 'Surprise', 'Shape', 'Fear_p_Anger']
img_paths = sorted(glob.glob(f'{image_dir}/sub-*_task-emot_*prepped-v1-0_bold.nii.gz'))

if len(img_paths) == 0:
    print('No task images found in', image_dir)
    sys.exit(1)

for img_path in img_paths:
    task_full = '_'.join(os.path.basename(img_path).split('_')[:4])
    print(task_full)
    img = nib.load(img_path)

    path_1d = f'{out_path}/{task_full}_{seed_label}.1D'
    if os.path.exists(path_1d):
        signal = np.loadtxt(path_1d)
    else:
        signal = np.mean(masking.apply_mask(img, img_seed), axis=-1)
        np.savetxt(path_1d, signal)

    for contrast in contrasts:
        interaction_path = path_1d.replace('.1D', f'x{contrast}.1D')
        if os.path.exists(interaction_path):
            continue
        hrf = np.loadtxt(f'{hrf_dir}/HRF_{contrast}_515TRs.1D')
        np.savetxt(interaction_path, signal * hrf)
