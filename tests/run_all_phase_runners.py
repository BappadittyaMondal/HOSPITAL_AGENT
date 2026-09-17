"""
Master Sequential Phase Runner Verifier
Executes each phase's dedicated run_all_phaseXX_tests.py sequentially.
Ensures every individual Quality Gate runner passes with 100% exit code 0.
"""

import os
import sys
import subprocess

def test_all_master_runners():
    base_dir = os.path.dirname(__file__)
    passed_count = 0
    failed_count = 0

    for i in range(1, 19):
        phase_str = f"phase{i:02d}"
        runner_file = os.path.join(base_dir, phase_str, f"run_all_{phase_str}_tests.py")
        if not os.path.exists(runner_file):
            print(f"[MISSING] {runner_file} does not exist!")
            failed_count += 1
            continue

        cmd = [sys.executable, runner_file]
        repo_root = os.path.abspath(os.path.join(base_dir, ".."))
        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[PASS] Phase {i:02d} Master Runner ({phase_str}) -> 100% Passed")
            passed_count += 1
        else:
            print(f"[FAIL] Phase {i:02d} Master Runner FAILED with returncode {result.returncode}")
            print("STDOUT:", result.stdout[-500:])
            print("STDERR:", result.stderr[-500:])
            failed_count += 1

    print("=" * 80)
    print(f"MASTER RUNNER RESULTS: {passed_count} Passed / {failed_count} Failed out of 18 Phases")
    print("=" * 80)
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    sys.exit(test_all_master_runners())
