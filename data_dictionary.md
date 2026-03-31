# Akoya PCF Pipeline — Data Dictionary
*Author: Henry Boyes, Cleveland Clinic*
*Created: 2026-03-31*

This document describes all outputs produced by the Akoya PCF analysis pipeline, including the SQLite database schema, AnnData object structure at each pipeline stage, and spatial analysis CSV formats.

---

## SQLite Database (`akoya.db`)

### `runs`
Stores instrument run-level metadata.

| Column | Type | Description |
|--------|------|-------------|
| run_id | INTEGER | Primary key, autoincrement |
| run_name | TEXT | Batch/run label from instrument |
| run_date | DATE | Date of run |
| panel_name | TEXT | Marker panel used |
| notes | TEXT | Optional free text |

---

### `slides`
One record per slide. Central table for all downstream processing.

| Column | Type | Description |
|--------|------|-------------|
| slide_id | INTEGER | Primary key, autoincrement |
| slide_name | TEXT | Slide label |
| patient_id | TEXT | Patient identifier |
| tissue_region | TEXT | Tissue source (e.g. tumor core) |
| run_id | INTEGER | Foreign key → runs.run_id |
| file_path | TEXT | Full path to .QPTIFF file on Isilon |
| file_name | TEXT | Original file name |
| num_channels | INTEGER | Number of channels in image |
| date_added | DATETIME | Timestamp of record creation |

---

### `pipeline_status`
Tracks processing status per slide across all pipeline stages.

| Column | Type | Description |
|--------|------|-------------|
| status_id | INTEGER | Primary key, autoincrement |
| slide_id | INTEGER | Foreign key → slides.slide_id |
| ingestion | TEXT | Not Started / Complete / Failed |
| preprocessing_qc | TEXT | Not Started / Complete / Failed |
| segmentation | TEXT | Not Started / Complete / Failed |
| feature_extraction | TEXT | Not Started / Complete / Failed |
| anndata_export | TEXT | Not Started / Complete / Failed |
| phenotyping | TEXT | Not Started / Complete / Failed |
| spatial_analysis | TEXT | Not Started / Complete / Failed |
| last_update | DATETIME | Timestamp of most recent status change |
| notes | TEXT | QC concerns or failure flags |

---

### `channel_stats`
Per-channel QC statistics computed during preprocessing.

| Column | Type | Description |
|--------|------|-------------|
| stat_id | INTEGER | Primary key, autoincrement |
| slide_id | INTEGER | Foreign key → slides.slide_id |
| channel_index | INTEGER | Zero-based channel index |
| channel_name | TEXT | Marker name (e.g. DAPI, CD3) |
| min_intensity | REAL | Minimum pixel intensity |
| max_intensity | REAL | Maximum pixel intensity |
| mean_intensity | REAL | Mean pixel intensity |
| nonzero_fraction | REAL | Fraction of non-zero pixels (0–1) |
| flagged | INTEGER | 1 = flagged for low signal, 0 = passed |
| flag_message | TEXT | Reason for flagging, null if passed |
| processed_at | DATETIME | Timestamp of preprocessing |

---

### `segmentation_results`
Cellpose segmentation outputs per slide.

| Column | Type | Description |
|--------|------|-------------|
| segment_id | INTEGER | Primary key, autoincrement |
| slide_id | INTEGER | Foreign key → slides.slide_id |
| cell_count | INTEGER | Total cells detected after stitching |
| diameter_used | REAL | Cell diameter used for segmentation (pixels) |
| tile_size | INTEGER | Tile size used (pixels) |
| tile_overlap | INTEGER | Tile overlap used (pixels) |
| segment_status | TEXT | Passed / Failed |
| error_message | TEXT | Null on success, error reason on failure |
| processed_at | DATETIME | Timestamp of segmentation |

---

### `cell_features`
Morphological features per cell extracted via `regionprops`.

