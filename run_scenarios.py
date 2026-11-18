"""
Run the five Part D scenarios against the configured model and write results/.

    python run_scenarios.py              # writes results/scenarios.{json,md} + scenario_log.json
    python run_scenarios.py --out DIR    # keep a run in another directory

Exit code 0 if every scenario matched its expectation, 1 otherwise. See src/scenarios.py.
"""

from src.scenarios import main

if __name__ == "__main__":
    raise SystemExit(main())
