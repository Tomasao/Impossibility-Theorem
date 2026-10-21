# Reproducing the version 14 results

## Requirements

- Python **3.9 or later** for all simulations and added utilities. The local validation used Python 3.9.6.
- The standard library is sufficient for simulations, numerical tables, checksums and TeX-source generation.
- Figure 4 additionally requires NumPy, pandas and Matplotlib. Exact versions used for the local rendering check are listed in `requirements-figures.txt`; this is a tested package set, not a claim to reconstruct the original author's complete environment.
- Compiling the other figures, numerical tables and S1 requires `pdflatex`, with TikZ/PGFPlots, `standalone`, `stmaryrd`, `microtype`, `booktabs`, `tabularx`, `longtable` and `pdflscape`. TeX Live or MacTeX can provide these. Put the TeX executables on `PATH`.

No external data, network service or API key is needed during execution once dependencies are installed. Scripts use processes across program lengths in Simulations 2 and 4. Python's `if __name__ == '__main__'` guards are retained for platforms that spawn processes.

## Commands from the repository root

| Command | Work performed |
| --- | --- |
| `python3 reproduce.py --suite archive` | Verify package hashes; derive percentile table; export numerical tables; rebuild TeX figure sources using archived results |
| `python3 reproduce.py --suite core` | Also regenerate the core finite-model and designed-bank data and compare with the archive |
| `python3 reproduce.py --suite full` | Also rerun exhaustive extensions, sampled programs and Simulations 1–5; harvest their outputs and compare scientific fields |
| Add `--plots` | Regenerate Figure 4 PDF/PNG and its numerical metadata |
| Add `--tex` | Compile six TeX figure sources, numerical tables and Supplementary Document S1 |
| `python3 scripts/check_known_limitations.py` | Reproduce concrete counterexamples to three archived Simulation 5 certifiers |

`--output build/another-run` selects another generated-output directory. The driver copies the original sources/data to a working directory before execution, so hard-coded output paths in archived scripts cannot overwrite repository inputs. Rerunning with the same output path refreshes that generated workspace.

## Outputs

After a run, inspect:

- `build/reproduction/reproduction_report.json`: command-suite status, elapsed times and per-file comparison results.
- `build/reproduction/logs/`: stdout/stderr for each stage.
- `build/reproduction/workspace/reproducibility/`: regenerated data and original-script intermediate outputs.
- `build/reproduction/workspace/figures/`: manuscript figure sources and, when requested, regenerated PDFs/PNG.
- `build/reproduction/workspace/reproducibility/figures/`: supplementary figure sources/PDFs.
- `build/reproduction/workspace/supplementary/`: compiled S1 when `--tex` is selected.
- `build/reproduction/tables/`: numerical CSV, Markdown and TeX exports; PDF when `--tex` is selected.

Figure 2 is conceptual and has no simulation input. Its original TikZ source is compiled directly. Numerical table typography is not identical to the manuscript: the exports retain the numbers and their provenance, and the original table fragments are in `tables/reference/`.

## Reproduction criteria

1. **Archive integrity:** `MANIFEST_SHA256.json` checks the bytes of each delivered input, including source and documentation. Extra repository files such as an existing licence are allowed. Deliberate edits require a new manifest/version; mismatches are not silently ignored.
2. **Core/extension/sampled data:** scientific CSV/JSON bytes are compared. Core `runtime.json` and its environment-dependent checksum manifest are excluded from scientific-output comparisons.
3. **Simulation 1:** compare non-timing fields. Hash-sensitive `coin_flip` rows are recorded as documented differences, never claimed to match. The driver sets `PYTHONHASHSEED=0`; the original generating process's hash seed is unknown.
4. **Simulation 3:** compare all scientific fields, excluding measured wall-clock seconds. A match says the archived computation was reproduced; it does not resolve the Collatz interpretation issue.
5. **Simulations 2, 4 and 5:** compare archived scientific outputs; the derived required-horizon table uses exact integer order statistics equivalent to the original lower-percentile convention.
6. **Figures:** compare their data/metadata and compile/render them. PDF metadata, fonts and renderer versions can change binary bytes. A PDF hash match is not required for scientific reproduction.

Status `completed_with_documented_differences` is distinct from an exact match. `failed_comparison` or `failed` gives a nonzero exit code. Neither successful status establishes the mathematical validity or general soundness of an implementation.

## Running original entry points separately

The original scripts remain directly runnable, but some overwrite adjacent generated files. Work on a copy if using them without the driver.

```bash
python3 reproducibility/run_simulations.py --output build/core-data
python3 reproducibility/run_extensions.py --output build/extension-data
python3 reproducibility/run_sampled.py --output build/sampled-data
python3 reproducibility/verify_reproduction.py
python3 reproducibility/verify_extensions.py
python3 reproducibility/verify_sampled.py
```

The three supplied verification scripts rerun their populations **twice** before comparison. The full driver runs each population once per invocation; no claim of repeated verification is made for a suite that was run only once.

## Resource and interpretation notes

The full suite includes 5,153,632 five-state models, 483,641 short programs, 200,000 programs in the earlier sampled experiment, 2.2 million programs in Simulation 2 and regeneration of that same population in Simulation 4. Simulations 2 and 4 launch up to ten processes. Runtime is hardware-dependent; see the validation record for measured durations. The Goldbach search can be a substantial stage.

One register-machine transition and one Python-generator yield are different experimental units. In the generator experiments, internal Python computation between yields is not charged. A wall-clock result must not be interpreted as a bound in the paper's abstract step model.

The reference datasets retain unresolved cases. Error rates are conditional on the populations/labels specified in the data dictionary. An unobserved violation is not a proof of safety; finite agreement of public outputs is not a proof of equality of their complete sequences.
