# =============================================================================
# generate_report.py
# Author: Henry Boyes
# Institution: Cleveland Clinic
# Date: 4/20/2026
# Version: v0.1.0
# Contact: boyeshenry@gmail.com
# Description: This script final AnnData files and output CSVs and generates visualizations for them for easy analysis.
# =============================================================================

import pandas as pd
import anndata as ad
import os
import argparse
import plotly.express as px

ISILON_BASE = os.environ.get("AKOYA_ISILON")

parser = argparse.ArgumentParser(description="Project folder name")
parser.add_argument("--project", required=True, type=str, help="Enter the project folder name (case sensitive)")
args = parser.parse_args()

def find_slides(spatial_dir):
    """
    This function finds the completed slides based on the available .h5ad files

    : ARGS :

    spatial_dir : str
        The directory the AnnData files are saved in

    
    : RETURNS :

    slide_list : list
        A list of tuples containing the slide_id and slide_name for each slide
    """    

    slide_list = []

    slides = os.listdir(os.path.join(spatial_dir, "anndata"))

    for slide in slides:
        slide_id, remainder = slide.split('_', 1)
        slide_name = remainder.replace('_final.h5ad', '')
        slide_list.append((slide_id, slide_name))

    return slide_list

# Load data
def load_spatial_csvs(spatial_dir, slide_id, slide_name):
    """
    This funciton loads the CSVs for visualization

    : ARGS :

    spatial_dir : str
        The directory the CSVs are located in

    slide_id : int
        The slide id number
    
    slide_name : str
        The slide name

    
    : RETURNS :

    data : dict
        A dictionary of the CSVs
    """
    
    data = {}

    # Load nhood CSVs
    nhood_zscore = pd.read_csv(os.path.join(spatial_dir, 'neighborhood_enrichment', f"{slide_id}_{slide_name}_zscore.csv"))
    nhood_pvals = pd.read_csv(os.path.join(spatial_dir, "neighborhood_enrichment", f"{slide_id}_{slide_name}_pvalue.csv"))

    data["nhood_zscore"] = nhood_zscore
    data["nhood_pvals"] = nhood_pvals

    # Load Ripley's CSVs
    modes = ["F", "G", "L"]

    for mode in modes:
        data[f"ripley_{mode}"] = pd.read_csv(os.path.join(spatial_dir, "ripley", f"{slide_id}_{slide_name}_mode_{mode}.csv"))
        data[f"ripley_{mode}_pvals"] = pd.read_csv(os.path.join(spatial_dir, "ripley", f"{slide_id}_{slide_name}_mode_{mode}_pvalues.csv"))
    
    # Load co-occurrence CSVs
    co_occ = pd.read_csv(os.path.join(spatial_dir, 'co_occurrence', f"{slide_id}_{slide_name}_co_occ.csv"), index_col=0)

    data["co_occ"] = co_occ

    return data


def load_adata(spatial_dir, slide_id, slide_name):
    """
    This function loads the .h5ad files

    : ARGS :

    spatial_dir : str
        The directory the CSVs are located in

    slide_id : int
        The slide id number
    
    slide_name : str
        The slide name

    
    : RETURNS :

    adata: AnnData object
        An AnnData object
    """
    adata = ad.read_h5ad(os.path.join(spatial_dir, "anndata", f"{slide_id}_{slide_name}_final.h5ad"))

    return adata

def generate_umap_clusters(adata):
    """
    This function generates per slide UMAP clusters

    : ARGS :

    adata : AnnData object
        An AnnData object with UMAP embedded

    : RETURNS :

    fig : scatter plot
        A plotly express scatter plot of UMAP colored by leiden
    """

    fig = []

    for i, a in enumerate(adata):
        fig.append(px.scatter(x=a.obsm['X_umap'][:,0], y=a.obsm['X_umap'][:,1], color=a.obs['leiden'], \
            title=f"Slide {a.obs['slide_name'].iloc[0]} UMAP"))

    return fig

def generate_nhood_heatmap(nhood_zscore, slide_name):
    """
    This function generates a heatmap of the neighborhood zscores

    : ARGS :

    nhood_zscores : matrix
        An n-by-n matrix of z scores

    slide_name : str
        The name of the slide

    : RETURNS :

    fig : heatmap
        A plotly heatmap of neighborhood z scores
    """

    fig = []

    for i, a in enumerate(nhood_zscore):
        fig.append(px.imshow(a, title=f"Slide {slide_name[i]} neighborhood z scores"))

    return fig

def generate_co_occ_heatmap(co_occ, slide_name):
    """
    This function generates a heatmap of the co-occurrence values

    : ARGS :

    co_occ : df
        A DataFrame containing co-occurrence values
    
    slide_name : str
        The name of the slide


    : RETURNS :

    fig : heatmap
        A plotly heatmap of co-occurrence values
    """

    fig = []

    for i, a in enumerate(co_occ):
        fig.append(px.imshow(a.pivot_table(columns='cluster_1', index='interval', values='score'), \
            title=f"Slide {slide_name[i]} co-occurrence"))

    return fig

