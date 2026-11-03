"""Run both test environments from the project root."""
import subprocess
from scripts.paths import ROOT
engine={'test_fcs_export','test_fcs_combine','test_gate_edit'}
all_tests={p.stem for p in (ROOT/'scripts/tests').glob('test_*.py')}
for python,names in [('.venv/bin/python',all_tests-engine),('.fcs-venv/bin/python',engine)]:
 result=subprocess.run([str(ROOT/python),'-m','unittest',*['scripts.tests.'+n for n in sorted(names)]],cwd=ROOT)
 if result.returncode:raise SystemExit(result.returncode)
