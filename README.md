# Fallback-Preserving Partial Identification for ASPA-BGP Measurement

[![Reproducibility validation](https://github.com/huynhanhkhiem-dms/-aspa-bgp-partial-identification/actions/workflows/reproducibility.yml/badge.svg)](https://github.com/huynhanhkhiem-dms/-aspa-bgp-partial-identification/actions/workflows/reproducibility.yml)

Reproducibility repository for the manuscript:

**Fallback-Preserving Partial Identification for Asynchronous Routing-Security Measurements: Sharp Robust Quorum Bounds for ASPA-BGP Measurement**

- Author: Huynh Anh Khiem
- Affiliation: Faculty of Information Technology, Ton Duc Thang University, Ho Chi Minh City, Vietnam
- ORCID: 0009-0007-7210-174X
- Target journal: *Telecommunication Systems*

## Scope

This repository contains the processed empirical inputs, analysis code, deterministic synthetic generators, oracle validators, automated tests, and packaged outputs used to reproduce the numerical and algorithmic claims reported in the manuscript.

The eight-day ASPA-BGP operational illustration supports only A1-S-conditional source-local resolution-sensitivity claims. Daily snapshots do not exclude hidden intra-bracket reversals. The robust multi-source layer is validated by proof, latent-truth stress tests, and implementation-independent exhaustive oracles rather than by a coupled field-prevalence study.

## Quick start

Requirements:

- Python 3.11 or later
- Final validation environment: Python 3.13.5
- `numpy==2.3.5`
- `pytest==9.0.2`

Install dependencies:

```bash
pip install -r requirements.txt
```

Validate the packaged outputs and test suite:

```bash
./RUN_ARTIFACT_VALIDATION.sh
```

Regenerate outputs from zero and validate:

```bash
./REGENERATE_AND_VALIDATE.sh
```

A successful validation ends with:

```text
REPORTED_RESULTS=PASS
TECHNICAL_QA=PASS
ARTIFACT_VALIDATION=PASS
```

The release package contains **79 automated tests**.

## Repository structure

```text
code/                  Analysis and validation code
data/input/            Packaged processed empirical inputs
data/output/           Reproduced numerical outputs
tests/                 Automated tests
README.txt             Original supplementary-artifact README
DATA_CONTRACTS.txt     Data-format contracts
METHOD_SPECIFICATION.txt
REFERENCES.txt
PROVENANCE_SHA256.txt  SHA-256 hashes of empirical inputs
requirements.txt       Pinned Python dependencies
RUN_ARTIFACT_VALIDATION.sh
REGENERATE_AND_VALIDATE.sh
```

## Packaged empirical inputs

- `data/input/aspa_snapshots_2026-08-26_09-02.json` — archived ASPA snapshot extraction used to reconstruct daily U-SPAS changes in the illustration window.
- `data/input/pilot_signing_time_probe_1h.csv` — archived processed BGP/signing-time candidate table used only for the source-local illustration.

The BGP/signing-time table is **processed evidence rather than raw MRT traffic**. Raw MRT traffic is not redistributed here. The manuscript's operational claims are limited to what can be reproduced from the packaged processed evidence.

## Provenance

Input hashes are recorded in `PROVENANCE_SHA256.txt`:

```text
4a4fdf1a71ebbc651ebf88f77fcfa2791e3eaa1b113cbf8d0cce1a1b816652e5  data/input/aspa_snapshots_2026-08-26_09-02.json
a6583371e906c52ba7fe7c38596800dc7aa1375dac03be5b6dffdcfda8de4a85  data/input/pilot_signing_time_probe_1h.csv
```

## Reproducibility boundary

Classical interval intersection and q-relaxed intersection are treated as prior support primitives, not as novel algorithms. The method's latent event refers to a source-local observed authorization-state transition, not operator intent, CMS signing time, or an assumed global commit time. Shared-event coupling is used only when lineage and source-delay envelopes are independently justified. The robust `q` model is a sensitivity model and should be prespecified before inspecting the downstream label.

See `README.txt` and `METHOD_SPECIFICATION.txt` for the complete scientific boundary and implementation details.

## Data and code availability statement

The processed evidence required for the reported operational calculations, input hashes, source code, automated tests, deterministic generators, oracle validators, reported-output validators, and full regeneration instructions are contained in this repository. Raw MRT traffic is not redistributed.

## License note

No repository-wide license is added in this release because the supplied artifact does not document a single license covering all code and third-party-derived data. The repository owner should add an appropriate code license and any required data-source attribution/license notice only after confirming the applicable redistribution terms.
