import numpy as np
from sklearn.decomposition import FastICA
import nibabel as nib
from nilearn import plotting

# 1. Load your fMRI mask (same grid / source‐space affine as stc)
mask_nii   = nib.load('myContrast_mask.nii')
mask_data  = mask_nii.get_fdata().astype(bool).ravel()  # flatten to 1D
                                                                 
# 2. Prepare your source‐space EEG data                             
#    `stc.data` is (n_sources, n_times)
X = stc.data.T        # now shape = (n_times, n_sources)

# 3. Fit spatial ICA                                              
n_components = 20     # or choose via explained-variance / cross-validation
ica = FastICA(n_components=n_components, random_state=0)
S   = ica.fit_transform(X)      # (n_times, n_components): IC time-courses
A   = ica.mixing_               # (n_sources, n_components): spatial maps

# 4. Score each IC by how much of its map lies inside the fMRI ROI 
scores = []
for ic in range(n_components):
    spatial_map = np.abs(A[:, ic])
    roi_strength    = spatial_map[mask_data].mean()
    nonroi_strength = spatial_map[~mask_data].mean()
    scores.append(roi_strength / (nonroi_strength + 1e-6))

# 5. Select the ICs with highest ROI‐over‐nonROI ratio
selected = np.argsort(scores)[-3:]   # e.g. pick top 3

# 6. Reconstruct the ROI signal (time‐courses) from those ICs
roi_timecourses = S[:, selected]     # shape = (n_times, n_sel)

# 7. Reconstruct the spatial map from those ICs
ic = selected[0]                     # pick one of your chosen IC indices
spatial_map = A[:, ic]               # shape = (n_sources,)
vol_map = spatial_map.reshape(mask_data.shape)  

# Now `vol_map` is a 3D array you can nibabel.save() as a NIfTI,
# or plot with nilearn:
plotting.plot_stat_map(nib.Nifti1Image(vol_map, mask_nii.affine),
                       title=f"IC {ic} spatial map")

'''
NB: This code does not actually work with the 4D fMRI data...
It only works if you collapse your fMRI down to a single 3D map of activation (T- or β-values) – i.e. a fixed weight per voxel

Alternatives include; Reducing the fMRI to a static summary first or doing a spatio-temporal fusion
'''