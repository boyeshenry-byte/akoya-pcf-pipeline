# Akoya PCF analysis pipeline
*Author: Henry Boyes, Cleveland Clinic*
*Created: 2026-02-25*

The purpose of this pipeline is to provide spatial analysis for the Akoya PCF core lab. 

---

## Ingestion
*Last updated: 2026/02/25*

Scans project folders on the Isilon for .QPTIFF files and extracts metadata including slide ID, number of channels, marker names, and image dimensions.

**Validation** - Files are validated for completeness before database entry. Required fields are file path, file name, slide ID, number of channels, marker names, and image dimensions. Channel count is cross-checked against the number of marker names detected. 

**Schema decisions** - `file_path` is `NOT NULL` as a slide record without a file path is meaningless for downstream processing. Foreign key relationships enforce that pipeline status records cannot exist without a corresponding slide record. 

---

## Preprocessing
*Last updated: 2026-03-05*

**Channel statistics** - Min, max, mean intensity and nonzero fraction computed per channel.

**Low signal flagging** - Channels with nonzero fraction below 0.01 are flagged. Flagged 
channels are excluded from illumination correction.

**Illumination correction** - Gaussian background subtraction applied to unflagged channels. 
Sigma set to 50. To be tuned based on prototype data validation.

---

## Segmentation
*Last updated: 2026-03-05*

**Cellpose version** - v4.0.8

**Model type** - `nuclei` model was initially specified but removed due to Cellpose v4.0.1+ API changes 
which deprecated the `model_type` argument. Cellpose v4 uses a single unified model by default. 
Segmentation validated on prototype tonsil dataset using CellposeModel with auto-diameter detection.

**Tile size** - 2048px chosen as a power of 2 (2^11), aligning with memory allocation 
conventions in image processing.

**Tile overlap** - 256px (2^8) chosen as sufficient to capture full cells at tile boundaries 
without excessive redundant computation.

**Diameter** - Diameter= 0 (autodetect) was initially selected but changed to `None` due to Cellpose API changes

**Overflow Fix** - updated the cell count and offset to fix overflow bug effecting cell counts. Initially np.int64 was tried. However, it was discovered that accumulating offset values were causing artificial count inflations

**Tile Boundary Fix** - Updated tile boundaries to use min() on row/col stop values.

---

## Feature extraction
*Last updated: 2026-03-05*

**regionprops** - used skimage's `regionprops` to extract cell morphological features and intensity values

**storage decisions** - Per-cell storage used with intended spatial analysis later in pipeline. Aggregating to slide level now would remove the option for downstream phenotyping. Long format was decided on for adaptability of cell features. Long format is used for intensities due to their inherently multi-valued nature. The features were separated as standard normalization and to avoid repeating features for every data channel

---

## Planned
- Validate and fix Cellpose diameter based on prototype tonsil data
- Tune Gaussian sigma for illumination correction
- Establish formal validation workflow for segmentation QC
- Consider pathologist review of representative segmentation overlays
- Validate feature extraction