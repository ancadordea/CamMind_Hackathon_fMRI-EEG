import numpy as np, nibabel as nib, mne
from mne.minimum_norm import make_inverse_operator, apply_inverse
from sklearn.decomposition import FastICA
from nilearn import plotting

subjects_dir = '/path/to/freesurfer/subjects'
subject      = 'sub-001'
raw_fname    = 'sub-001_eeg.fif'           # or build RawArray from your matrix
bem_fname    = f'{subjects_dir}/{subject}/bem/{subject}-5120-bem.fif'
trans_fname  = f'{subjects_dir}/{subject}/mri/{subject}-eeg-trans.fif'
mask_fname   = 'myContrast_mask.nii'

# 1. Load EEG and create a forward model
raw = [] # LOAD THE RAW 2D-ARRAY

# time-based noise covariance for MNE
cov = mne.compute_raw_covariance(raw, tmin=0, tmax=None)

# Source space: 5-mm cortical grid
src = mne.setup_source_space(subject, spacing='ico5',
                             subjects_dir=subjects_dir, add_dist=False)

fwd = mne.make_forward_solution(
            raw.info, trans=trans_fname, src=src,
            bem=bem_fname, eeg=True, meg=False)


# 2. Build an inverse operator and obtain the source estimate
inverse_op = make_inverse_operator(raw.info, fwd, cov,
                                   loose=0.2, depth=0.8)   # MNE defaults
snr = 3.
lambda2 = 1. / snr ** 2

# Apply the inverse to continuous data -> SourceEstimate (n_vertices × n_times)
stc = apply_inverse(raw, inverse_op, lambda2,
                    method='dSPM', pick_ori='normal')


# 3. Vectorise the fMRI mask to the same grid
# 3-D mask in the *same affine* as the source space
mask_img   = nib.load(mask_fname)
mask_bool  = mask_img.get_fdata().astype(bool).ravel()   # -> (n_vertices,)

assert mask_bool.size == stc.data.shape[0], "mask / source mismatch"


# 4. Spatial ICA on the (time × sources) matrix
X   = stc.data.T                       # (n_times, n_sources)
ica = FastICA(n_components=20, random_state=0)
S   = ica.fit_transform(X)             # component time-courses
A   = ica.mixing_                      # spatial maps (n_sources × n_IC)


# 5. Score each component by ROI-over-nonROI power
roi_scores = []
for ic in range(A.shape[1]):
    m = np.abs(A[:, ic])
    roi_scores.append(m[mask_bool].mean() /
                      (m[~mask_bool].mean() + 1e-6))

sel = np.argsort(roi_scores)[-3:]      # keep the top 3


# 6. Grab the outputs you need
# (a) ROI time-courses
roi_tc = S[:, sel]                     # shape: (n_times, 3)

# (b) Spatial map of the best component as NIfTI
best_ic      = sel[-1]
best_map     = A[:, best_ic].reshape(mask_img.shape)
best_img     = nib.Nifti1Image(best_map, mask_img.affine)
nib.save(best_img, 'IC_roi_map.nii')

# Visual-check the map:
plotting.plot_stat_map(best_img, title=f'IC {best_ic} – ROI-constrained')