def generate_ripley_curves(ripley_f, ripley_g, ripley_l, slide_name):
    """
    This function generates the Ripley's statistics curves for each mode

    : ARGS :

    ripley_f : DataFrame
        A DataFrame containing Ripley's statistics

    ripley_g : DataFrame
        A DataFrame containing Ripley's statistics

    ripley_l : DataFrame
        A DataFrame containing Ripley's statistics

    slide_name : str
        The name of the slide

    
    : RETURNS :

    plot_f : lineplot
        A lineplot of Ripley's statistics

    plot_g : lineplot
        A lineplot of Ripley's statistics

    plot_l : lineplot
        A lineplot of Ripley's statistics
    """

    fig_f = []
    fig_g = []
    fig_l = []

    for i, a in enumerate(ripley_f):
        fig_f.append(px.line(a, x='bins', y='stats', color='leiden',\
            title=f"Slide {slide_name[i]} Ripley's F"))

    for i, a in enumerate(ripley_g):
        fig_g.append(px.line(a, x='bins', y='stats', color='leiden',\
            title=f"Slide {slide_name[i]} Ripley's G"))
    
    for i, a in enumerate(ripley_l):
        fig_l.append(px.line(a, x='bins', y='stats', color='leiden',\
            title=f"Slide {slide_name[i]} Ripley's L"))

    return fig_f, fig_g, fig_l

def generate_report(umap, zscores, co_occ, f, g, l):
    """
    This function generates an .html report of all plots generated in the script

    : ARGS :

    umap : fig
        A plotly cluster map

    zscores : fig
        A plotly heatmap

    co_occ : fig
        A plotly heatmap

    f : fig
        A plotly linechart

    g : fig
        A plotly linechart

    l : fig
        A plotly linechart

    : RETURNS :

    report : str
        An html string 
    """

    report = ''.join([i.to_html(full_html=False) for i in umap]) + ''.join([i.to_html(full_html=False) for i in zscores])\
        + ''.join([i.to_html(full_html=False) for i in co_occ]) + ''.join([i.to_html(full_html=False) for i in f]) + \
            ''.join([i.to_html(full_html=False) for i in g]) + ''.join([i.to_html(full_html=False) for i in l])

    return report


if __name__ == "__main__":
    folder_name = args.project
    project_path = f"{ISILON_BASE}/{folder_name}"

    spatial_dir = os.path.join(project_path, 'spatial')

    slides = find_slides(spatial_dir)
    if not slides:
        exit()
    
    project_data = {
                    'slide_name': [],
                    'adata': [],
                    'nhood_zscore': [],
                    'nhood_pvals': [],
                    'co_occ': [],
                    'ripley_F': [],
                    'ripley_G': [],
                    'ripley_L': [],
                    'ripley_F_pvals': [],
                    'ripley_G_pvals': [],
                    'ripley_L_pvals': []
                }

    for slide in slides:
        try:
            slide_id, slide_name = slide

            csvs = load_spatial_csvs(spatial_dir, slide_id, slide_name)
            adata = load_adata(spatial_dir, slide_id, slide_name)

            
            project_data['slide_name'].append(slide_name)
            project_data['adata'].append(adata)
            project_data['nhood_zscore'].append(csvs['nhood_zscore'])
            project_data['nhood_pvals'].append(csvs['nhood_pvals'])
            project_data['co_occ'].append(csvs['co_occ'])
            project_data['ripley_F'].append(csvs['ripley_F'])
            project_data['ripley_G'].append(csvs['ripley_G'])
            project_data['ripley_L'].append(csvs['ripley_L'])
            project_data['ripley_F_pvals'].append(csvs['ripley_F_pvals'])
            project_data['ripley_G_pvals'].append(csvs['ripley_G_pvals'])
            project_data['ripley_L_pvals'].append(csvs['ripley_L_pvals'])

        except Exception as e:
            print(e)

    try:
        umap = generate_umap_clusters(project_data['adata'])
        zscores = generate_nhood_heatmap(project_data['nhood_zscore'], project_data['slide_name'])
        co_occ = generate_co_occ_heatmap(project_data['co_occ'], project_data['slide_name'])
        f, g, l = generate_ripley_curves(project_data['ripley_F'], project_data['ripley_G'], \
            project_data['ripley_L'], project_data['slide_name'])

    except Exception as e:
        print(e)

    try:
        report = generate_report(umap, zscores, co_occ, f, g, l)

        html = f"""
        <html>
        <head><title>{folder_name} Report</title></head>
        <body>
        {report}
        </body>
        </html>
        """

        output_path = os.path.join(project_path, f"{folder_name}_report.html")
        with open(output_path, 'w') as r:
            r.write(html)

    except Exception as e:
        print(e)