#!/bin/bash
#SBATCH --job-name="gPPI"
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=8gb
#SBATCH --time=48:00:00

module load afni/22.3.07
export AFNI_NIFTI_TYPE_WARN=NO

image_dir=$1
hrf_dir=$2
gppi_dir=$3
out_dir=$4
seed=amygR
pipeline_version=v1-0

if [ -z "$image_dir" ] || [ -z "$hrf_dir" ] || [ -z "$gppi_dir" ] || \
   [ -z "$out_dir" ]; then
    echo "Usage: $0 IMAGE_DIR HRF_DIR GPPI_DIR OUT_DIR"
    exit 1
fi

mkdir -p "$out_dir/stats/$seed" "$out_dir/corr_z/$seed"

run_3dDeconvolve() {
    task_full=$1
    emot_file="$image_dir/${task_full}_space-MNI152NLin6Asym_desc-prepped-${pipeline_version}_bold.nii.gz"

    echo "-------- Running $task_full --------"

    if [ -e "$out_dir/stats/${seed}/${task_full}_bucket.nii.gz" ]; then
        echo "  Bucket already exists!"
    else
        3dDeconvolve -input "$emot_file" \
            -polort -1 -nfirst 0 -float -quiet \
            -num_stimts 9 \
            -stim_file 1 "$hrf_dir/HRF_Fear_p_Anger_515TRs.1D" \
                -stim_label 1 fear_p_anger \
            -stim_file 2 "$hrf_dir/HRF_Neutral_515TRs.1D" \
                -stim_label 2 neutral \
            -stim_file 3 "$hrf_dir/HRF_Surprise_515TRs.1D" \
                -stim_label 3 surprise \
            -stim_file 4 "$hrf_dir/HRF_Shape_515TRs.1D" \
                -stim_label 4 shapes \
            -stim_file 5 "$gppi_dir/${task_full}_${seed}.1D" \
                -stim_label 5 seed \
            -stim_file 6 "$gppi_dir/${task_full}_${seed}xFear_p_Anger.1D" \
                -stim_label 6 fear_p_angerPPI \
            -stim_file 7 "$gppi_dir/${task_full}_${seed}xNeutral.1D" \
                -stim_label 7 neutralPPI \
            -stim_file 8 "$gppi_dir/${task_full}_${seed}xSurprise.1D" \
                -stim_label 8 surprisePPI \
            -stim_file 9 "$gppi_dir/${task_full}_${seed}xShape.1D" \
                -stim_label 9 shapesPPI \
            -tout -rout -fout -noFDR \
            -x1D "$out_dir/stats/${seed}/${task_full}_xmat.1D" \
            -bucket "$out_dir/stats/${seed}/${task_full}_bucket.nii.gz"
    fi

    # PPI sub-bricks: coefficient 22, R2 24.
    contrast=fear_p_angerPPI
    a_index=24
    b_index=22

    3dcalc -overwrite \
        -a "$out_dir/stats/${seed}/${task_full}_bucket.nii.gz[${a_index}]" \
        -b "$out_dir/stats/${seed}/${task_full}_bucket.nii.gz[${b_index}]" \
        -expr 'ispositive(b)*sqrt(a)-isnegative(b)*sqrt(a)' \
        -prefix "$out_dir/corr_z/${seed}/tmp_${task_full}_${contrast}.nii.gz"

    3dcalc -overwrite \
        -a "$out_dir/corr_z/${seed}/tmp_${task_full}_${contrast}.nii.gz" \
        -expr 'atanh(a)' \
        -prefix "$out_dir/corr_z/${seed}/${task_full}_${contrast}_Fz.nii.gz"

    rm -f "$out_dir/corr_z/${seed}/tmp_${task_full}_${contrast}.nii.gz"
}

shopt -s nullglob
images=("$image_dir"/sub-*_task-emot_*prepped-"$pipeline_version"_bold.nii.gz)
if [ ${#images[@]} -eq 0 ]; then
    echo "No task images found in $image_dir"
    exit 1
fi

tasks=()
for image_path in "${images[@]}"; do
    image_name=$(basename "$image_path")
    tasks+=("${image_name%%_space-*}")
done

for ((start=0; start<${#tasks[@]}; start+=16)); do
    for task_full in "${tasks[@]:start:16}"; do
        run_3dDeconvolve "$task_full" &
    done
    wait
done
wait
