# SNP2Cluster-Py bioRxiv reproducibility repository

This repository contains the configurations, redistributable analytical inputs, final run outputs, figure-generation scripts, supplementary files and run instructions supporting the manuscript:

> **SNP2Cluster-Py: a pathogen-agnostic, context-aware framework for genomic transmission-cluster analysis**  
> **Authors:** Stanford Kwenda and Alan Christoffels  
> **Software version:** SNP2Cluster-Py v1.1.2  
> **Software repository:** [stanikae/snp2cluster-py](https://github.com/stanikae/snp2cluster-py)  
> **Software archive:** [Zenodo DOI 10.5281/zenodo.23045861](https://doi.org/10.5281/zenodo.23045861)

The repository preserves the six final analyses used in the manuscript and the materials required to inspect or reconstruct the reported results. SNP2Cluster-Py separates authoritative, context-aware Core SNP clustering from optional Facility, Area or Community analysis using epidemiological and temporal criteria.

## Final analyses

| ID | Dataset | Core context | Downstream analysis | SNP threshold | Temporal window |
|---|---|---|---|---:|---:|
| 01 | Full 172-isolate *Klebsiella pneumoniae* dataset | ST | None | 11 SNPs | Not applicable |
| 02 | Full 172-isolate *K. pneumoniae* dataset | Facility + ST | Facility | 11 SNPs | 14 days |
| 03 | 36-isolate single-hospital *K. pneumoniae* subset | ST | None | 11 SNPs | Not applicable |
| 04 | 36-isolate single-hospital *K. pneumoniae* subset | Facility + ST | Facility | 11 SNPs | 14 days |
| 05 | 168-isolate *Streptococcus pneumoniae* carriage dataset | ST | None | 12 SNPs | Not applicable |
| 06 | 168-isolate *S. pneumoniae* carriage dataset | ST | Community | 12 SNPs | 45 days |

All six analyses were generated with SNP2Cluster-Py v1.1.2 from Git commit `a4535d47beecfde1d6dc66097e0b78580032afc6`.

## Key reported results

- In the full *K. pneumoniae* dataset, ST-only analysis assigned 141 of 172 isolates (82.0%) to 25 Core SNP clusters. Facility + ST analysis assigned 134 isolates (77.9%) to 32 separately labelled Core clusters.
- Facility analysis of the complete *K. pneumoniae* dataset retained 84 isolates in 24 temporally compatible clusters across six hospitals.
- In the single-hospital subset, ST and Facility + ST contexts produced identical membership: 30 of 36 isolates were assigned to five Core SNP clusters. Facility analysis retained 23 isolates in four clusters.
- In the pneumococcal dataset, ST-context analysis assigned 114 of 168 isolates (67.9%) to 38 Core SNP clusters. All 114 were retained in 38 Community strain-sharing clusters.
- The representative Community examples in Figure 4 are ST802 and ST5103.

The increase from 25 Core clusters under ST-only analysis to 32 under Facility + ST analysis does not indicate increased clustering. Facility stratification divided ST-defined populations into smaller hospital–ST contexts while reducing total membership from 141 to 134 isolates.

## Repository structure

```text
.
├── README.md
├── configs/
│   └── final-v1.1.2/
│       ├── 01_kpneumoniae_full_st_core.yaml
│       ├── 02_kpneumoniae_full_facility_st.yaml
│       ├── 03_kpneumoniae_hospital_c_st.yaml
│       ├── 04_kpneumoniae_hospital_c_facility_st.yaml
│       ├── 05_spneumoniae_ghana_st_core.yaml
│       └── 06_spneumoniae_ghana_community.yaml
├── data/
│   ├── kpneumoniae/
│   └── spneumoniae/
├── reports/
├── runs/
│   ├── 01_kpneumoniae_full_st_core/
│   ├── 02_kpneumoniae_full_facility_st/
│   ├── 03_kpneumoniae_hospital_c_st/
│   ├── 04_kpneumoniae_hospital_c_facility_st/
│   ├── 05_spneumoniae_ghana_st_core/
│   └── 06_spneumoniae_ghana_community/
├── scripts/
└── supplementary/
    ├── SNP2Cluster-Py_Supplementary_Figures.pdf
    ├── SNP2Cluster-Py_Supplementary_Tables.xlsx
    └── SNP2Cluster-Py_Interactive_Visualizations.zip
```

The numbered configuration and run directories correspond one-to-one. The run directory names provide stable public identifiers for the six final manuscript analyses.

## Run-folder contents

Each directory under `runs/` retains the SNP2Cluster-Py output structure:

```text
<run>/
├── audit/
├── figures/
├── report/
└── tables/
```

### `audit/`

Contains validation records and the run manifest. For portability and privacy, machine-specific absolute input paths in the public copies of the manifests were replaced with repository-relative paths. All other recorded analytical parameters and provenance fields were preserved. Original, unmodified manifests are retained in the private analysis archive.

### `figures/`

Contains the static and interactive outputs generated for the analysis, including, where applicable:

- exploratory K-means and silhouette diagnostic figures;
- annotated Core SNP heatmaps;
- temporal scatterplots;
- interactive Core minimum spanning trees in HTML format; and
- interactive Facility or Community networks in HTML format.

Open the HTML files in a modern browser. Minimum-spanning-tree and downstream-network edges are analytical visualization relationships and must not be interpreted as confirmed direct or directional transmission.

### `report/`

Contains the scientific HTML report generated by SNP2Cluster-Py.

### `tables/`

Contains the authoritative machine-readable CSV outputs, including, where applicable:

- `core_snp_clusters.csv`;
- `isolate_cluster_assignments.csv`;
- `k_selection_diagnostics.csv`;
- `kmeans_cluster_assignments.csv`;
- `minimum_spanning_tree_edges.csv`;
- `transmission_clusters.csv`;
- `transmission_context.csv`;
- `transmission_network_nodes.csv`; and
- `transmission_network_edges.csv`.

The supplementary Excel workbook provides manuscript-oriented summaries and does not replace the native run-specific CSV files.

## Main manuscript figures

- **Figure 1:** SNP2Cluster-Py analytical workflow.
- **Figure 2:** Full-dataset comparison of ST-only and Facility + ST Core clustering in *K. pneumoniae*.
- **Figure 3:** Facility-level analysis of the 36-isolate Hospital C *K. pneumoniae* subset.
- **Figure 4:** Community-level pneumococcal analyses for ST802 and ST5103.

Scripts and run instructions for manuscript figure generation are available in `scripts/`. Static network panels are reconstructed deterministically from the corresponding node and edge tables rather than captured manually from a browser.

## Supplementary information

### Supplementary figures

`SNP2Cluster-Py_Supplementary_Figures.pdf` contains five figures:

- **Figure S1:** Complete *K. pneumoniae* annotated Core SNP heatmap from the full 172-isolate ST-only Core analysis.
- **Figure S2:** Complete *K. pneumoniae* annotated Core SNP heatmap from the full 172-isolate Facility + ST Core analysis.
- **Figure S3:** Facility-level *K. pneumoniae* transmission scatterplots for Hospitals A, B, D, E and F. Hospital C is presented in main-text Figure 3.
- **Figure S4:** Complete *S. pneumoniae* annotated Core SNP heatmap from the ST-only Core analysis.
- **Figure S5:** Complete *S. pneumoniae* annotated Core SNP heatmap with Community strain-sharing cluster annotations.

### Supplementary tables

`SNP2Cluster-Py_Supplementary_Tables.xlsx` contains five worksheets:

- **Table S1:** Input datasets, effective analytical configurations, software version and run provenance for the six final analyses.
- **Table S2:** Context-level authoritative Core SNP-clustering results.
- **Table S3:** Facility-level *K. pneumoniae* Core and transmission-cluster summaries.
- **Table S4:** Community-level pneumococcal Core and strain-sharing cluster summaries.
- **Table S5:** Isolate-level comparison of ST-only and Facility + ST *K. pneumoniae* Core-cluster assignments.

### Interactive visualizations

`SNP2Cluster-Py_Interactive_Visualizations.zip` contains the final interactive Core minimum spanning trees and downstream Facility and Community networks in their native HTML format, together with the associated machine-readable cluster, node and edge tables. The archive includes a README and manifest and preserves an analysis-specific directory structure.

## Reproducing the analyses

### 1. Obtain SNP2Cluster-Py v1.1.2

Clone the primary software repository and check out the manuscript version:

```bash
git clone https://github.com/stanikae/snp2cluster-py.git
cd snp2cluster-py
git checkout v1.1.2
```

Install SNP2Cluster-Py using the instructions in the primary repository. Confirm the version before running an analysis:

```bash
python -m src.snp2cluster.cli version
```

Expected:

```text
1.1.2
```

### 2. Clone this repository

```bash
git clone https://github.com/stanikae/SNP2Cluster-Py-bioRxiv-reproducibility.git
cd SNP2Cluster-Py-bioRxiv-reproducibility
```

### 3. Review data access and placement

The public configurations use repository-relative paths under `data/`. Confirm that every required input is present and that use of the source data complies with the relevant access conditions.

### 4. Run an analysis

From a SNP2Cluster-Py installation, run the required numbered configuration. For example:

```bash
python -m src.snp2cluster.cli run \
  --config /path/to/SNP2Cluster-Py-bioRxiv-reproducibility/configs/final-v1.1.2/01_kpneumoniae_full_st_core.yaml
```

When running from a different working directory, either resolve the repository-relative input paths before execution or use an equivalent local copy of the configuration with paths adjusted to the cloned repository.

### 5. Compare results

Compare the generated `audit/`, `figures/`, `report/` and `tables/` directories with the corresponding numbered directory under `runs/`. The native CSV outputs are authoritative for numerical comparisons.

## Figure and supplementary-file generation

The `scripts/` directory contains the reproducible workflows used to generate or compose the final manuscript materials, including:

- the Figure 2 Core-context comparison;
- deterministic static network exports;
- Figure 3 and Figure 4 composition;
- manuscript-run summaries and representative-lineage selection;
- supplementary-source collection; and
- final supplementary PDF, workbook and interactive archive generation.

Run the associated instruction files in `scripts/` from the location specified in each file. Manuscript-only build dependencies should be installed in a separate environment rather than added to the SNP2Cluster-Py runtime environment.

## Data provenance and access

The use-case data were derived from previously published studies:

- neonatal *K. pneumoniae* genomic surveillance from the Baby GERMS-SA programme in South Africa; and
- pneumococcal carriage genomic surveillance in Cape Coast, Ghana.

Public sequence data for the pneumococcal study are available under NCBI BioProject **PRJNA1100994**. Access conditions for the Baby GERMS-SA genomic data are described in the corresponding source publication.

Only derived inputs and de-identified metadata permitted for redistribution are included. Materials that cannot be redistributed should be represented through data dictionaries, expected filenames, checksums where permitted, access conditions and reconstruction or placement instructions. Users are responsible for complying with the source studies' access conditions and licences.

## Interpretation boundaries

SNP2Cluster-Py clusters are analytical groupings defined by the configured genomic, epidemiological and temporal criteria.

- Core SNP-cluster membership establishes genomic connectedness within the configured context but does not establish epidemiological linkage.
- Facility, Area or Community membership does not prove direct transmission.
- In carriage or population-surveillance datasets, Community assignments may represent putative strain-sharing clusters rather than confirmed transmission events.
- Network and minimum-spanning-tree edges do not establish transmission direction, source attribution or the absence of unsampled intermediates.
- The connected-component procedure implements single-linkage clustering; cluster diameter may exceed the configured edge threshold through chains of qualifying links.
- Results depend on the upstream SNP-distance matrix, metadata quality, selected Core context, SNP threshold and temporal window.

## Software and archive versions

- **SNP2Cluster-Py:** v1.1.2
- **SNP2Cluster-Py source commit:** `a4535d47beecfde1d6dc66097e0b78580032afc6`
- **SNP2Cluster-Py software archive:** [10.5281/zenodo.23045861](https://doi.org/10.5281/zenodo.23045861)
- **Original R-based SNP2Cluster archive:** [10.5281/zenodo.14060296](https://doi.org/10.5281/zenodo.14060296)
- **Companion repository release:** to be added when the public release is created
- **Companion Zenodo DOI:** to be added before manuscript submission

## Citation

When using SNP2Cluster-Py, cite the software archive and manuscript. When using the exact analyses, configurations or outputs preserved here, also cite the versioned archive of this companion repository. A machine-readable citation record should be updated with the bioRxiv DOI and companion archive DOI when available.

## Licence

SNP2Cluster-Py is distributed under the Apache License 2.0. The source datasets and derived materials remain subject to the licences, ethics approvals and access conditions described by their originating studies. Review the repository licence and the data-specific documentation before reusing the supplied materials.

## Contact

For questions about the public reproducibility materials, contact:

**BioinfoX**  
Email: [info@bioinfox.co.za](mailto:info@bioinfox.co.za)
