#!/bin/bash
#SBATCH --job-name="3dClustSim"
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=8gb
#SBATCH --time=48:00:00

# ACF estimation for exploratory symptom maps.

module load afni/22.3.07
export AFNI_NIFTI_TYPE_WARN=NO

stats_dir=$1
smoothness_mask=$2
inference_mask=$3
mask_label=$4
out_dir=$5

if [ -z "$stats_dir" ] || [ -z "$smoothness_mask" ] || \
   [ -z "$inference_mask" ] || [ -z "$mask_label" ] || [ -z "$out_dir" ]; then
    echo "Usage: $0 STATS_DIR SMOOTHNESS_MASK INFERENCE_MASK MASK_LABEL OUT_DIR"
    exit 1
fi

mkdir -p "$out_dir/acf"
summary_file="$out_dir/acf/ACF_${mask_label}.1D"
rm -f "$summary_file"

shopt -s nullglob
errts_files=("$stats_dir"/sub*_errts.nii.gz)
if [ ${#errts_files[@]} -eq 0 ]; then
    echo "No residual files found in $stats_dir"
    exit 1
fi

run_3dFWHMx() {
    errts_file=$1
    task=$(basename "$errts_file" _errts.nii.gz)
    acf_file="$out_dir/acf/${task}_ACF_${mask_label}.1D"
    if [ ! -e "$acf_file" ]; then
        3dFWHMx -acf NULL \
            -input "$errts_file" \
            -mask "$smoothness_mask" \
            >> "$acf_file"
    fi
}

for ((start=0; start<${#errts_files[@]}; start+=16)); do
    for errts_file in "${errts_files[@]:start:16}"; do
        run_3dFWHMx "$errts_file" &
    done
    wait
done
wait

for errts_file in "${errts_files[@]}"; do
    task=$(basename "$errts_file" _errts.nii.gz)
    acf_file="$out_dir/acf/${task}_ACF_${mask_label}.1D"
    ACF=$(sed '2q;d' "$acf_file")
    echo "$task $ACF" >> "$summary_file"
done

acf_a=$(awk '{ total += $2 } END { print total/NR }' "$summary_file")
acf_b=$(awk '{ total += $3 } END { print total/NR }' "$summary_file")
acf_c=$(awk '{ total += $4 } END { print total/NR }' "$summary_file")
echo "$acf_a $acf_b $acf_c"

3dClustSim -acf "$acf_a" "$acf_b" "$acf_c" \
    -pthr 0.05 0.01 0.005 0.001 0.0001 \
    -athr 0.1 0.05 0.01 0.005 0.001 0.0001 \
    -mask "$inference_mask" \
    -iter 10000 > "$out_dir/ClustSim_${mask_label}.txt"
