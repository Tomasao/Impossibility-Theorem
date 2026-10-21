# Data dictionary and provenance

## Scope

 `PROVENANCE.json` records the source-archive checksum, preserved files and deliberate omissions. `data_inventory.json` lists each CSV/JSON file with its size, checksum, CSV row count and field names. No private participant data, external data download or learned model is required.

The archived data consist of full finite-model records, observations on designed program banks, and aggregate results/histograms for exhaustive and sampled populations. The 2.2 million sampled program codes and their individual traces are **not** stored as 2.2 million records. The sampler, seed schedule and interpreter regenerate that population; its supplied CSV has 121 aggregate rows (11 lengths × 11 horizons).

## Norms and units

- **Safety:** no `BAD` event on input 0.
- **Confidentiality:** identical complete public-output sequences on inputs 0 and 1. Event timing and silent termination are ignored by the reference norm; fixed-horizon prefixes can still differ.
- **Response:** an eventual valid answer on every natural input. Finite-state experiments instead check all effective starting states under their declared input mapping.
- **Register-machine step:** one instruction transition. Registers contain arbitrary-precision natural numbers; physical bit cost is not measured.
- **Generator step:** one Python `yield` in Simulations 1, 3 and 5. Work between yields is unmetered and can contain many Python operations.
- **Unresolved:** the implemented reference methods have not settled the unbounded label. It is a computational status, not a third normative category, and is excluded from label-dependent error rates.
- **Uncertified:** a partial certificate method abstains; this is not itself an incorrect decision.

## Populations and seeds

| Experiment | Population | Randomness/provenance |
| --- | --- | --- |
| Core finite models | 2,744 three-state graphs | Complete enumeration, no seed |
| Designed banks | 14 safety, 25 confidentiality, 25 response programs | Analytic templates; code and label explanations in `data/candidates.json` |
| Extensions A | All 3-, 4-, 5-state graphs: 2,744; 104,976; 5,153,632 | Complete enumeration |
| Extensions B | 483,641 programs of lengths 1–4; registers 0–1, constants 0–1 | Complete enumeration |
| Earlier sampled C | 50,000 per length 6, 8, 10, 12 | One `random.Random(20261013)` stream consumed sequentially across lengths |
| Simulation 1 | 8 checkers × 8 budgets; 5 benign programs per budget/checker | Source-dependent `hash(src)` coin rule; original process hash seed not recorded |
| Simulation 2 | 200,000 per length 4, 6, …, 24 | Separate stream `random.Random(20261020 * 1000 + L)` for each length |
| Simulation 3 | 3 designed generator programs × 6 horizons | No sampling |
| Simulation 4 | Regenerates the same population as Simulation 2 | Same per-length stream and instruction options |
| Simulation 5 | 4 supplied certifiers and their self-referential plans | No sampling |

For random register-machine programs, each of the first `L-1` instructions is drawn uniformly from the list of syntactically valid instruction options; the final instruction is drawn from returns and jumps. This induces a specific distribution over instruction sequences, not a uniform distribution over behaviours or deployed agents. The three registers available to sampled code are `r0`, `r1`, `r2`; the interpreter has four registers. Constants are 0–7. Sampling with replacement can repeat a program.

Reference runs use an initial budget of 5,000 transitions, followed where applicable by the specified stable-cycle check. An unresolved timeout is not labelled as divergence. Exact graph algorithms, complete runs, repeated complete configurations, stable-cycle arguments and the documented syntactic sufficient conditions supply labels. Simulation 5's lexical Python certifiers require the separate qualifications in `KNOWN_LIMITATIONS.md`.

## File groups

| Path under `reproducibility/` | Row count / role |
| --- | --- |
| `data/finite_models.csv` | 2,744 graphs and three binary labels |
| `data/finite_summary.csv` | 3 norm-level counts |
| `data/safety_observations.csv`, `safety_summary.csv` | 154 program/horizon observations; 11 summaries |
| `data/confidentiality_observations.csv`, `confidentiality_summary.csv` | 275 observations; 11 summaries |
| `data/response_observations.csv`, `response_summary.csv` | 300 observations; 12 summaries |
| `data/candidates.json` | All designed-bank program codes and analytic justifications |
| `data/protocol.json`, `summary.json` | Core parameters and aggregate counts |
| `data/runtime.json`, `sha256_manifest.json` | Historical Python metadata and core-file hashes |
| `data_extensions/separator_coverage.csv` | 9 rows: 3 state counts × 3 norms |
| `data_extensions/small_programs_summary.csv`, `small_programs_meta.json` | 18 norm/horizon rows and supporting diagnostics |
| `data_sampled/sampled_programs_summary.csv`, `sampled_programs_meta.json` | 72 length/norm/horizon rows and provenance |
| `sim1_adversary_results.csv`, `sim1_benign_benchmark.csv` | 64 adversary rows; 320 benign benchmark rows |
| `sim2_landscape.csv`, `sim2_first_bad_meta.json` | 121 aggregate rows; first-violation histograms by length |
| `sim2_required_horizon.csv` | 11 rows of first-violation percentiles and tested error-free horizons |
| `sim3_open_problem_results.csv` | 18 plan/horizon rows; wall times are measurements |
| `sim4_plateau_breakdown.csv` | 33 length/horizon rows |
| `sim5_rulebook_sized_omission.csv` | 4 certifier/omitted-program rows |
| `verification_record.json` | Historical core verification record from the supplied ZIP, not the new full-suite report |

## Common fields

