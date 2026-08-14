# Amygdala-Centered Emotional Processing in Prolonged Grief Disorder

Hwang G, Blair NP, Ward BD, et al. Amygdala-centered emotional processing in
prolonged grief disorder: Relationship with clinical symptomatology. *Biol
Psychiatry Cogn Neurosci Neuroimaging.* 2025;10(12):1284–1293.
<https://doi.org/10.1016/j.bpsc.2024.12.008>

## Scripts

- `scripts/task/`: task activation and group analysis
- `scripts/gppi/`: task-dependent connectivity
- `scripts/rest_proc/`: resting-state connectivity
- `scripts/clinical/`: ROI and voxelwise clinical analyses

## Environment

Python 3.9 and AFNI 22.3.07.

```bash
python3.9 -m venv .env_task
source .env_task/bin/activate
pip install -r requirements.txt
```

No study data are included. Paths are supplied as script arguments.
