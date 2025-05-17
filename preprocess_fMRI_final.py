#!/usr/bin/env python3
import os
import glob
import subprocess
import numpy as np
from nilearn import image, masking, datasets

# USER SETTINGS
data_dir   = '/rds/user/rl574/hpc-work/CamMIND/data/daly_2019'
output_dir = '/rds/user/rl574/hpc-work/CamMIND/data/preprocessed'
if not os.path.exists(output_dir):
    os.makedirs(output_dir, exist_ok=True)

# FSL MNI template (ensure $FSLDIR is set)
fsl_mni = os.path.join(os.environ.get('FSLDIR', ''), 'data/standard/MNI152_T1_2mm.nii.gz')

# 1. Build ROI masks once
print('Building ROI masks')
subcort = datasets.fetch_atlas_harvard_oxford('sub-maxprob-thr25-2mm')
cort    = datasets.fetch_atlas_harvard_oxford('cort-maxprob-thr25-2mm')

REGION_LABELS = {
    'amygdala': ['Left Amygdala', 'Right Amygdala']
}

mask_dir = os.path.join(output_dir, 'masks')
if not os.path.exists(mask_dir):
    os.makedirs(mask_dir, exist_ok=True)

sub_img  = image.load_img(subcort.maps)
cort_img = image.load_img(cort.maps)
sub_lbls = [lbl.strip() for lbl in subcort.labels]
cort_lbls= [lbl.strip() for lbl in cort.labels]

i_nifti_masks = {}
for region, names in REGION_LABELS.items():
    atlas_img  = sub_img
    atlas_lbls = sub_lbls
    mask_img   = None
    for name in names:
        if name not in atlas_lbls:
            raise ValueError(f"Label '{name}' not found: {atlas_lbls}")
        idx = atlas_lbls.index(name)
        code = idx
        this_m = image.math_img(f"img == {code}", img=atlas_img)
        mask_img = this_m if mask_img is None else image.math_img(
            'img1 | img2', img1=mask_img, img2=this_m)
    # Ensure binary mask (0/1)
    mask_img = image.math_img('img > 0.5', img=mask_img)
    out_mask = os.path.join(mask_dir, f"{region}_mask_mni.nii.gz")
    if not os.path.exists(out_mask):
        mask_img.to_filename(out_mask)
    i_nifti_masks[region] = out_mask
    print(f"Saved binary MNI mask {region}: {out_mask}")

# 2. Subjects list Subjects list
subjects = sorted(['sub-01','sub-02','sub-03','sub-04','sub-05'])
print('Subjects:', subjects)

