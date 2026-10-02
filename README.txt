ONLINE RESOURCE 1 - SUPPLEMENTARY REPRODUCIBILITY ARTIFACT
Article title: Fallback-Preserving Partial Identification for Asynchronous Routing-Security Measurements: Sharp Robust Quorum Bounds for ASPA-BGP Measurement
Journal: Telecommunication Systems
Author: Huynh Anh Khiem
Affiliation: Faculty of Information Technology, Ton Duc Thang University, Ho Chi Minh City, Vietnam
Corresponding author: huynhanhkhiem@tdtu.edu.vn
ORCID: 0009-0007-7210-174X

PURPOSE
This artifact reproduces the numerical and algorithmic claims reported in the accompanying manuscript. It implements sharp event-level duration bounds, event-specific threshold decision boundaries, threshold-exceedance bounds, separable k-of-M quorum classification, an optional shared-event coupling model with bounded source delays, an outlier-robust coupled quorum count envelope and exact attainable count set that allow up to q invalid source-to-common-event constraints without discarding source-local evidence, a support-only fusion insufficiency counterexample showing that common-time support alone cannot recover the sharp downstream quorum extrema, deterministic local/separable/coupled stress tests, strict-versus-robust coupling-contamination tests, an adversarially stratified q-sensitivity test, a held-out conformal calibration rule for prespecifying q from trusted historical events, a coupling-tension diagnostic, a cross-configuration M/k/q generalization grid, an implementation-independent exhaustive-oracle audit of the exact attainable count set, a separate exhaustive audit of the nonnegative weighted-score extension, the eight-day ASPA snapshot differencing used for the source-local illustration, exact point-resolution budgets, a decision-level coupling-relaxation certificate, and dedicated endpoint-closure and boundary-semantics regressions.

VALIDATION AND FULL REGENERATION
1. Use Python 3.11 or later. The final package was validated with Python 3.13.5.
2. Install dependencies:
   pip install -r requirements.txt
3. Fast validation of the packaged outputs and complete test suite:
   ./RUN_ARTIFACT_VALIDATION.sh
4. Full from-zero regeneration followed by the same validation:
   ./REGENERATE_AND_VALIDATE.sh

A successful validation recomputes or checks the broadened grid and oracle audit and ends with:
   REPORTED_RESULTS=PASS
   Q_SENSITIVITY_VALIDATION=PASS
   Q_CALIBRATION_VALIDATION=PASS
   TECHNICAL_QA=PASS
   ARTIFACT_VALIDATION=PASS

WHAT FULL REGENERATION RECREATES
- data/output/aspa_changes_2026-08-26_09-02.json
- data/output/synthetic_identification_stress.csv
- data/output/synthetic_identification_stress.summary.json
- data/output/synthetic_quorum_stress.csv
- data/output/synthetic_quorum_stress.summary.json
- data/output/synthetic_coupled_quorum_stress.csv
- data/output/synthetic_coupled_quorum_stress.summary.json
- data/output/synthetic_coupled_quorum_generalization.summary.json
- data/output/synthetic_robust_coupling_stress.csv
- data/output/synthetic_robust_coupling_stress.summary.json
- data/output/adversarial_q_sensitivity.summary.json
- data/output/conformal_q_calibration.summary.json
- data/output/synthetic_coupling_tension_stress.csv
- data/output/synthetic_coupling_tension_stress.summary.json
- data/output/robust_generalization_grid.csv
- data/output/robust_generalization_grid.summary.json
- data/output/exact_oracle_validation.summary.json
- data/output/weighted_oracle_validation.summary.json
- data/output/pilot_bracket_reclassification_1h.json

SCIENTIFIC BOUNDARY
The primary contribution is a partial-identification method for asynchronous cross-plane timing and downstream quorum decisions. Classical interval intersection and q-relaxed intersection are treated as prior support primitives, not as novel algorithms. The latent A in the method is a source-local observed authorization-state transition, not operator intent, CMS signing time, or an assumed global commit time. The synthetic experiments validate both separable and delay-coupled implementations against known latent truth. Shared-event coupling is used only when lineage and source-delay envelopes are justified independently. The robust q model is a sensitivity model, not a data-selected hyperparameter: every source-local bracket remains valid, while up to q source-to-common-event delay constraints may be invalid and revert to their local evidence. The identity of relaxed constraints is not estimated from the desired outcome. Operationally, q should be fixed before inspecting the downstream label. It may come from provenance/engineering assumptions, a reported q-sensitivity path, or the included held-out conformal calibration rule: on trusted calibration events, count how many source-to-common-event constraints exclude the trusted event time and take the finite-sample upper conformal quantile of that violation count. Under exchangeability, this prespecifies a future q with marginal coverage at least 1-alpha; the artifact separately stress-tests deliberate distribution shift to expose the assumption boundary. The artifact includes an adversarial q stress test showing that underspecifying q can produce resolved errors, while valid q values preserve truth in the generator at the cost of wider ambiguity. The eight-day operational illustration is deliberately limited to A1-S-conditional source-local resolution-sensitivity diagnostics; daily snapshots cannot exclude hidden intra-bracket reversals, and the illustration makes no unconditional sharp field-identification, provider-concentration, or prevalence claim. Its embedded CMS signing-time probe is not treated as a trusted first-observation clock and is not used to estimate Internet-wide ASPA misconfiguration or confirmed temporal-gap prevalence.

