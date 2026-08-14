import os
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests


if len(sys.argv) != 4:
    print('Usage: python 02_clin_corr.py CLINICAL_CSV ROI_SIGNALS_CSV OUTPUT_CSV')
    sys.exit(1)

clinical_path = sys.argv[1]
roi_path = sys.argv[2]
save_path = sys.argv[3]

covars = ['Age', 'Gender', 'Education', 'logDSL', 'HDRS-17']
vars = [
    'ICG-1 Yearning',
    'ICG-2 Anger',
    'ICG-6 Avoidance',
    'IES-R Intrusion',
    'UCLA Loneliness'
]
group_names = ['PGD', 'IG']


def run_glm(df, dv, iv, covars):
    if df.shape[0] == 0:
        return np.nan, np.nan
    dv = df[f'{dv}_z']
    iv = df[f'{iv}_z']
    covars = [f'{a}_z' for a in covars]
    dv_res = sm.GLM(
        dv, df[covars], family=sm.families.Gaussian()
    ).fit().resid_pearson
    iv_res = sm.GLM(
        iv, df[covars], family=sm.families.Gaussian()
    ).fit().resid_pearson
    r, p = stats.pearsonr(iv_res, dv_res)
    return r, p


# Standardize covariates before merging and subsetting.
df = pd.read_csv(clinical_path, low_memory=False)
if df['Gender'].dtype == object:
    df['Gender'] = df['Gender'].map({'F': 0, 'M': 1})
df['Group'] = df['Group'].replace({'csPG': 'PGD'})
df[[f'{a}_z' for a in covars]] = stats.zscore(df[covars], nan_policy='omit')

df_roi = pd.read_csv(roi_path)
roi_columns = [a for a in df_roi.columns if a != 'ID_long']
df = df.merge(df_roi, on='ID_long')

results = []
for col in roi_columns:
    # Standardize the brain signal in the full merged sample.
    df[f'{col}_z'] = stats.zscore(df[col], nan_policy='omit')

    for var in vars:
        complete = (~pd.isna(df[var])) & (np.sum(pd.isna(df[covars]), axis=1) == 0)
        df_var = df.loc[complete, :].reset_index(drop=True).copy()
        df_var[f'{var}_z'] = stats.zscore(df_var[var])

        r, p = run_glm(df_var, var, col, covars)
        results.append({
            'Group': 'All',
            'Variable': var,
            'ROI': col,
            'N': df_var.shape[0],
            'r': r,
            'p_raw': p
        })

        for group in group_names:
            df_group = df_var.loc[df_var['Group'] == group].reset_index(drop=True)
            r, p = run_glm(df_group, var, col, covars)
            results.append({
                'Group': group,
                'Variable': var,
                'ROI': col,
                'N': df_group.shape[0],
                'r': r,
                'p_raw': p
            })

df_results = pd.DataFrame(results)
df_results['p_FDR'] = np.nan
for group in ['All'] + group_names:
    group_i = df_results['Group'] == group
    _, p_adj, _, _ = multipletests(
        df_results.loc[group_i, 'p_raw'], method='fdr_bh'
    )
    df_results.loc[group_i, 'p_FDR'] = p_adj

os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
df_results.to_csv(save_path, index=False)
print('Saved to', save_path)
