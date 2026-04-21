# Akoya PCF analysis pipeline
*Author: Henry Boyes, Cleveland Clinic*
*Created: 2026-02-25*

The purpose of this pipeline is to provide spatial analysis for the Akoya PCF core lab. 

---

## Ingestion
*Last updated: 2026-03-31*

Scans project folders on the Isilon for .QPTIFF files and extracts metadata including slide ID, number of channels, marker names, and image dimensions.

**Validation** - Files are validated for completeness before database entry. Required fields are file path, file name, slide ID, number of channels, marker names, and image dimensions. Channel count is cross-checked against the number of marker names detected. 

**Schema decisions** - `file_path` is `NOT NULL` as a slide record without a file path is meaningless for downstream processing. Foreign key relationships enforce that pipeline status records cannot exist without a corresponding slide record. 

---

## Preprocessing
*Last updated: 2026-03-31*

**Channel statistics** - Min, max, mean intensity and nonzero fraction computed per channel.

**Low signal flagging** - Channels with nonzero fraction below 0.01 are flagged. Flagged 
channels are excluded from illumination correction.

**Illumination correction** - Gaussian background subtraction applied to unflagged channels. 
Sigma set to 50. To be tuned based on prototype data validation.

**Added QC PNG subfolders** - Added subfolders to save per slide QC PNGs. 

**Channel name** - Added a fix to write the channel name to the database. 

---

## Segmentation
*Last updated: 2026-03-31*

**Cellpose version** - v4.0.8

**Model type** - `nuclei` model was initially specified but removed due to Cellpose v4.0.1+ API changes 
which deprecated the `model_type` argument. Cellpose v4 uses a single unified model by default. 
Segmentation validated on prototype tonsil dataset using CellposeModel with auto-diameter detection.

**Tile size** - 2048px chosen as a power of 2 (2^11), aligning with memory allocation 
conventions in image processing.

**Tile overlap** - 256px (2^8) chosen as sufficient to capture full cells at tile boundaries 
without excessive redundant computation.

**Diameter** - Diameter= 0 (autodetect) was initially selected but changed to `None` due to Cellpose API changes.

**Overflow Fix** - updated the cell count and offset to fix overflow bug effecting cell counts. Initially np.int64 was tried. However, it was discovered that accumulating offset values were causing artificial count inflations.

**Tile Boundary Fix** - Updated tile boundaries to use min() on row/col stop values.

---

## Feature extraction
*Last updated: 2026-03-31*

**regionprops** - Used skimage's `regionprops` to extract cell morphological features and intensity values. 
Initially, `.mean_intensity` and `.max_intensity` were used, however, those methodologies are deprecated. 
Updated to `.intensity_mean` and `.intensity_max` respectively.

**storage decisions** - Per-cell storage used with intended spatial analysis later in pipeline. Aggregating to slide level now would remove the option for downstream phenotyping. Long format was decided on for adaptability of cell features. Long format is used for intensities due to their inherently multi-valued nature. The features were separated as standard normalization and to avoid repeating features for every data channel.

**cell count discrepancy** - Upon analysis there is a roughly 10 to 15% discrepancy between segmentation and feature extraction counts. This is consistent across all 5 prototyping slides and is likely fragments or artifacts from the tiling process, rather than actual counts. Considering this is replicated across all five slides it is believed to be a filtering effect rather than a random error. 

**Validation check** - The intensity records show 24M cells. 3M x 8 Channels is 24M. This shows consistency in the counts across the channels and scikit-image.

---

## AnnData Export
*Last updated: 2026-03-31*

**AnnData Export** - Created separately from other pipelines to ensure usability across analyses.

**AnnData Design** - Considering the usability for projects, one file per slide was chosen instead of one file per project. The .h5ad file was mapped to the following:
* X - mean_intensity from cell_intensity.
* layers['max_intensity'] - max_intensity from cell_intensity.
* obs - cell_features (area, centroid_x and _y, eccentricity, perimeter, and solidity) plus slide_id and slide_name joined from slides.
* var - channel_stats (channel_name as index, min_intensity, max_intensity, mean_intensity, nonzero_fraction, flagged, and flag_message).
* obsm['spatial'] - centroid_x and _y from cell_features stacked as a numpy array following Squidpy's spatial coordinate system.

