#!/bin/bash
#SBATCH --job-name="3dttest2_clustsim"
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=8gb
#SBATCH --time=48:00:00

module load afni/22.3.07

data_path=$1
covariates_file=$2
mask_path=$3
mask_label=$4
out_path=$5
g1=cs
g2=ig
contrast=fear_p_anger
g1_upper=CS
g2_upper=IG

if [ -z "$data_path" ] || [ -z "$covariates_file" ] || \
   [ -z "$mask_path" ] || [ -z "$mask_label" ] || [ -z "$out_path" ]; then
    echo "Usage: $0 DATA_PATH COVARIATES_FILE MASK MASK_LABEL OUT_PATH"
    exit 1
fi

case "$data_path" in /*) ;; *) data_path="$PWD/$data_path" ;; esac
case "$covariates_file" in /*) ;; *) covariates_file="$PWD/$covariates_file" ;; esac
case "$mask_path" in /*) ;; *) mask_path="$PWD/$mask_path" ;; esac
case "$out_path" in /*) ;; *) out_path="$PWD/$out_path" ;; esac

mkdir -p "$out_path"
shopt -s nullglob

file_list1=("$data_path"/sub-*-${g1}_*_run-??_${contrast}_Fz.nii.gz)
file_list2=("$data_path"/sub-*-${g2}_*_run-??_${contrast}_Fz.nii.gz)
n1=${#file_list1[@]}
n2=${#file_list2[@]}

if [ "$n1" -eq 0 ] || [ "$n2" -eq 0 ]; then
    echo "No input maps found: ${g1}=${n1}, ${g2}=${n2}"
    exit 1
fi

set_args1=()
for file in "${file_list1[@]}"; do
    subject=$(basename "$file" | cut -d '_' -f 1)
    set_args1+=("$subject" "$file")
done

set_args2=()
for file in "${file_list2[@]}"; do
    subject=$(basename "$file" | cut -d '_' -f 1)
    set_args2+=("$subject" "$file")
done

prefix="${contrast}_${g1_upper}${n1}-${g2_upper}${n2}"
(
    cd "$out_path" || exit 1
    3dttest++ -mask "$mask_path" \
        -Clustsim \
        -prefix "./${prefix}.nii.gz" \
        -prefix_clustsim "./${prefix}_${mask_label}" \
        -nomeans -toz -nocov -no1sam \
        -covariates "$covariates_file" \
        -setA "$g1_upper" "${set_args1[@]}" \
        -setB "$g2_upper" "${set_args2[@]}"
)