# 3. Process each subject/run
for subj in subjects:
    anat = os.path.join(data_dir, subj, 'anat', f'{subj}_T1w.nii.gz')
    funcs = sorted(glob.glob(os.path.join(data_dir, subj, 'func', f'{subj}_task-genMusic*_bold.nii.gz')))
    if not funcs:
        print(f"No bold runs for {subj}, skipping")
        continue
    for func in funcs:
        run = os.path.basename(func).replace('.nii.gz','')
        out_sub = os.path.join(output_dir, subj, run)
        if not os.path.exists(out_sub):
            os.makedirs(out_sub, exist_ok=True)
        print(f"Processing {subj} {run}")

        # Motion correction
        func_mc = os.path.join(out_sub, 'func_mc.nii.gz')
        if not os.path.exists(func_mc):
            try:
                subprocess.run([
                    'mcflirt', '-in', func, '-out', func_mc,
                    '-plots', '-refvol', '0'
                ], check=True)
                print('  Motion correction done')
            except subprocess.CalledProcessError:
                print(f"  WARNING: mcflirt failed on {run}, skipping")
                continue
        else:
            print('  Skipping motion correction, exists')

        # Extract reference volume for registration
        ref_vol = os.path.join(out_sub, 'func_mc_ref.nii.gz')
        if not os.path.exists(ref_vol):
            subprocess.run(['fslroi', func_mc, ref_vol, '0', '1'], check=True)
            print('  Extracted reference volume')
        else:
            print('  Skipping ref volume extraction, exists')

        # T1 to MNI
        anat2mni = os.path.join(out_sub, 'anat2mni.mat')
        anat_mni = os.path.join(out_sub, 'anat_mni.nii.gz')
        if not os.path.exists(anat2mni) or not os.path.exists(anat_mni):
            subprocess.run([
                'flirt', '-in', anat, '-ref', fsl_mni,
                '-omat', anat2mni, '-out', anat_mni
            ], check=True)
            print('  T1 to MNI done')
        else:
            print('  Skipping T1 to MNI, exists')

        # Register reference volume to T1
        func2anat = os.path.join(out_sub, 'func2anat.mat')
        func2anat_img = os.path.join(out_sub, 'func2anat_ref.nii.gz')
        if not os.path.exists(func2anat) or not os.path.exists(func2anat_img):
            subprocess.run([
                'flirt', '-in', ref_vol, '-ref', anat,
                '-omat', func2anat, '-out', func2anat_img
            ], check=True)
            print('  Ref vol to T1 done')
        else:
            print('  Skipping ref->T1, exists')

        # Concatenate and warp entire func_mc to MNI
        func2mni = os.path.join(out_sub, 'func2mni.mat')
        func_mni = os.path.join(out_sub, 'func_mni.nii.gz')
        if not os.path.exists(func2mni):
            subprocess.run([
                'convert_xfm', '-concat', anat2mni, func2anat, '-omat', func2mni
            ], check=True)
            print('  Concatenated transforms')
        else:
            print('  Skipping transform concat, exists')
        if not os.path.exists(func_mni):
            subprocess.run([
                'flirt', '-in', func_mc, '-ref', fsl_mni,
                '-applyxfm', '-init', func2mni, '-out', func_mni
            ], check=True)
            print('  Warped func to MNI')
        else:
            print('  Skipping func->MNI warp, exists')

        # Smooth
        func_s = os.path.join(out_sub, 'func_mni_smooth.nii.gz')
        if not os.path.exists(func_s):
            subprocess.run(['fslmaths', func_mni, '-s', '2', func_s], check=True)
            print('  Smoothing done')
        else:
            print('  Skipping smoothing, exists')

                        # Warp MNI masks back to native func space
        native_masks = {}
        for region, mni_mask in i_nifti_masks.items():
            native_mask = os.path.join(out_sub, f"{region}_mask_native.nii.gz")
            if not os.path.exists(native_mask):
                # First invert the func2mni transform
                inv_xfm = os.path.join(out_sub, f"{region}_func2mni_inv.mat")
                subprocess.run([
                    'convert_xfm', '-omat', inv_xfm,
                    '-inverse', func2mni
                ], check=True)
                # Then apply the inverted transform to the mask
                subprocess.run([
                    'flirt', '-in', mni_mask,
                    '-ref', func_mc,
                    '-applyxfm', '-init', inv_xfm,
                    '-out', native_mask
                ], check=True)
                # Ensure binary mask (threshold and binarize)
                subprocess.run([
                    'fslmaths', native_mask,
                    '-thr', '0.5', '-bin', native_mask
                ], check=True)
                print(f"  Warped and binarized {region} mask to native space")
            else:
                print(f"  Skipping warp {region}, native mask exists")
            native_masks[region] = native_mask

        # Extract time series"}]}
        func_img = image.load_img(func_mc)
        for region, mask_native in native_masks.items():
            ts_file = os.path.join(out_sub, f"{region}_ts.txt")
            if not os.path.exists(ts_file):
                # Load and enforce binary mask in Python
                mask_img = image.load_img(mask_native)
                mask_bin = image.math_img('img > 0.5', img=mask_img)
                # Apply mask and extract mean time series
                ts = masking.apply_mask(func_img, mask_bin).mean(axis=1)
                np.savetxt(ts_file, ts, fmt='%.6f')
                print(f"  Extracted ts for {region}")
            else:
                print(f"  Skipping extract {region}, exists")

print('All done')
