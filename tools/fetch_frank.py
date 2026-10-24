#!/usr/bin/env python3
"""Alternative zum lokalen Export: FRANK herunterladen und Treiber exportieren.

Erfordert Internet, Git und passende Upstream-Version. Ein lokaler, bereits
getesteter FRANK-Klon ist fuer reproduzierbare Builds vorzuziehen.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
from vendor_frank import export

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="main", help="Branch, Tag oder Commit von FRANK-MICRO")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="frank_import_") as tmp:
        repo = Path(tmp) / "frank-micro"
        subprocess.run(["git", "clone", "--recurse-submodules",
                        "https://github.com/rh1tech/frank-micro.git", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "checkout", args.ref], check=True)
        subprocess.run(["git", "-C", str(repo), "submodule", "update", "--init", "--recursive"], check=True)
        export(repo)

if __name__ == "__main__":
    main()