**Cell count discrepancy check** - Considering the discrepancy between segmentation_results and cell_features's cell counts a check was added to flag if there is a more than 20% difference between the two. Roughly 15% discrepancy is expected from tiling artifacts and as such, 20% was decided on to leave space for variance. For the prototyping run, 10-15% variation was observed which is in the expected range. 

**NULL byte bug** - A null byte bug was discovered in channel_stats that caused an issue in converting to .h5ad format. This was solved by ensuring the numpy values were cast to floats() before writing to SQLite.

---

## Phenotyping
*Last updated: 2026-04-01*

**Scope** - Since this pipeline is developed as a core lab service for use with the IO60 panel. Cell annotation using the IO60 panel as a defult is used to suggest cell types. Expected cells depend on many factors outside of what the core lab anticipates knowing and varies too broadly. As such, annotation will be the researcher's responsibility and suggested cell types should be verified with what the researcher expects to see.

**arcsinh** - A cofactor of 5 was used as industry standard instead of log normalization since intensity data is not count data.

**Leiden** - Leiden clustering was chosen over KMeans since it is graph-based and more suitable for high-dimensional, single-cell data. A resolution was set at 0.5. This is a default and tunable per dataset.

**UMAP** - Computed after clustering for the correct dependency order.

**scanpy** - `flavor="igraph"`, `n_iterations=2` and `directed=False` were used in accordance with future scanpy defaults.

**per-slide output** - per-slide `.h5ad` output files and figures saved to `phenotyping/` subfolder. These are distinct from the original `.h5ad` files. Raw `.h5ad` values were preserved in the new processed files.

---

## Spatial Analysis
*Last updated: 2026-04-02*

**Scope** - Spatial analysis is performed on phenotyped AnnData files using Squidpy. Analysis includes spatial graph construction, neighborhood enrichment, co-occurrence scoring, and Ripley's statistics.

**Spatial graph** - KNN graph constructed using `sq.gr.spatial_neighbors` with `coord_type='generic'` since cells are biologically distributed rather than arranged in a regular grid. Default `n_neighs=10`, tunable via `--n_neigh` argument.

**Neighborhood enrichment** - Permutation-based enrichment analysis (`n_perms=1000`) computed between Leiden clusters. Results stored as z-scores in an n×n matrix where n is the number of clusters.

**Co-occurrence** - Distance-resolved co-occurrence scores computed across interval bins derived from cell diameter (1–10x diameter, step=1x diameter). Cell diameter sourced from `segmentation_results.diameter_used`. Scores stored in long format with columns `cluster_1`, `interval`, and `score`.

**Ripley's statistics** - All three modes (F, G, L) computed per slide with `n_simulations=1000`. F and G describe nearest-neighbor distance distributions; L is a normalized measure of overall clustering.

**Output structure** - Results exported to `spatial/` subfolder with subdirectories: `anndata/` (final .h5ad), `neighborhood_enrichment/` (zscore CSVs), `ripley/` (stat and pvalue CSVs per mode), and `co_occurrence/` (melted long-format CSV).

**QC plotting** - QC plots are saved to `spatial/` in the `spatial_qc/` subdirectory.

**Known issues** - `diameter_used` was not being written to `segmentation_results` during prototype runs due to Cellpose returning `None` when diameter is not explicitly set. Values manually set to 30 for prototype validation. Fix implemented in `segmentation.py` but prototype slides have not been re-segmented.

---

## Report Generation
*Last updated: 2026-04-20*

**HTML** - The decision was made to generate reports using html as opposed to streamlit or other interactive dashboards due to the need to keep projects separated for researchers using the service. 

**UMAP** - UMAP figures are generated per-slide as opposed to a grouped overview of the project as different tissues/locations would exist on the slide and averaging position would not make sense in reporting. 

**Averages** - For the remainder of reports, the project average is returned as a general overview of the data from the project. 

---

## HPC/parallelization
*Last updated: 2026-04-21*

**Two-phase submission** - Scripts were designed with two-phase submission. The current pipeline design uses a combination of checking the environment for what files are available in early stages. Then checks to ensure stage completion in the database before writing orphan data in later stages. Since the later stages cannot know the slide count until the database is populated, they are implemented in a second phase after the slides have been input. 

**SLURM_ARRAY_TASK_ID** - SLURM_ARRAY_TASK_ID is used to index slides via SLURM submission. It is used as a fallback for local runs and to ensure deterministic ordering so slides are mapped the same across concurrent runs. 