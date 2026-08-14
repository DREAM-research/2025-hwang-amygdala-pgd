import os
import sys
import glob
import numpy as np
import nibabel as nib
from scipy import stats
from nilearn import masking


if len(sys.argv) != 5:
    print('Usage: python 01_corr_wb.py IMAGE_DIR SEED_MASK GM_MASK OUT_PATH')
    sys.exit(1)

image_dir = sys.argv[1]
roi_path = sys.argv[2]
mask_path = sys.argv[3]
out_path = sys.argv[4]

img_roi = nib.load(roi_path)
img_roi_np = img_roi.get_fdata()
img_mask_np = nib.load(mask_path).get_fdata()
os.makedirs(out_path, exist_ok=True)

img_paths = sorted(glob.glob(f'{image_dir}/sub-*_task-rest_*prepped-v1-0_bold.nii.gz'))
if len(img_paths) == 0:
    print('No resting-state images found in', image_dir)
    sys.exit(1)

for img_path in img_paths:
    img_name = '_'.join(os.path.basename(img_path).split('_')[:4])
    out_path_full = f'{out_path}/{img_name}_corr_z.nii.gz'
    print(img_name)
    if os.path.exists(out_path_full):
        continue

    img = nib.load(img_path)
    img_np = img.get_fdata()
    img_corr = np.zeros(img_np.shape[:3])
    roi_signal = np.average(masking.apply_mask(img, img_roi), axis=1)

    for ix in range(img_np.shape[0]):
        for iy in range(img_np.shape[1]):
            for iz in range(img_np.shape[2]):
                # Skip if outside mask.
                if img_mask_np[ix, iy, iz] == 0:
                    continue
                # Skip if all zero.
                if np.sum(img_np[ix, iy, iz, :] == 0) == len(img_np[ix, iy, iz, :]):
                    img_corr[ix, iy, iz] = 0
                    continue
                # Skip the seed itself.
                if img_roi_np[ix, iy, iz] != 0:
                    img_corr[ix, iy, iz] = 0
                    continue

                r, _ = stats.pearsonr(roi_signal, img_np[ix, iy, iz, :])
                img_corr[ix, iy, iz] = 0.5 * np.log((1 + r) / (1 - r))
                if np.isnan(img_corr[ix, iy, iz]):
                    print('Correlation failed at', [ix, iy, iz])
                    sys.exit(1)

    nib.save(nib.Nifti1Image(img_corr, img_roi.affine), out_path_full)
