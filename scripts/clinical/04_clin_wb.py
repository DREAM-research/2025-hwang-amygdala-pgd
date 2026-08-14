import os
import sys
import glob
import numpy as np
import pandas as pd
import nibabel as nib
import statsmodels.api as sm
from scipy import stats
from nilearn import image


if len(sys.argv) != 7:
    print(
        'Usage: python 04_clin_wb.py '
        'CLINICAL_CSV IMAGE_DIR IMAGE_SUFFIX GM_MASK CLUSTSIM_TXT OUT_PATH'
    )
    sys.exit(1)

clinical_path = sys.argv[1]
img_path = sys.argv[2]
img_path_suffix = sys.argv[3]
mask_path = sys.argv[4]
clustsim_path = sys.argv[5]
out_path = sys.argv[6]

covars = ['Age', 'Gender', 'Education', 'logDSL', 'HDRS-17']
vars = [
    'ICG-1 Yearning',
    'ICG-2 Anger',
    'ICG-6 Avoidance',
    'IES-R Intrusion',
    'UCLA Loneliness'
]


def run_glm(dv, iv, covars):
    dv_res = sm.GLM(
        dv, covars, family=sm.families.Gaussian()
    ).fit().resid_pearson
    iv_res = sm.GLM(
        iv, covars, family=sm.families.Gaussian()
    ).fit().resid_pearson
    r, p = stats.pearsonr(iv_res, dv_res)
    return r, -np.log10(p)


df_all = pd.read_csv(clinical_path, low_memory=False)
if df_all['Gender'].dtype == object:
    df_all['Gender'] = df_all['Gender'].map({'F': 0, 'M': 1})
df_all['Group'] = df_all['Group'].replace({'csPG': 'PGD'})
df_all = df_all.loc[df_all['Group'] == 'PGD', :].reset_index(drop=True)

img_mask = nib.load(mask_path)
mask_np = img_mask.get_fdata()
os.makedirs(out_path, exist_ok=True)

for var in vars:
    # Complete cases for each symptom.
    df = df_all.loc[~pd.isna(df_all[var]), :].reset_index(drop=True).copy()
    print(var, 'n =', df.shape[0])

    img_paths = []
    for id_long in df['ID_long']:
        matches = glob.glob(f'{img_path}/{id_long}_{img_path_suffix}')
        if len(matches) != 1:
            raise RuntimeError(
                f'Expected one image for {id_long}, found {len(matches)}'
            )
        img_paths.append(matches[0])

    first_img = nib.load(img_paths[0])
    img_shape = first_img.shape[:3]
    img_all = np.zeros((*img_shape, df.shape[0]))
    for i, img_path_full in enumerate(img_paths):
        img_all[:, :, :, i] = nib.load(img_path_full).get_fdata()

    df[[f'{a}_z' for a in covars + [var]]] = stats.zscore(
        df[covars + [var]], nan_policy='omit'
    )
    r_img_np = np.zeros(img_shape)
    p_img_np = np.zeros(img_shape)

    for ix in range(img_shape[0]):
        print(f'{ix + 1}/{img_shape[0]}')
        for iy in range(img_shape[1]):
            for iz in range(img_shape[2]):
                if mask_np[ix, iy, iz] == 0:
                    continue
                if (
                    np.min(img_all[ix, iy, iz, :]) == 0
                    and np.max(img_all[ix, iy, iz, :]) == 0
                ):
                    r_img_np[ix, iy, iz], p_img_np[ix, iy, iz] = 0, 0
                else:
                    r_img_np[ix, iy, iz], p_img_np[ix, iy, iz] = run_glm(
                        stats.zscore(df[f'{var}_z']),
                        img_all[ix, iy, iz, :],
                        df[[f'{a}_z' for a in covars]]
                    )

    var_label = var.replace(' ', '_').replace('/', '-')
    prefix = f'{out_path}/{var_label}_n{df.shape[0]}'
    r_img = nib.Nifti1Image(r_img_np, first_img.affine)
    p_img = nib.Nifti1Image(p_img_np, first_img.affine)
    nib.save(r_img, f'{prefix}_r.nii.gz')
    nib.save(p_img, f'{prefix}_p.nii.gz')

    # p=0.005, alpha=0.05
    cluster_threshold = np.ceil(np.loadtxt(clustsim_path)[-13][2])
    p_thresholded = image.threshold_img(
        p_img,
        -np.log10(0.005),
        cluster_threshold=cluster_threshold
    )
    p_thresholded_np = p_thresholded.get_fdata()
    r_thresholded_np = r_img_np.copy()
    r_thresholded_np[p_thresholded_np == 0] = 0
    nib.save(
        nib.Nifti1Image(r_thresholded_np, first_img.affine),
        f'{prefix}_r_wb_005_05.nii.gz'
    )
    print('Cluster size =', cluster_threshold)
