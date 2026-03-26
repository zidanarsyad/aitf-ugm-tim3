import duckdb

duckdb.read_json("siaran_pers_general.json")              # read a JSON file into a Relation


# Get the schema (column names and types)
print("\nSchema:")
duckdb.sql("DESCRIBE siaran_pers_general.json").show()

article_row_count = duckdb.sql("SELECT count(*) FROM 'siaran_pers_general.json'").fetchone()[0]
print(f"Total rows: {article_row_count}")

duckdb.read_json("siaran_pers_general_links.json")              # read a JSON file into a Relation

# Get the schema (column names and types)
print("\nSchema:")
duckdb.sql("DESCRIBE siaran_pers_general_links.json").show()

links_row_count = duckdb.sql("SELECT count(*) FROM 'siaran_pers_general_links.json'").fetchone()[0]
print(f"Total rows: {links_row_count}")


print(f"\nProgress: {article_row_count / links_row_count * 100:.2f}%")

print("\nHead:")

duckdb.sql("SELECT * FROM 'siaran_pers_general.json' LIMIT 10").show()