| Column | Type | Description |
|--------|------|-------------|
| cell_id | INTEGER | Primary key, autoincrement |
| slide_id | INTEGER | Foreign key → slides.slide_id |
| label | INTEGER | Cell label from segmentation mask |
| area | REAL | Cell area in pixels² |
| centroid_x | REAL | X coordinate of cell centroid (pixels) |
| centroid_y | REAL | Y coordinate of cell centroid (pixels) |
| eccentricity | REAL | Cell elongation (0 = circle, 1 = line) |
| perimeter | REAL | Cell boundary length (pixels) |
| solidity | REAL | Convexity measure (0–1, 1 = fully convex) |

---

### `cell_intensity`
Per-cell marker intensity values across all channels. Long format.

| Column | Type | Description |
|--------|------|-------------|
| intensity_id | INTEGER | Primary key, autoincrement |
| cell_id | INTEGER | Foreign key → cell_features.cell_id |
| channel_index | INTEGER | Foreign key → channel_stats.channel_index |
| channel_name | TEXT | Marker name |
| mean_intensity | REAL | Mean pixel intensity within cell mask |
| max_intensity | REAL | Maximum pixel intensity within cell mask |

---

## AnnData Objects (`.h5ad`)

One `.h5ad` file is produced per slide at two pipeline stages. All files follow the naming convention `slide_<id>_<slide_name>.h5ad`.

### Post `anndata_export.py`
Stored in `<project>/anndata/`

| Slot | Content |
|------|---------|
| `X` | Mean marker intensity matrix (cells × channels), arcsinh-transformed in phenotyping |
| `layers['max_intensity']` | Max marker intensity matrix (cells × channels) |
| `obs` | Per-cell features: area, centroid_x, centroid_y, eccentricity, perimeter, solidity, slide_id, slide_name |
| `var` | Per-channel stats: min_intensity, max_intensity, mean_intensity, nonzero_fraction, flagged, flag_message |
| `obsm['spatial']` | (n_cells × 2) array of centroid_x, centroid_y coordinates |

### Post `phenotyping.py`
Stored in `<project>/phenotyping/`, named `slide_<id>_<slide_name>_phenotyped.h5ad`

Inherits all slots from above, plus:

| Slot | Content |
|------|---------|
| `obs['leiden']` | Leiden cluster label per cell |
| `obsm['X_pca']` | PCA embedding |
| `obsm['X_umap']` | UMAP embedding |
| `uns['leiden']` | Leiden clustering parameters |
| `uns['neighbors']` | Neighbor graph parameters |
| `uns['pca']` | PCA parameters |
| `uns['umap']` | UMAP parameters |

---

## Spatial Analysis Outputs

Stored in `<project>/spatial/` with subdirectories by analysis type. Files follow the naming convention `<slide_id>_<slide_name>_<type>.csv`.

### `neighborhood_enrichment/`
**`<slide_id>_<slide_name>_zscore.csv`**

Square matrix (n_clusters × n_clusters) of neighborhood enrichment z-scores. Rows and columns are Leiden cluster labels. Positive values indicate enrichment, negative values indicate depletion.

---

### `ripley/`
**`<slide_id>_<slide_name>_mode_<F/G/L>.csv`**

Ripley's statistic per cluster across distance bins. Columns: `bins`, `leiden`, `stats`.

**`<slide_id>_<slide_name>_mode_<F/G/L>_pvalues.csv`**

P-values per cluster (rows) across distance bins (columns).

---

### `co_occurrence/`
**`<slide_id>_<slide_name>_co_occ.csv`**

Long-format co-occurrence scores. Columns: `interval`, `cluster_1`, `score`. Each row represents the co-occurrence score between two clusters at a given distance interval.

---

### `anndata/`
**`<slide_id>_<slide_name>_final.h5ad`**

Final AnnData object with all spatial analysis results embedded in `uns`. Inherits all phenotyping slots plus Squidpy outputs:

| Key | Content |
|-----|---------|
| `uns['spatial_neighbors']` | Spatial KNN graph |
| `uns['leiden_nhood_enrichment']` | Neighborhood enrichment zscore and count matrices |
| `uns['leiden_co_occurrence']` | Co-occurrence scores and interval bins |
| `uns['leiden_ripley_F']` | Ripley's F statistics |
| `uns['leiden_ripley_G']` | Ripley's G statistics |
| `uns['leiden_ripley_L']` | Ripley's L statistics |
| `uns['cell_diameter']` | Cell diameter used for co-occurrence intervals |