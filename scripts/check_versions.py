"""Check installed and locked package versions against Architecture.md baselines."""

import json
from pathlib import Path
import sys
from importlib.metadata import version as get_pkg_version

BASELINES = {
    # Backend
    "python": "3.12",
    "fastapi": "0.115+",
    "uvicorn": "0.30+",
    "pydantic": "2.x",
    "pydantic-settings": "2.x",
    "sqlalchemy": "2.0",
    "alembic": "1.x",
    "psycopg": "3.x",
    "psycopg-binary": "3.x",
    "argon2-cffi": "modern",
    "pyjwt": "2.x",
    "email-validator": "2.x",
    "httpx": "0.27+",
    "pytest": "latest",
    "pytest-asyncio": "latest",
    "ruff": "latest",
    "mypy": "latest",
    # Frontend
    "node": "22 LTS",
    "react": "19",
    "vite": "7 (or 6+)",
    "typescript": "5.x",
    "tailwindcss": "4.x",
    "zustand": "5.x",
    "three": "0.17x+",
    "@react-three/fiber": "9 (or 8/9)",
    "@react-three/drei": "latest",
    "vitest": "latest",
    "eslint": "latest",
}


def get_backend_versions():
    results = {"python": sys.version.split()[0]}
    packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "sqlalchemy",
        "alembic",
        "psycopg",
        "psycopg-binary",
        "argon2-cffi",
        "pyjwt",
        "email-validator",
        "httpx",
        "pytest",
        "pytest-asyncio",
        "ruff",
        "mypy",
    ]
    for pkg in packages:
        try:
            results[pkg] = get_pkg_version(pkg)
        except Exception:
            results[pkg] = "not installed"
    return results


def get_frontend_versions():
    results = {}
    lock_file = Path("frontend/package-lock.json")
    if not lock_file.exists():
        return results

    try:
        with open(lock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            packages = data.get("packages", {})
            for name in [
                "react",
                "vite",
                "typescript",
                "tailwindcss",
                "zustand",
                "three",
                "@react-three/fiber",
                "@react-three/drei",
                "vitest",
                "eslint",
            ]:
                key = f"node_modules/{name}"
                if key in packages:
                    results[name] = packages[key].get("version", "unknown")
                else:
                    results[name] = "not found"
    except Exception as e:
        results["error"] = str(e)
    return results


def main():
    print("=" * 70)
    print("VERDICT TECH STACK VERSION REPORT")
    print("=" * 70)
    print(f"{'Component / Package':<25} | {'Architecture Baseline':<20} | {'Actual Pinned':<18}")
    print("-" * 70)

    backend = get_backend_versions()
    for pkg, actual in backend.items():
        baseline = BASELINES.get(pkg, "n/a")
        print(f"{pkg:<25} | {baseline:<20} | {actual:<18}")

    frontend = get_frontend_versions()
    for pkg, actual in frontend.items():
        baseline = BASELINES.get(pkg, "n/a")
        print(f"{pkg:<25} | {baseline:<20} | {actual:<18}")

    print("=" * 70)


if __name__ == "__main__":
    main()

