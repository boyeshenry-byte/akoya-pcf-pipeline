# Akoya PCF analysis pipeline
*Author: Henry Boyes, Cleveland Clinic*
*Created: 2026-02-25

The purpose of this pipeline is to provide spatial analysis for the Akoya PCF core lab. 

---

## Ingestion
*Last updated: 2026/02/25*

Scans project folders on the Isilon for .QPTIFF files and extracts metadata including slide ID, number of channels, marker names, and image dimensions.

**Validation** - Files are validated for completeness before database entry. Required fields are file path, file name, slide ID, number of channels, maker names, and image dimensions. Channel count is cross-checked agains the number of marker names detected. 

**Schema decisions** - `file_path` is `NOT NULL` as a slide record without a file path is meaningless for downstream processing. Foreign key relationships enfor that pipeline status records cannot exist without a corresponding slide record. 

---

## Preprocessing
*Last updated: 2026-02-25*

**Channel statistics** - Min, max, mean intensity and nonzero fraction computed per channel.

**Low signal flagging** - Channels with nonzero fraction below 0.01 are flagged. Flagged 
channels are excluded from illumination correction.

**Illumination correction** - Gaussian background subtraction applied to unflagged channels. 
Sigma set to 50. To be tuned based on prototype data validation.

---

## Segmentation
*Last updated: 2026-02-25*

**Model type** - `nuclei` model chosen due to the nuclear-staining-anchored workflow of the 
PhenoCycler and intended use in the tumor microenvironment. Specifically trained for DAPI 
channels and handles dense cell packing better than cytoplasm-based models.

**Tile size** - 2048px chosen as a power of 2 (2^11), aligning with memory allocation 
conventions in image processing.

**Tile overlap** - 256px (2^8) chosen as sufficient to capture full cells at tile boundaries 
without excessive redundant computation.

**Diameter** - Auto-detect (0) used during development. To be tuned and fixed following 
prototype data validation.

---

## Planned
- Validate and fix Cellpose diameter based on prototype tonsil data
- Tune Gaussian sigma for illumination correction
- Establish formal validation workflow for segmentation QC
- Consider pathologist review of representative segmentation overlays