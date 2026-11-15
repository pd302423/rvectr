# User-supplied licensed model assets

The published source contains no body-model parameters or meshes. The Python
package `smplx` is code; official SMPL/SMPL-X data is obtained separately under
the applicable model license. The current fitter uses **SMPL neutral**, not
SMPL-X, and expects `smpl/SMPL_NEUTRAL.pkl` under `RVECTR_MODELS_DIR`.

Prefer a private model directory outside the repository. Existing local files
are preserved and ignored by Git. Do not upload parameter pickles, regressors,
templates, converted arrays or generated meshes as part of a source release
without checking the applicable terms. SMPL-X support is a separate future
model/landmark mapping change, not a filename substitution.

Official model terms: https://smpl.is.tue.mpg.de/modellicense.html
