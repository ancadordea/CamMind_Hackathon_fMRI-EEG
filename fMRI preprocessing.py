import os
import glob
import gzip
import shutil
import json  
import nibabel as nib
from nipype.interfaces.spm import NewSegment, Normalize12, SliceTiming, Realign, Smooth
from nipype.interfaces.matlab import MatlabCommand
from nipype import Node

# Set SPM path
MatlabCommand.set_default_paths('/Users/Admin/spm')  #CHANGE SPM path
MatlabCommand.set_default_matlab_cmd("/Applications/MATLAB_R2024b.app/bin/matlab -nodisplay -nosplash")


# ============
# ANATOMICAL
# ============

print("Start ANAT preprocessing")

base_dir = "/Users/Admin/Documents/CamMind-pink-purple-team/daly_2019"  #CHANGE
subject_dirs = sorted(glob.glob(os.path.join(base_dir, 'sub*')))

for subj_dir in subject_dirs:
    print(f"Processing {subj_dir} (ANAT)...") #change to subject directory
    
    anat_dir = os.path.join(subj_dir, 'anat')
    nii_gz_files = glob.glob(os.path.join(anat_dir, '*.nii.gz'))
    
    if not nii_gz_files:
        print(f"No NIFTI GZ file found for {subj_dir}. Skipping...")
        continue
    
    nii_gz_file = nii_gz_files[0]
    nii_file = nii_gz_file[:-3]  #removes .gz file

    # Unzip if needed
    if not os.path.exists(nii_file):
        with gzip.open(nii_gz_file, 'rb') as f_in:
            with open(nii_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"Unzipped {nii_gz_file} to {nii_file}")

    # Segmentation
    seg = Node(NewSegment(), name=f"seg_{os.path.basename(subj_dir)}")
    seg.inputs.channel_files = nii_file
    seg.inputs.channel_info = (0.001, 60, (True, True))
    seg.inputs.write_deformation_fields = [True, True]
    seg_res = seg.run()

    # Normalization
    deformation_field = os.path.join(anat_dir, 'y_' + os.path.basename(nii_file))
    if not os.path.exists(deformation_field):
        print(f"Deformation field {deformation_field} not found for {subj_dir}. Skipping normalization...")
        continue

    norm = Node(Normalize12(), name=f"norm_{os.path.basename(subj_dir)}")
    norm.inputs.image_to_align = nii_file
    norm.inputs.deformation_file = deformation_field
    norm.inputs.jobtype = 'write'
    norm.inputs.write_voxel_sizes = [1, 1, 1]
    norm.run()

print("Done with all anatomical preprocessing!")

# ============
# FUNCTIONAL
# ============

print("Start FUNC preprocessing")

for subj_dir in subject_dirs:
    print(f"Processing {subj_dir} (FUNC)...")

    func_dir = os.path.join(subj_dir, 'func')
    func_files = sorted(glob.glob(os.path.join(func_dir, '*_bold.nii.gz')))

    if not func_files:
        print(f"No functional NIFTI GZ files found for {subj_dir}. Skipping...")
        continue

    for func_gz in func_files:
        print(f"Processing {func_gz}...")

        func_nii = func_gz[:-3]  #gives the .nii name without .gz

        # Unzip if needed
        if not os.path.exists(func_nii):
            with gzip.open(func_gz, 'rb') as f_in:
                with open(func_nii, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            print(f"Unzipped {func_gz} to {func_nii}")

        # --- Read TR from BIDS JSON ---
        json_file = func_nii.replace('.nii', '.json')
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                metadata = json.load(f)
                TR = metadata.get('RepetitionTime', 2.0)
        else:
            print(f"Warning: JSON metadata file not found for {func_nii}. Using default TR=2.0")
            TR = 2.0

        # Load functional image
        img = nib.load(func_nii)
        num_slices = img.shape[2]  # Z dimension

        # Step 1: Slice Timing Correction
        st = Node(SliceTiming(), name=f"st_{os.path.basename(func_nii)}")
        st.inputs.in_files = func_nii
        st.inputs.num_slices = num_slices
        st.inputs.time_repetition = TR
        st.inputs.time_acquisition = TR - (TR / num_slices)
        st.inputs.slice_order = list(range(1, num_slices + 1))  # sequential slice order
        st.inputs.ref_slice = int(num_slices / 2)
        st_res = st.run()

        # Step 2: Realignment
        realign = Node(Realign(), name=f"realign_{os.path.basename(func_nii)}")
        realign.inputs.in_files = st_res.outputs.timecorrected_files
        realign.inputs.register_to_mean = True
        realign_res = realign.run()

        # Step 3: Normalization
        norm = Node(Normalize12(), name=f"norm_{os.path.basename(func_nii)}")
        norm.inputs.image_to_align = realign_res.outputs.mean_image
        norm.inputs.apply_to_files = realign_res.outputs.realigned_files
        norm.inputs.write_voxel_sizes = [2, 2, 2]
        norm_res = norm.run()

        # Step 4: Smoothing
        smooth = Node(Smooth(), name=f"smooth_{os.path.basename(func_nii)}")
        smooth.inputs.in_files = norm_res.outputs.normalized_files
        smooth.inputs.fwhm = [6, 6, 6]
        smooth.run()

print("Done with all functional preprocessing!")
