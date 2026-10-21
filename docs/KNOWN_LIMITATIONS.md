# Confirmed limitations of the supplied v14 materials

These notes separate faithful reproduction of archived computations from validity of an interpretation. Original scientific sources/data are retained; their semantics have not been silently changed. Issues below should be resolved in a new version, or disclosed when the historical snapshot is released.

## 1. Process-dependent coin-flip rows

`sim1_diagonal_gatekeeper.py` seeds the checker with `random.Random(hash(src) & 0xffff)`. Python string hashes normally vary between processes. A fixed `random.Random` constructor therefore does not make the original script reproducible across arbitrary process launches. The generating process's `PYTHONHASHSEED` was not recorded.

The added driver fixes `PYTHONHASHSEED=0` for new subprocesses and reports differences in the archived `coin_flip` rows separately. Wall-clock columns are also excluded from scientific comparisons. The historical coin rows cannot be described as byte-reproducible from the supplied provenance. This checker is a deterministic, source-dependent pseudorandom rule within a process, not an experiment over fresh independent coin flips on repeated executions.

## 2. Collatz cutoff is not a mathematical counterexample

In `sim3_open_problem_programs.py`, the Collatz plan performs `BAD` if a trajectory has taken more than `10**7` iterations without reaching 1. Exceeding a finite iteration cutoff does not prove a cycle or divergence: a trajectory might reach 1 later. The supplied implementation therefore does not establish that the plan's safety is equivalent to the Collatz conjecture. Matching its CSV cannot repair that interpretation.

The Goldbach and control computations are preserved as supplied. Their steps count generator yields, with potentially extensive Python work between yields; they are not register-machine instruction counts.

## 3. Simulation 5 certifiers are not all globally sound for Python

Three advertised certifiers accept a program that performs `BAD` in the supplied execution environment:

| Certifier | Counterexample mechanism |
| --- | --- |
| `syntactic_no_bad` | `getattr(env, "bad")()` invokes the forbidden operation without the text `bad(` |
| `no_loops_no_bad` | The same straight-line alias passes both substring tests |
| `bad_only_in_dead_code_after_return` | A `return` in an unrelated helper function is mistaken for evidence that a later `env.bad()` in `run` is unreachable |

Run `python3 scripts/check_known_limitations.py` for the complete short programs and their observed bad-event steps. Each is certified and performs `BAD` at step 2. Passing the original three-program bank demonstrates behaviour on that bank; it does not establish global soundness. A restricted, formally defined syntax or a sound analyser is needed before using these methods as examples of universally sound certifiers. The omission demonstrations themselves still have the archived finite outcomes; finite observation alone does not prove that a program never acts.

## 4. A response-case proof requires correction

The manuscript appendix's permitted-response case of the rulebook-sized-omission proposition says to search for a certificate, diverge if found, and return otherwise. An unbounded unsuccessful search has no computable “otherwise” branch. That proof text does not supply the claimed program. A plausible repair is a program that, on input `n`, checks only certificate indices up to `n`, diverges if one verifies, and returns otherwise; this needs to be incorporated and checked in a manuscript revision. This observation is not a complete audit of the theorem or its size bound, and the historical manuscript has not been edited here.

## 5. Finite experiments do not establish universal or asymptotic claims

Random-program error rates concern the specified instruction distributions and resolved subsets. Neither zero sampled errors at a horizon nor a persistent sampled plateau proves a statement about every program, every horizon or deployed agents. The 2.2-million-program population does not store individual sampled code files; it is regenerated from the documented seed and instruction sampler. Source-character counts in Simulation 5 are not bit lengths under the theorem's specified coding system. In the generator environment, unmetered computation and code construction between yields prevent interpreting the experiment as a physical-computation lower-bound measurement.

## 6. Documentation/automation gaps addressed by this preparation

The supplied ZIP did not contain the README asserted in the manuscript, dependency instructions for Figure 4, a generator for `sim2_required_horizon.csv`, or one complete run sequence. Original Simulations 1 and 2 write into `sim1_out/` and `sim2_out/`, while figure scripts read flattened, prefixed filenames. The added driver harvests these files inside a generated workspace; the archived scripts are unchanged.

The original `build.py` compiled some figures and the manuscript but did not regenerate Figure 4 or all experiments. It is not distributed as the reproduction entry point. A stale log containing a failed local build and personal workspace paths is omitted. Duplicate PDFs are omitted where they add no source information. No changes to the original main manuscript, fixed environment, normative definitions or reference data are asserted.

## Publication status

This preparation establishes the checks listed in `VALIDATION.md`, not submission readiness of the manuscript. Mathematical claims beyond the observations above, novelty, citations, and the real-machine corollaries have not received a complete referee-level audit as part of the repository preparation. The full article source is not included in this upload package; original table fragments and Supplementary Document S1 are included for reproducibility.
