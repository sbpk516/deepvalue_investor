import pytest
import json
import os
import subprocess


class TestMainPipeline:
    def test_pipeline_runs_without_errors(self, tmp_path):
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        env["DB_PATH"] = str(tmp_path / "test.db")
        env["OUTPUT_DIR"] = str(tmp_path / "output/")
        env["LOG_DIR"] = str(tmp_path / "logs/")
        env["CACHE_DIR"] = str(tmp_path / "cache/")
        result = subprocess.run(
            ["python3", "-m", "pipeline.main", "--test"],
            capture_output=True, text=True, timeout=120,
            env=env,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )
        assert result.returncode == 0, f"Pipeline failed: {result.stderr}"

    def test_creates_results_json(self, tmp_path):
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        env["DB_PATH"] = str(tmp_path / "test.db")
        env["OUTPUT_DIR"] = str(tmp_path / "output/")
        env["LOG_DIR"] = str(tmp_path / "logs/")
        env["CACHE_DIR"] = str(tmp_path / "cache/")
        subprocess.run(
            ["python3", "-m", "pipeline.main", "--test"],
            capture_output=True, text=True, timeout=120,
            env=env,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )
        output_path = os.path.join(str(tmp_path / "output"), "results.json")
        assert os.path.exists(output_path)
        with open(output_path) as f:
            results = json.load(f)
        assert "candidates" in results
        assert "stats" in results
        # With real layers, candidates may be filtered — just verify structure
        assert isinstance(results["candidates"], list)
        assert "stocks_screened" in results["stats"]
