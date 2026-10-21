# Manuscript-to-code map

 Table labels are given as well as numbers so that the mapping remains useful if a later typesetting pass renumbers the document. The root driver performs path harvesting and the percentile derivation; the archived scripts themselves retain their original paths.

## Simulation populations and numerical results

| Manuscript location | Generating script under `reproducibility/` | Archived outputs under `reproducibility/` |
| --- | --- | --- |
| Section 6: 2,744 complete three-state models | `run_simulations.py` | `data/finite_models.csv`, `data/finite_summary.csv` |
| S1 designed safety/confidentiality/response banks; Appendix F | `run_simulations.py` | `data/*_observations.csv`, `data/*_summary.csv`, `data/candidates.json` |
| Table G.1A (`tab:experiments`): 3-, 4-, 5-state separators | `run_extensions.py` | `data_extensions/separator_coverage.csv` |
| Table G.1B and S1 Table S2 (`tab:S1small`): all 483,641 short programs | `run_extensions.py` | `data_extensions/small_programs_summary.csv`, `small_programs_meta.json` |
| Table G.1C and S1 Table S3 (`tab:S1sampled`): 50,000 programs at each of lengths 6, 8, 10, 12 | `run_sampled.py` | `data_sampled/sampled_programs_summary.csv`, `sampled_programs_meta.json` |
| Section 6, Simulation 1: 8 checkers × 8 budgets; benign benchmark | `sim1_diagonal_gatekeeper.py` | `sim1_adversary_results.csv`, `sim1_benign_benchmark.csv` |
| Section 6, Simulation 2: 200,000 programs × 11 lengths | `sim2_horizon_landscape.py` | `sim2_landscape.csv`, `sim2_first_bad_meta.json` |
| S1 Table S4 (`tab:S1sim2`): first-violation percentiles | Added `scripts/derive_horizons.py` | `sim2_required_horizon.csv`, derived from histogram and landscape |
| Section 6, Simulation 3: Goldbach, Collatz-cutoff and control plans | `sim3_open_problem_programs.py` | `sim3_open_problem_results.csv` |
| Section 6, Simulation 4: composition of confidentiality errors | `sim4_plateau_breakdown.py` | `sim4_plateau_breakdown.csv` |
| Section 6, Simulation 5: self-reference against 4 advertised certifiers | `sim5_rulebook_sized_omission.py` | `sim5_rulebook_sized_omission.csv` |

For interpretation of Simulations 1, 3 and 5, see `KNOWN_LIMITATIONS.md`. A successful rerun does not remove those limitations.

## Figures

| Figure | Data dependencies | Build procedure | Result |
| --- | --- | --- | --- |
| 1: concept and Goldbach timeline | `sim3_open_problem_results.csv` | `figures/build_fig1_data.py`, then pdfLaTeX on `fig1_concept.tex` | `figures/fig1_concept.pdf` |
| 2: evidence/observational extensions | Conceptual illustration; no numerical input | pdfLaTeX on `figures/fig2_evidence.tex` | `figures/fig2_evidence.pdf` |
| 3: self-reference and checker costs | `sim1_adversary_results.csv` | `figures/build_fig3_data.py`, then pdfLaTeX on `fig3_selfreference.tex` | `figures/fig3_selfreference.pdf` |
| 4: random-program landscape and first violations | `sim2_landscape.csv`, `sim2_required_horizon.csv`, `sim4_plateau_breakdown.csv`, `sim2_first_bad_meta.json` | `figures/build_fig4.py` | `figures/fig4_simulations.pdf`, `.png`, `fig4_numbers.json` |
| Supplement: three-state counts | `data/finite_summary.csv` | `reproducibility/build_figures.py --compile` | `reproducibility/figures/finite_models.pdf` |
| S1 Figure S1: designed banks | Three bank summary CSVs in `data/` | `reproducibility/build_figures.py --compile` | `reproducibility/figures/bounded_observation.pdf` |
| Supplement: experiments A–C | `data_extensions/` and `data_sampled/` summary CSVs | `reproducibility/build_figure_experiments.py --compile` | `reproducibility/figures/experiments.pdf` |

With `--plots --tex`, the driver rebuilds all seven figures and compiles S1. PDF bytes can differ due to metadata, fonts and renderer versions. Figure 1/3 numerical TeX blocks and Figure 4 numerical metadata support data-level comparisons.

## Tables

`scripts/export_tables.py` exports numerical tables to CSV, Markdown and a standalone TeX document, using the original denominators and the full available horizon grid. The root driver invokes it automatically. Its output is also included under `tables/generated/` for immediate reading.

| Export | Covers |
| --- | --- |
| `table_G1_A.csv` | Table G.1A, all finite-state separator counts |
| `table_G1_B_and_S2.csv` | Table G.1B and S1 Table S2, all short-program horizons |
| `table_G1_C_and_S3.csv` | Table G.1C and S1 Table S3, all sampled lengths/horizons |
| `table_S4.csv` | S1 Table S4, landscape error percentages and first-violation percentiles |
| `numerical_tables.md`, `.tex`, `.pdf` | Human-readable versions; PDF generated with `--tex` |

The theoretical/interpretive tables are authored exposition, not simulation outputs. Their original TeX fragments are included verbatim in `tables/reference/`:

- `tab_glance.tex`: main-result overview.
- `tab_glossary.tex`: formal notions and interpretations.
- `tab_mechanisms.tex`: deployed-mechanism comparison.
- `tab_novelty.tex`: prior-work comparison; no new bibliographic validation is claimed here.
- `tab_classes.tex`: expressive capabilities and closure.
- `tab_attempts.tex`: attempted ways around the barrier.
- `tab_experiments.tex`: manuscript numerical Table G.1, including original typesetting.
- `tab_vm.tex`: S1 instruction semantics.
- `tab_S1small.tex`, `tab_S1sampled.tex`, `tab_S1sim2.tex`: original numerical S1 tables.

These fragments preserve original labels/citations and are intended for insertion into the manuscript context; they are not standalone documents. The generated numerical table document is standalone and does not depend on the article source.
