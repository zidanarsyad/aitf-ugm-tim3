"""
crawl/pipeline.py
Main CLI orchestrator for the AITF UGM Tim 3 Scraping Pipeline.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path for direct execution
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def run_script(script_path: Path) -> bool:
    """Run a python script synchronously and wait for it to finish."""
    name = script_path.name
    print(f"\n{'='*50}")
    print(f"RUNNING: {name}")
    print(f"{'='*50}\n")
    
    # Ensure current project root is in PYTHONPATH for the child process
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root_dir) + os.pathsep + env.get("PYTHONPATH", "")

    start_time = time.time()
    try:
        # Using sys.executable to ensure we use the same Python env
        subprocess.run([sys.executable, str(script_path)], check=True, env=env)
        elapsed = time.time() - start_time
        print(f"\n[SUCCESS] {name} finished in {elapsed:.2f} seconds.")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"\n[ERROR] {name} failed with return code {exc.returncode}.")
        return False


def main() -> None:
    # Ensure working directory is project root
    crawl_dir = Path(__file__).parent.resolve()
    os.chdir(crawl_dir.parent)

    print("Starting AITF UGM Tim 3 Scraping Pipeline...")
    
    pipelines = {
        "1": {
            "name": "Regulation Pipeline (peraturan.go.id)",
            "scripts": [
                crawl_dir / "peraturan_go_id_rekapitulasi.py",
                crawl_dir / "peraturan_go_id_all.py",
                crawl_dir / "peraturan_go_id_batch_pdf_download.py",
                crawl_dir / "peraturan_go_id_pdf_metadata.py",
            ]
        },
        "2": {
            "name": "Komdigi News Pipeline",
            "scripts": [
                crawl_dir / "siaran_pers_komdigi_links.py",
                crawl_dir / "siaran_pers_komdigi.py",
            ]
        },
        "3": {
            "name": "General News Pipeline (BAPPENAS, BGN, ESDM)",
            "scripts": [
                crawl_dir / "siaran_pers_general_links.py",
                crawl_dir / "siaran_pers_general.py",
            ]
        },
        "4": {
            "name": "OCR & Autocorrect Pipeline",
            "scripts": [
                crawl_dir / "ocr" / "pipeline.py",
            ]
        }
    }

    print("\nSelect Pipeline to run:")
    print("1. Regulation Pipeline (Rekap -> Scrape -> Download PDF -> Metadata)")
    print("2. Komdigi News Pipeline (Links -> Scrape Content)")
    print("3. General News Pipeline (Links -> Scrape Content)")
    print("4. OCR Pipeline (Extract Text -> Autocorrect Indonesian)")
    print("5. Run EVERYTHING (1 + 2 + 3 + 4)")
    print("Q. Quit")

    choice = input("\nEnter choice: ").strip().lower()

    if choice == '1':
        selected = pipelines["1"]["scripts"]
    elif choice == '2':
        selected = pipelines["2"]["scripts"]
    elif choice == '3':
        selected = pipelines["3"]["scripts"]
    elif choice == '4':
        selected = pipelines["4"]["scripts"]
    elif choice == '5':
        selected = pipelines["1"]["scripts"] + pipelines["2"]["scripts"] + pipelines["3"]["scripts"] + pipelines["4"]["scripts"]
    elif choice == 'q':
        return
    else:
        print("Invalid choice.")
        return

    for script_path in selected:
        if not script_path.exists():
            print(f"Critical Error: Script {script_path.name} not found at {script_path}")
            sys.exit(1)
        
        if not run_script(script_path):
            print("\nPipeline stopped due to error in the previous step.")
            sys.exit(1)

    print("\nPipeline execution finished!")


if __name__ == "__main__":
    main()
