"""CLI entry point: `porgui --serve` (or `python -m porgui --serve`).

Launches the Streamlit UI as a subprocess, exactly the way the Dockerfile
already does (`streamlit run app.py ...`), so behavior stays predictable
across Streamlit versions.
"""
import argparse
import importlib.resources
import os
import subprocess
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(prog="porgui", description="Run the porgui Streamlit app.")
    parser.add_argument("--serve", action="store_true", help="Start the local web server (default action).")
    parser.add_argument("--port", type=int, default=8501, help="Port to serve on (default: 8501).")
    parser.add_argument("--host", default="localhost", help="Address to bind to (default: localhost).")
    parser.add_argument("--workspace", default=None, help="Directory to use for runs/ output (default: current directory).")
    args = parser.parse_args(argv)

    workspace = os.path.abspath(args.workspace) if args.workspace else os.getcwd()
    env = dict(os.environ)
    env["PORGUI_WORKSPACE"] = workspace

    app_path = importlib.resources.files("porgui") / "app.py"

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.port", str(args.port),
        "--server.address", args.host,
    ]
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
