import subprocess
import sys
import os
from pathlib import Path
import time

def run_script(script_path):
    """Runs a python script and waits for it to finish."""
    print(f"\n{'='*50}")
    print(f"RUNNING: {os.path.basename(script_path)}")
    print(f"{'='*50}\n")
    
    start_time = time.time()
    try:
        # Using sys.executable to ensure we use the same environment
        result = subprocess.run([sys.executable, script_path], check=True)
        end_time = time.time()
        print(f"\n[SUCCESS] {os.path.basename(script_path)} finished in {end_time - start_time:.2f} seconds.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {os.path.basename(script_path)} failed with return code {e.returncode}.")
        return False

def main():
    # Get the directory of this script (crawl/)
    crawl_dir = Path(__file__).parent.absolute()
    os.chdir(crawl_dir)

    print("Starting AITF UGM Tim 3 Scraping Pipeline...")
    
    # Define Pipelines
    # Define Pipelines
    pipelines = {
        "1": {
            "name": "Regulation Pipeline (peraturan.go.id)",
            "scripts": [
                "peraturan_go_id_rekapitulasi.py",
                "peraturan_go_id_all.py",
                "peraturan_go_id_perda_links.py",
                "peraturan_go_id_perda.py",
                "peraturan_go_id_pdf_metadata.py",
                "peraturan_go_id_batch_pdf_download.py"
            ]
        },
        "2": {
            "name": "Siaran Pers Pipeline (Komdigi + General + Cleaning)",
            "scripts": [
                "siaran_pers_komdigi_links.py",
                "siaran_pers_komdigi_remove_duplicates.py",
                "siaran_pers_komdigi.py",
                "siaran_pers_general_links.py",
                "siaran_pers_general.py",
                "siaran_pers_cleaning.py"
            ]
        },
        "3": {
            "name": "Wikipedia Pipeline",
            "scripts": [
                "wikipedia_links.py",
                "wikipedia.py"
            ]
        }
    }

    print("\nSelect Pipeline to run:")
    print("1. Regulation Pipeline (peraturan.go.id)")
    print("2. Siaran Pers Pipeline (Komdigi + General + Cleaning)")
    print("3. Wikipedia Pipeline")
    print("4. Run ALL (1 -> 2 -> 3)")
    print("Q. Quit")

    choice = input("\nEnter choice: ").strip().lower()

    selected_scripts = []
    if choice == '1':
        selected_scripts = pipelines["1"]["scripts"]
    elif choice == '2':
        selected_scripts = pipelines["2"]["scripts"]
    elif choice == '3':
        selected_scripts = pipelines["3"]["scripts"]
    elif choice == '4':
        selected_scripts = (
            pipelines["1"]["scripts"] + 
            pipelines["2"]["scripts"] + 
            pipelines["3"]["scripts"]
        )
    elif choice == 'q':
        return
    else:
        print("Invalid choice.")
        return

    for script in selected_scripts:
        script_path = crawl_dir / script
        if not script_path.exists():
            print(f"Critical Error: Script {script} not found at {script_path}")
            break
        
        if not run_script(str(script_path)):
            print("\nPipeline stopped due to error in the previous step.")
            break

    print("\nPipeline execution finished!")

if __name__ == "__main__":
    main()