| Field(s) | Meaning |
| --- | --- |
| `norm` | `safety`, `confidentiality` or `response` |
| `model_id`, `graph` | Enumeration index and JSON-encoded state-transition graph; states are `(event, successor)` pairs, with no successor for return states |
| `safety`, `confidentiality`, `response` in finite-model records | 1 = permitted, 0 = forbidden |
| `horizon`, `H`, `T` | Declared transition/yield budget; `T` is the bounded safety budget in Simulation 1 |
| `length` | Number of register-machine instructions |
| `states`, `models` | State count; size of the complete finite-model population |
| `programs`, `total` | Population size for that aggregate row; repeated across horizons, not new independent samples |
| `permitted`, `forbidden`, `unresolved` | Reference-label counts; they sum to `programs` in program-population summaries |
| `true_permitted`, `true_forbidden` | Corresponding counts in the designed-bank summaries |
| `candidate` | Designed-program identifier, joined to `data/candidates.json` |
| `truth_permitted` | Reference membership; 0/1 in core data, `True`/`False` strings in generator-experiment CSVs |
| `naive_permitted`, `verdict_permitted` | Binary verdict of a bounded test/checker, with the corresponding encoding |
| `certificate_status` | `permitted`, `forbidden` or `unknown` in designed-bank observations |
| `false_permissions` | Forbidden reference-labelled programs permitted by the binary test |
| `false_prohibitions` | Permitted reference-labelled programs forbidden by the binary test |
| `certified`, `safety_certified`, `conf_certified` | Resolved programs assigned a definite verdict by the partial certificate method |
| `certificate_unknown` | Designed-bank programs for which the certificate fragment abstains |
| `certificate_errors` | Disagreements of definite certificate verdicts with available reference labels in that population; zero observed errors is not a proof beyond the validated class |
| `bad_steps` | JSON list of observed forbidden-event steps |
| `public_0`, `public_1` | JSON lists of bounded public outputs for the two secret inputs |
| `halted`, `halted_0`, `halted_1` | Whether the specified bounded execution returned |
| `input_count` | Number of tested response inputs, `0` through `input_count-1` |
| `timed_out_inputs` | JSON list of tested inputs that did not return within the observation budget |
| `proved_cycle_inputs` | JSON list of inputs for which a complete nonterminal configuration repeated |
| `separator`, `admitted`, `unsound_admissions` | Syntactic admission-set description, number admitted, and admitted-but-forbidden count |
| `coverage_percent` | `100 * admitted / permitted` in finite separator experiments |
| `checker`, `program` | Checker identifier; benign or open-problem plan identifier |
| `correct` | Whether a checker verdict agrees with its reference label |
| `cost`, `checker_cost_steps`, `cost_over_T` | Checker yield count and that count divided by budget T; not wall time |
| `adversary_chars`, `certifier_chars`, `omitted_program_chars`, `overhead_chars` | Python-source character counts and difference; not the theorem's encoded bit lengths |
| `bad_step`, `bad_observed` | First observed forbidden-event step (empty when absent); whether an event was observed |
| `wall_truth_s`, `wall_checker_s`, `wall_s` | Measured seconds; excluded from deterministic scientific comparisons |
| `bounded_test_verdict` | `permitted` or `forbidden` in Simulation 3 |
| `safety_permitted`, `safety_forbidden`, `safety_unresolved` | Simulation 2 safety reference counts |
| `conf_permitted`, `conf_forbidden`, `conf_unresolved` | Simulation 2 confidentiality reference counts |
| `safety_false_permissions`, `conf_false_permissions`, `conf_false_prohibitions` | Corresponding Simulation 2 error counts |
| `unsafe_programs`, `median_first_bad`, `p99`, `p999`, `max_first_bad` | Number of unsafe programs and order statistics of their first violation |
| `min_errorfree_horizon_tested` | Smallest tested horizon from which every later tested horizon has no observed safety false permissions for that length; not a universal safe horizon |
| `both_halted`, `some_run_publishes_forever`, `both_publish_forever` | Counts among the falsely prohibited compliant cases in Simulation 4 |
| `compliant_both_halted_within_H`, `compliant_both_halted_within_H_errors` | Compliant cases with both runs returned by H, and errors restricted to those cases |
| `certifier`, `certifies_q`, `q_bad_within_1e5`, `q_returned`, `bank_verdicts` | Simulation 5 method; its verdict on q; bounded behaviour of q; and a Python-dictionary representation of benchmark verdicts |

CSV Boolean strings must be parsed explicitly; `bool("False")` evaluates to `True` in Python. Empty event-step cells mean “not observed,” not step zero. `bank_verdicts` is a Python literal, not JSON; use `ast.literal_eval` if parsing is needed.

## Denominators and percentiles

- Figure 4(a): `100 * safety_false_permissions / safety_forbidden`.
- Figure 4(b): `100 * conf_false_prohibitions / conf_permitted`.
- Certificate coverage in the earlier program experiments: `100 * certified / (programs - unresolved)`.
- The earlier supplemental experiments figure expresses false permissions per 10,000 sampled programs, using `programs` as denominator; do not confuse it with Figure 4(a)'s conditional percentage.
- First-violation percentiles use the value at zero-based index `floor((n-1)*p)` of the sorted histogram-expanded sample, for p = 0.5, 0.99 or 0.999. `scripts/derive_horizons.py` implements the equivalent weighted order statistic without NumPy. This lower-percentile convention can place slightly less than the nominal fraction at or below a reported percentile in small samples with a gap.

Repeated horizon rows describe the **same** program population and must not be summed as independent sampled programs.
