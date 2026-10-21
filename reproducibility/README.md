# Original simulation sources and data

Run `python3 reproduce.py --suite full` **from the repository root** for a complete rerun that preserves these archived files. The driver handles the original scripts' `sim1_out/` and `sim2_out/` paths and derives `sim2_required_horizon.csv`.

The data dictionary is in `../docs/DATA_DICTIONARY.md`. `verification_record.json` is a historical core verification record from the supplied ZIP. The new, broader check record is in `../docs/validation_results.json`.

Read `../docs/KNOWN_LIMITATIONS.md` before treating the newer demonstrations as evidence of global soundness or mathematical equivalence. The original sources are retained without silently changing their scientific meaning.
