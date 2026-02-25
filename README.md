# Akoya PCF analysis 

**A pipeline for processing and segmentation of QPTIFF files from the Akoya PCF instrument.**

---

## Project Overview

This pipeline ingests QPTIFF images generated from Akoya's PhenoCycler Fusion instrument, processes them, and segments them for downstream analysis. 

---

## Quick Start

### Requirements

-python 3.11+

### Installation

```bash
# Clone the repository
git clone https://github.com/boyeshenry-byte/akoya-pcf-pipeline.git
cd akoya_pcf

# Install dependencies
pip install -r requirements.txt
```

---

## Project structure
```
akoya_pcf/
├── README.md
├── methods_log.md
├── requirements.txt
├── schema.sql
├── tests/
├── notebooks/
│   ├── 01_metadata_extraction_testing.ipynb
│   └── 02_preprocessing_exploration.ipynb
└── scripts/
    ├── ingestion.py
    ├── preprocessing.py
    ├── segmentation.py
    ├── utils.py
    └── init_db.py
```
---

## Usage

### Environment Variables
Set the following before running:
```bash
export AKOYA_ISILON=/path/to/isilon
export AKOYA_DB=/path/to/akoya.db
```

Execute in order:
1.) **init_db.py** - creates a database to store metadata
    - python scripts/init_db.py
2.) **ingestion.py** - extracts metadata and stores it in the db
    - python scripts/ingestion.py --project my_project
3.) **preprocessing.py** - compute channel statistics and correct low signals, save statistics to db and save QC PNG's
    - python scripts/preprocessing.py --project my_project
4.) **segmentation.py** - Extract DAPI channel and segments via Cellpose. Saves masks in project dir
     -python scripts/segmentation.py --project my_project --diameter 0

---

## Database schema

The pipeline uses a SQLite database with the following tables:

- `runs` - instrument run metadata
- `slides` - slide records and file paths
- `pipeline_status` - tracks processing status across all pipeline stages per slide
- `channel_stats` - per-channel QC statistics from preprocessing
- `segmentation_results` - Cellpose segmentation outputs and status per slide

##  Author

**Henry Boyes**
- GitHub: [@boyeshenry-byte](https://github.com/boyeshenry-byte)
- LinkedIn: [Henry Boyes](https://linkedin.com/in/hboyes)
- Email: boyeshenry@gmail.com

---

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

##  Acknowledgments

- **Cellpose (Stringer et al.)** - Cell segmentation model used in the segmentation stage
- **Cleveland Clinic** -institutional support

---

## Citation
If you use this pipeline in your research, please cite this repository:
Henry Boyes. Akoya PCF Analysis Pipeline. Cleveland Clinic, 2026.
https://github.com/boyeshenry-byte/akoya-pcf-pipeline