"""
load_to_sqlite.py
-----------------
Builds data/sales.db from the CSVs using sql/01_schema.sql, creates the clean
view (sql/02_data_cleaning.sql) and runs every query in the SQL folder,
printing the results. No database server needed.

Run:
    python python/load_to_sqlite.py            # build + run all queries
    python python/load_to_sqlite.py --build    # build only
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, SQL = ROOT / "data", ROOT / "sql"
DB = DATA / "sales.db"


def split_statements(text: str):
    """Split a .sql file into (comment_title, statement) pairs."""
    out, title, buf = [], "", []
    for line in text.splitlines():
        s = line.strip()
        if not s and not buf:
            continue
        if s.startswith("--") and not buf:
            t = s.lstrip("- ").strip()
            if t and not set(t) <= {"="}:
                title = t
            continue
        buf.append(line)
        if s.split("--", 1)[0].rstrip().endswith(";"):
            out.append((title, "\n".join(buf)))
            buf, title = [], ""
    return out


def build(con):
    con.executescript((SQL / "01_schema.sql").read_text())
    for t in ["dim_regions", "dim_products", "dim_sales_reps", "dim_customers", "fact_sales"]:
        df = pd.read_csv(DATA / f"{t}.csv")
        if "is_returned" in df:
            df["is_returned"] = df["is_returned"].astype(int)
        df.to_sql(t, con, if_exists="append", index=False)
    print(f"Built {DB.name}")


def run_file(con, name):
    print(f"\n{'#' * 70}\n# {name}\n{'#' * 70}")
    for title, stmt in split_statements((SQL / name).read_text()):
        head = stmt.lstrip().split(None, 1)[0].upper()
        if head in ("SELECT", "WITH"):
            print(f"\n-- {title}")
            print(pd.read_sql_query(stmt, con).to_string(index=False))
        else:
            con.execute(stmt)
    con.commit()


if __name__ == "__main__":
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    build(con)
    files = ["02_data_cleaning.sql"] if "--build" in sys.argv else \
            ["02_data_cleaning.sql", "03_kpi_analysis.sql", "04_advanced_analysis.sql"]
    for f in files:
        run_file(con, f)
    con.close()
