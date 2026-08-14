import os
import sys
import pandas as pd
import nibabel as nib
from scipy import stats
from nilearn import image


if len(sys.argv) != 5:
    print(
        'Usage: python 03_threshold_ttest.py '
        'STAT_MAP CLUSTSIM_CSV MASK OUTPUT'
    )
    sys.exit(1)

img_path = sys.argv[1]
clustsim_path = sys.argv[2]
mask_path = sys.argv[3]
save_path = sys.argv[4]

p_threshold = 0.005
z_threshold = round(stats.norm.ppf(1 - p_threshold / 2), 3)
alpha_column = '.05000'

csim_results = pd.read_csv(clustsim_path, low_memory=False)
cluster_threshold = csim_results.loc[
    csim_results['p'] == p_threshold, alpha_column
].values[0]

img_afni = nib.load(img_path)
img_np = img_afni.get_fdata()
mask_np = nib.load(mask_path).get_fdata()
img_np[mask_np == 0] = 0

img_thresholded = image.threshold_img(
    nib.Nifti1Image(img_np, img_afni.affine),
    z_threshold,
    cluster_threshold=cluster_threshold
)

os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
nib.save(img_thresholded, save_path)
print(f'Cluster size = {cluster_threshold}')
print(f'Saved to {save_path}')
