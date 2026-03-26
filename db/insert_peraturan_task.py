import sqlite3
import json
import glob
import os
from datetime import datetime
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Paths
DB_PATH = r'd:\1_projects\aitf-ugm-tim3\db\peraturan.db'
DB_DIR = r'd:\1_projects\aitf-ugm-tim3\db'

def get_now():
    return datetime.now().isoformat()

def insert_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = get_now()

    with Progress(
        # SpinnerColumn(spinner_name="dots"),
        # Progress bar with description, percentage and time elapsed
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:

        # 1. Process Rekapitulasi for 'urls' table
        rekap_files = glob.glob(os.path.join(DB_DIR, 'peraturan_go_id_rekapitulasi_*.json'))
        rekap_task = progress.add_task("[green]Processing Rekapitulasi...", total=len(rekap_files))

        for file_path in rekap_files:
            filename = os.path.basename(file_path)
            # Extract {p} from 'peraturan_go_id_rekapitulasi_{p}.json'
            p = filename.replace('peraturan_go_id_rekapitulasi_', '').replace('.json', '')
            
            progress.update(rekap_task, description=f"[green]Rekap: [bold]{p}[/]")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    progress.console.print(f"[bold red]Skipping {filename} due to JSON error.[/]")
                    progress.advance(rekap_task)
                    continue

                for entry in data:
                    tahun = entry.get('tahun')
                    try:
                        jumlah = int(entry.get('jumlah_peraturan', 0))
                    except (ValueError, TypeError):
                        jumlah = 0
                    
                    urls_to_insert = []
                    for nomor in range(1, jumlah + 1):
                        url = f"https://peraturan.go.id/id/{p}-no-{nomor}-tahun-{tahun}"
                        urls_to_insert.append((url, p, 0, now, now))
                    
                    # Batch insert to urls (ignore duplicates)
                    cursor.executemany('''
                        INSERT OR IGNORE INTO urls (url, peraturan, status, date_created, date_modified)
                        VALUES (?, ?, ?, ?, ?)
                    ''', urls_to_insert)

            progress.advance(rekap_task)

        conn.commit()
        progress.console.print("[cyan]Finished inserting into 'urls' table.[/]")

        # 2. Process 'all' files for 'pages' table
        all_files = glob.glob(os.path.join(DB_DIR, 'peraturan_go_id_all_*.json'))
        pages_task = progress.add_task("[yellow]Processing 'all' files (pages)...", total=len(all_files))

        for file_path in all_files:
            filename = os.path.basename(file_path)
            # Extract {p} from 'peraturan_go_id_all_{p}.json'
            p = filename.replace('peraturan_go_id_all_', '').replace('.json', '')
            
            progress.update(pages_task, description=f"[yellow]All: [bold]{p}[/]")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    progress.console.print(f"[bold red]Skipping {filename} due to JSON error.[/]")
                    progress.advance(pages_task)
                    continue

                if not isinstance(data, list):
                    progress.advance(pages_task)
                    continue

                pages_to_insert = []
                for entry in data:
                    nomor = entry.get('nomor')
                    tahun = entry.get('tahun')
                    
                    if not nomor or not tahun:
                        continue
                    
                    # Filter out non-numeric entries if any (sometimes placeholder strings exist)
                    try:
                        int(nomor)
                        int(tahun)
                    except (ValueError, TypeError):
                        continue

                    # Construct URL
                    url = f"https://peraturan.go.id/id/{p}-no-{nomor}-tahun-{tahun}"
                    
                    pejabat = entry.get('pejabat yang menetapkan', '')
                    
                    pages_to_insert.append((
                        url,
                        entry.get('judul'),
                        entry.get('jenis'),
                        entry.get('pemrakarsa'),
                        nomor,
                        tahun,
                        entry.get('tentang'),
                        entry.get('tempat_penetapan'),
                        entry.get('ditetapkan_tanggal'),
                        pejabat,
                        entry.get('status'),
                        entry.get('dokumen_peraturan')
                    ))

                # Batch insert to pages (Insert or Replace)
                cursor.executemany('''
                    INSERT OR REPLACE INTO pages (
                        url, judul, jenis, pemrakarsa, nomor, tahun, tentang, 
                        tempat_penetapan, ditetapkan_tanggal, pejabat_yang_menetapkan, 
                        status, dokumen_peraturan
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', pages_to_insert)

            progress.advance(pages_task)

        conn.commit()
        progress.console.print("[cyan]Finished inserting into 'pages' table.[/]")

        # 3. Update status on urls
        progress.add_task("[blue]Updating status on urls table...", total=None) # indeterminate task
        cursor.execute('''
            UPDATE urls
            SET status = 1, date_modified = ?
            WHERE url IN (SELECT url FROM pages)
        ''', (get_now(),))
        
        conn.commit()
        progress.console.print(f"[bold green]Task success! Updated {cursor.rowcount} rows in 'urls' table.[/]")

    conn.close()

if __name__ == "__main__":
    insert_data()
