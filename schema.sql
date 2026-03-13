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
    file_path text not null, -- /home/boyesh/IMLAkoyafusion/<subfolder>/<filename>.qptiff
    file_name text, -- Original file name
    num_channels integer, -- Number of channels in image
    date_added datetime -- when record was created
);

create table pipeline_status(
    status_id integer primary key autoincrement, --Primary key, autoincrement
    slide_id integer references slides(slide_id) not null, --Foreign key (slides.slide_id)
    ingestion text, --Not started/In progress/Complete/Failed
    preprocessing_qc text, --Not started/In progress/Complete/Failed
    segmentation text, --Not started/In progress/Complete/Failed
    feature_extraction text, --Not started/In progress/Complete/Failed
    anndata_export text, --Not Started/In Progress/Complete/Failed
    phenotyping text, --Not started/In progress/Complete/Failed
    spatial_analysis text, --Not started/In progress/Complete/Failed
    last_update datetime, --Timestamp of most recent status change
    notes text --Flag failures and QC concerns
);

create table channel_stats(
    stat_id integer primary key autoincrement, --Primary key, autoincrement
    slide_id integer references slides(slide_id), --Foreign key (slide_id)
    channel_index integer, --Index of channels run
    channel_name text, --Name of channel
    min_intensity real,  --Minimum intensity of the channel
    max_intensity real, --Maximum intensity of the channel
    mean_intensity real, --Mean intensity of the channel
    nonzero_fraction real, --The nonzero fraction of the channel
    flagged integer, --QC status of the channel
    flag_message text, --Associated QC message
    processed_at datetime not null --When the slide was preprocessed
);

create table segmentation_results(
    segment_id integer primary key autoincrement, --Primary key, autoincrement
    slide_id integer references slides(slide_id) not null, -- Foreign key (slide_id)
    cell_count integer, --Total cells detected
    diameter_used real, --Diameter used for segmentation
    tile_size integer, --Tile size used
    tile_overlap integer, --Tile overlap used
    segment_status text not null, --Passed/failed
    error_message text, --Null on success, reason on failure
    processed_at datetime not null --When the slide was segmented
);

create table cell_features(
    cell_id integer primary key autoincrement, --Primary key autoincrementing
    slide_id integer references slides(slide_id) not null, --Foreign key (slide_id)
    label integer not null, --Cell label from the mask
    area real, --Area of the cell
    centroid_x real, --X coordinate of the cell's centroid
    centroid_y real, --Y coordinate of the cell's centroid
    eccentricity real, --How elongated is the cell (0=circle, 1=line)
    perimeter real, --Boundary length of the cell
    solidity real --How convex the cell is (filled vs irregular)
);

create table cell_intensity(
    intensity_id integer primary key autoincrement, --Primary key autoincrementing
    cell_id integer references cell_features(cell_id) not null, --Foreign key (cell_id)
    channel_index integer references channel_stats(channel_index) not null, --Foreign key (channel_index)
    channel_name text, --Channel name
    mean_intensity real not null, --Average cell intensity
    max_intensity real not null --Max cell intensity
);