PACKAGED INPUTS
- data/input/aspa_snapshots_2026-08-26_09-02.json: archived ASPA snapshot extraction used to reconstruct daily U-SPAS changes in the illustration window.
- data/input/pilot_signing_time_probe_1h.csv: archived processed BGP/signing-time candidate table used only for the source-local illustration.

The source-local input table is processed evidence rather than raw MRT traffic. This distinction is intentional and is disclosed because the manuscript makes no full-population or raw-MRT prevalence claim from the pilot. All 12 packaged candidate probes lie strictly inside their covered daily RPKI endpoint brackets. Their reported resolution margins are conditional on the single-transition support model; hidden within-day reversals are not excluded by the daily snapshots.

KEY IMPLEMENTATION FILES
- code/interval_identification.py: sharp event bounds, exceedance envelope, separable/strict-coupled/robust-coupled k-of-M quorum rules, q-relaxed transition support, the fast exact robust-extrema evaluator, a dynamic program for the exact attainable robust count set, and a coupling-relaxation decision certificate.
- tests/test_interval_identification.py: deterministic and randomized sharpness checks, including exact-count-set agreement with explicit relaxed-subset enumeration, extrema agreement, a non-convex count-set witness, and the Proposition 10 support-only-fusion insufficiency witness. tests/test_boundary_and_relaxation.py locks closed transition-bracket endpoints, BGP end exclusivity, strict threshold equality, all-q boundary oracle agreement, zero-weight behavior, and the coupling-relaxation certificate.
- code/synthetic_identification_stress.py: two-million-case source-local stress test.
- code/synthetic_quorum_stress.py: 500,000-event separable eight-source, five-of-eight quorum regression stress test.
- code/synthetic_coupled_quorum_stress.py: 100,000-event shared-latent-transition stress test for exact delay-coupled quorum identification.
- code/synthetic_coupled_quorum_generalization.py: 90,000-event strict-coupling generalization stress spanning M={4,6,8,12,16}, 18 configuration-width cells, and quorum thresholds from 3-of-4 to 12-of-16; it checks feasibility, truth agreement of every resolved decision, non-reversal of separably resolved labels, and ambiguity reduction.
- code/synthetic_robust_coupling_stress.py: 50,000-event strict-versus-q=1 coupling-misspecification stress test (10,000 events at each of five displacements).
- code/conformal_q_calibration.py: finite-sample held-out calibration of q from trusted event-level coupling-violation counts, with an exchangeable coverage check and an explicit distribution-shift failure stress.
- code/adversarial_q_sensitivity.py: adversarially stratified q-sensitivity validation cycling all eight single-contamination identities and both displacement signs, plus balanced two-contamination strata. It demonstrates the expected safety/ambiguity trade-off when q is prespecified at, below, or above the actual number of invalid coupling constraints.
- code/synthetic_coupling_tension_stress.py: 100,000-event auxiliary contamination stress test for strict shared-event incompatibility and uniform feasibility slack.
- code/robust_generalization_grid.py: 81,000-event cross-configuration validation over M={4,8,16}, q={0,1,2}, three bracket widths, three thresholds, both transition directions, and quorum levels near one-third/one-half/two-thirds; 216,000 quorum decisions.
- code/exact_oracle_validation.py: 30,000-instance implementation-independent exhaustive oracle that reimplements local duration geometry, conditional intersections, and the strict theta grid, enumerates relaxed-source identities, samples q over 0..M, and compares both the exact count set and its extrema with the production dynamic program and the direct O(M^2) extrema evaluator.
- code/weighted_oracle_validation.py: 20,000-instance independent exhaustive relaxed-identity audit of the nonnegative weighted-score extrema with q sampled over 0..M and integer weights including zero.
- code/robust_oracle_common.py: oracle-only local geometry deliberately independent of the production identification module.
- code/aspa_semantics.py: tri-state ASPA semantics and path helpers.
- code/build_global_event_lineage.py: source-change-key lineage rule for repeated cross-vantage events.
- code/diff_aspa_timeseries.py: daily U-SPAS snapshot differencing for the source-local illustration window.
- code/classify_pilot_bracket_evidence.py: reclassifies the 12 signing-time candidates using only daily last-before/first-after snapshot brackets.
- code/validate_reported_results.py: fail-closed checks against all manuscript table/text numbers.

REPRODUCIBILITY NOTES
The final package was validated with Python 3.13.5, numpy 2.3.5, and pytest 9.0.2; requirements.txt pins the two external Python dependencies exactly. Legacy/headline synthetic generators use seed 20260914; the strict-coupling generalization grid, robust generalization grid, and exact-count oracle use seed 20260915; the weighted-score oracle uses seed 20260916. The release outputs were regenerated from an empty output directory before packaging. The packaged test suite contains 79 tests, including ten dedicated endpoint-closure/boundary/relaxation regressions. RUN_ARTIFACT_VALIDATION.sh checks the packaged outputs fail-closed against manuscript numbers and runs all tests; REGENERATE_AND_VALIDATE.sh provides the full regeneration path. PROVENANCE_SHA256.txt records hashes of both packaged empirical inputs. Direct `python -m pytest -q tests` execution is also supported from the artifact root.
