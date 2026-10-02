#!/usr/bin/env python3
"""Regenerate all packaged outputs from zero and run fail-closed technical QA.

Independent generators execute sequentially in isolated Python processes.
This avoids shared interpreter state and CPU contention while keeping exact
scripts, inputs, seeds, and outputs. Any failed generator aborts the run.
"""
from __future__ import annotations
import json, os, py_compile, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/'code'
OUT=ROOT/'data'/'output'
OUT.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
    if p.is_file(): p.unlink()

base_env=os.environ.copy()
base_env['PYTHONPATH']=str(CODE)+(os.pathsep+base_env['PYTHONPATH'] if base_env.get('PYTHONPATH') else '')


def cmd(name: str, args: list[str]|None=None, extra_env: dict[str,str]|None=None):
    env=base_env.copy()
    if extra_env: env.update(extra_env)
    return name,[sys.executable,str(CODE/name)]+(args or []),env

jobs=[
    cmd('diff_aspa_timeseries.py',[str(ROOT/'data/input/aspa_snapshots_2026-08-26_09-02.json'),'--output',str(OUT/'aspa_changes_2026-08-26_09-02.json')]),
    cmd('synthetic_identification_stress.py'),
    cmd('synthetic_quorum_stress.py'),
    cmd('synthetic_coupled_quorum_stress.py'),
    cmd('synthetic_coupled_quorum_generalization.py'),
    cmd('synthetic_robust_coupling_stress.py'),
    cmd('adversarial_q_sensitivity.py'),
    cmd('conformal_q_calibration.py'),
    cmd('synthetic_coupling_tension_stress.py'),
    cmd('robust_generalization_grid.py'),
    cmd('exact_oracle_validation.py'),
    cmd('weighted_oracle_validation.py'),
    cmd('classify_pilot_bracket_evidence.py',[str(ROOT/'data/input/pilot_signing_time_probe_1h.csv'),'--output',str(OUT/'pilot_bracket_reclassification_1h.json')]),
]


def run_job(job):
    name,argv,env=job
    p=subprocess.run(argv,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    if p.returncode:
        raise RuntimeError(f'{name} failed ({p.returncode}):\n{p.stderr}')
    return name

print(f'RUN {len(jobs)} independent generators',flush=True)
for job in jobs:
    name=run_job(job)
    print(f'PASS {name}',flush=True)

# Manuscript-number validator.
print('RUN validate_reported_results.py',flush=True)
p=subprocess.run([sys.executable,str(CODE/'validate_reported_results.py')],cwd=ROOT,env=base_env,text=True)
if p.returncode: raise SystemExit(p.returncode)

q=json.loads((OUT/'adversarial_q_sensitivity.summary.json').read_text())
for key,ok in q['checks'].items():
    if not ok: raise SystemExit(f'Q_SENSITIVITY_CHECK_FAILED: {key}')
print('Q_SENSITIVITY_VALIDATION=PASS',flush=True)

c=json.loads((OUT/'conformal_q_calibration.summary.json').read_text())
for key,ok in c['checks'].items():
    if not ok: raise SystemExit(f'Q_CALIBRATION_CHECK_FAILED: {key}')
print('Q_CALIBRATION_VALIDATION=PASS',flush=True)

print('RUN pytest',flush=True)
import pytest
rc=pytest.main(['-q',str(ROOT/'tests')])
if rc: raise SystemExit(int(rc))

print('RUN py_compile',flush=True)
for p in list(CODE.glob('*.py'))+list((ROOT/'tests').glob('*.py'))+[ROOT/'conftest.py']:
    py_compile.compile(str(p),doraise=True)
print('TECHNICAL_QA=PASS',flush=True)
print('ARTIFACT_VALIDATION=PASS',flush=True)
