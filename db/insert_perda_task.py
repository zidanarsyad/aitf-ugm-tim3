import sqlite3
import json
import os
from datetime import datetime
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Paths
DB_PATH = r'd:\1_projects\aitf-ugm-tim3\db\peraturan.db'
LINKS_PATH = r'd:\1_projects\aitf-ugm-tim3\db\peraturan_go_id_perda_links.json'
DATA_PATH = r'd:\1_projects\aitf-ugm-tim3\db\peraturan_go_id_perda.json'

def get_now():
    return datetime.now().isoformat()

def insert_perda():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = get_now()

    with Progress(
        # SpinnerColumn(spinner_name="dots"), # This might cause issues
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:

        # 1. Load and Insert Links to 'urls' table
        progress.console.print("[cyan]Loading perda links...[/]")
        with open(LINKS_PATH, 'r', encoding='utf-8') as f:
            links_data = json.load(f)

        links_task = progress.add_task("[green]Inserting links into 'urls'...", total=len(links_data))
        
        # Mapping title -> url for later
        title_to_url = {}
        urls_to_insert = []
        
        for item in links_data:
            title = item.get('title', '')
            link = item.get('link', '')
            if not link:
                progress.advance(links_task)
                continue
            
            full_url = f"https://peraturan.go.id{link}"
            title_to_url[title] = full_url
            
            urls_to_insert.append((full_url, 'perda', 0, now, now))
            progress.advance(links_task)

        cursor.executemany('''
            INSERT OR IGNORE INTO urls (url, peraturan, status, date_created, date_modified)
            VALUES (?, ?, ?, ?, ?)
        ''', urls_to_insert)
        conn.commit()
        progress.console.print(f"[bold green]Inserted {cursor.rowcount} new links into 'urls'.[/]")

        # 2. Load and Insert Data to 'pages' table
        progress.console.print("[cyan]Loading perda data...[/]")
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            perda_data = json.load(f)

        pages_task = progress.add_task("[yellow]Processing 'pages' table...", total=len(perda_data))
        pages_to_insert = []
        urls_to_update = []

        # Optimization: pre-sort titles by length descending to match longest title first if multiple matches
        sorted_titles = sorted(title_to_url.keys(), key=len, reverse=True)

        for item in perda_data:
            judul = item.get('judul', '')
            url = item.get('url') # Check if it already has URL
            
            if not url:
                # Try to match judul with title
                # The user said: "judul contains title"
                matched_url = None
                for title in sorted_titles:
                    if title in judul:
                        matched_url = title_to_url[title]
                        break
                url = matched_url

            if not url:
                progress.advance(pages_task)
                continue

            pejabat = item.get('pejabat yang menetapkan', '')
            
            pages_to_insert.append((
                url,
                item.get('judul'),
                item.get('jenis'),
                item.get('pemrakarsa'),
                item.get('nomor'),
                item.get('tahun'),
                item.get('tentang'),
                item.get('tempat_penetapan'),
                item.get('ditetapkan_tanggal'),
                pejabat,
                item.get('status'),
                item.get('dokumen_peraturan')
            ))
            
            urls_to_update.append((url,))
            progress.advance(pages_task)

        # Batch insert to pages
        cursor.executemany('''
            INSERT OR REPLACE INTO pages (
                url, judul, jenis, pemrakarsa, nomor, tahun, tentang, 
                tempat_penetapan, ditetapkan_tanggal, pejabat_yang_menetapkan, 
                status, dokumen_peraturan
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', pages_to_insert)
        conn.commit()
        progress.console.print(f"[bold green]Inserted {len(pages_to_insert)} records into 'pages'.[/]")

        # 3. Update status in 'urls'
        progress.console.print("[cyan]Updating status in 'urls' table...[/]")
        now = get_now()
        # Update status to 1 for all URLs that we just processed
        # We can do this in bulk using a temporary table or just a large IN clause if reasonably sized,
        # but since we have the list, let's use a subquery check again for safety or just bulk update.
        
        cursor.executemany('''
            UPDATE urls
            SET status = 1, date_modified = ?
            WHERE url = ?
        ''', [(now, u[0]) for u in urls_to_update])
        
        conn.commit()
        progress.console.print(f"[bold green]Updated {cursor.rowcount} rows in 'urls' table.[/]")

    conn.close()
    print("All tasks completed.")

if __name__ == "__main__":
    insert_perda()
