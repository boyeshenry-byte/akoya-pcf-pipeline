create table runs(
    run_id integer primary key autoincrement, --primary key, autoincrement
    run_name text not null, -- Batch/run label from instrument
    run_date date, -- Date of run
    panel_name text, -- Marker panel used
    notes text --Optional free text
);

create table slides(
    slide_id integer primary key autoincrement, -- Primary key, autoincrement
    slide_name text not null, -- Slide label
    patient_id text, -- Patient identifier
    tissue_region text, -- Where tissue is from (eg tumor core)
    run_id integer references runs(run_id), -- Foreign key (runs.run_id)
    file_path text, -- /home/boyesh/IMLAkoyafusion/<subfolder>/<filename>.qptiff
    file_name text, -- Original file name
    num_channels integer, -- Number of channels in image
    date_added datetime -- when record was created
);

create table pipeline_status(
    status_id integer primary key autoincrement, --Primary key, autoincrement
    slide_id integer references slides(slide_id), --Foreign key (slides.slide_id)
    ingestion text, --Not started/In progress/Complete/Failed
    preprocessing_qc text, --Not started/In progress/Complete/Failed
    segmentation text, --Not started/In progress/Complete/Failed
    feature_extraction text, --Not started/In progress/Complete/Failed
    phenotyping text, --Not started/In progress/Complete/Failed
    spatial_analysis text, --Not started/In progress/Complete/Failed
    last_update datetime, --Timestamp of most recent status change
    notes text --Flag failures and QC concerns
);

