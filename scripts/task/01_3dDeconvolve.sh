#!/bin/bash
#SBATCH --job-name="3dDeconvolve"
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=8gb
#SBATCH --time=48:00:00

module load afni/22.3.07
export AFNI_NIFTI_TYPE_WARN=NO

image_dir=$1
hrf_dir=$2
out_dir=$3
pipeline_version=v1-0

if [ -z "$image_dir" ] || [ -z "$hrf_dir" ] || [ -z "$out_dir" ]; then
    echo "Usage: $0 IMAGE_DIR HRF_DIR OUT_DIR"
    exit 1
fi

mkdir -p "$out_dir/stats" "$out_dir/corr_z"

run_3dDeconvolve() {
    task_full=$1
    emot_file="$image_dir/${task_full}_space-MNI152NLin6Asym_desc-prepped-${pipeline_version}_bold.nii.gz"

    echo "-------- Running $task_full --------"

    if [ -e "$out_dir/stats/${task_full}_bucket.nii.gz" ]; then
        echo "  Bucket already exists!"
    else
        3dDeconvolve -input "$emot_file" \
            -polort -1 -nfirst 0 -float -quiet \
            -num_stimts 5 \
            -stim_file 1 "$hrf_dir/HRF_Fear_515TRs.1D"       -stim_label 1 fear \
            -stim_file 2 "$hrf_dir/HRF_Neutral_515TRs.1D"    -stim_label 2 neutral \
            -stim_file 3 "$hrf_dir/HRF_Anger_515TRs.1D"      -stim_label 3 anger \
            -stim_file 4 "$hrf_dir/HRF_Surprise_515TRs.1D"   -stim_label 4 surprise \
            -stim_file 5 "$hrf_dir/HRF_Shape_515TRs.1D"      -stim_label 5 shapes \
            -gltsym 'SYM: +fear -shapes'            -glt_label 1 glt_fear \
            -gltsym 'SYM: +neutral -shapes'         -glt_label 2 glt_neutral \
            -gltsym 'SYM: +anger -shapes'           -glt_label 3 glt_anger \
            -gltsym 'SYM: +surprise -shapes'        -glt_label 4 glt_surprise \
            -gltsym 'SYM: +fear +anger -2*shapes'   -glt_label 5 glt_fear_p_anger \
            -gltsym 'SYM: +fear -neutral'           -glt_label 6 glt_fear_m_neutral \
            -gltsym 'SYM: +anger -neutral'          -glt_label 7 glt_anger_m_neutral \
            -gltsym 'SYM: +fear +anger -2*neutral'  -glt_label 8 glt_fear_p_anger_m_neutral \
            -gltsym 'SYM: +fear +neutral +anger +surprise -4*shapes' \
            -glt_label 9 glt_faces \
            -tout -rout -fout -noFDR \
            -x1D "$out_dir/stats/${task_full}_xmat.1D" \
            -x1D_stop

        3dREMLfit -input "$emot_file" \
            -matrix "$out_dir/stats/${task_full}_xmat.1D" \
            -tout -rout -fout -noFDR \
            -Rbuck "$out_dir/stats/${task_full}_bucket.nii.gz" \
            -Rerrts "$out_dir/stats/${task_full}_errts.nii.gz"
    fi

    # Export primary contrast.
    contrast=fear_p_anger
    a_index=40
    b_index=38
    echo "Computing Fisher's z-transform for ${contrast}: ${a_index} ${b_index}"

    3dcalc -overwrite \
        -a "$out_dir/stats/${task_full}_bucket.nii.gz[${a_index}]" \
        -b "$out_dir/stats/${task_full}_bucket.nii.gz[${b_index}]" \
        -expr 'ispositive(b)*sqrt(a)-isnegative(b)*sqrt(a)' \
        -prefix "$out_dir/corr_z/tmp_${task_full}_${contrast}.nii.gz"

    3dcalc -overwrite \
        -a "$out_dir/corr_z/tmp_${task_full}_${contrast}.nii.gz" \
        -expr 'atanh(a)' \
        -prefix "$out_dir/corr_z/${task_full}_${contrast}_Fz.nii.gz"

    rm -f "$out_dir/corr_z/tmp_${task_full}_${contrast}.nii.gz"
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

# Run 16 tasks in parallel.
for ((start=0; start<${#tasks[@]}; start+=16)); do
    for task_full in "${tasks[@]:start:16}"; do
        run_3dDeconvolve "$task_full" &
    done
    wait
done
wait
