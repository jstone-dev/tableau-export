import argparse
import logging
import os
import pathlib
import subprocess

logger = logging.getLogger(__name__)

pg_host = os.environ.get("TABLEAU_POSTGRES_HOST", "localhost")
pg_port = int(os.environ.get("TABLEAU_POSTGRES_HOST", "8060"))
pg_user = os.environ.get("TABLEAU_POSTGRES_USER", "tblwgadmin")
pg_password = os.environ.get("TABLEAU_POSTGRES_PASSWORD", "")

PSQL = "psql"
PSQL_COMMAND = f"{PSQL} -h {pg_host} -p {pg_port} -U {pg_user} -d workgroup"

LIST_WORKBOOKS_SQL = """
SELECT
  p.name project_name, w.name workbook_name, w.repository_url workbook_url
FROM workbooks w
  LEFT OUTER JOIN projects p ON p.id=w.project_id
ORDER BY p.name, w.name;
"""


def fetch_workbooks_list():
    result = subprocess.run(
        PSQL_COMMAND.split(" "),
        capture_output=True,
        env={"PGPASSWORD": pg_password},
        input=LIST_WORKBOOKS_SQL,
        text=True
    )

    if result.returncode == 0:
        output = result.stdout
        row_strs = output.split("\n")[2:-3]  # Output has 2 header lines and 3 extra lines at the end.
        rows = list(map(lambda row: list(map(lambda cell: cell.strip(), row.split("|"))), row_strs))
        return [{
            "project_name": row[0],
            "workbook_name": row[1],
            "workbook_url": row[2],
        } for row in rows]
    else:
        raise Exception(f"Unable to get the list of workbooks. PSQL exited with code {result.returncode}.")


def fetch_workbook(project_name: str, workbook_name: str, workbook_url: str, output_dir: str):
    logger.info(f"Fetching workbook {project_name}/{workbook_name} (URL: {workbook_url})")

    subprocess.run(["mkdir", "-p", f"{output_dir}/{project_name}/{workbook_name}"])

    blob_path = f"{output_dir}/{project_name}/{workbook_name}/{workbook_url}.blob"

    export_sql = f"""
\\copy (
WITH concatenated_data AS (
SELECT
    lo.loid,
    string_agg(lo.data, '' ORDER BY lo.pageno) AS full_data
FROM pg_largeobject lo
GROUP BY lo.loid
)
SELECT cd.full_data
FROM workbooks w, repository_data rd, concatenated_data cd
WHERE
w.repository_url='{workbook_url}'
AND COALESCE(w.data_id, w.reduced_data_id) = rd.tracking_id
AND rd.content = cd.loid
) TO '{output_dir}/{project_name}/{workbook_name}/{workbook_url}.blob' WITH (FORMAT binary);"""

    subprocess.run(
        PSQL_COMMAND.split(" "),
        capture_output=True,
        env={"PGPASSWORD": pg_password},
        input=export_sql,
        text=True
    )

    # Remove the PGCOPY header and footer, plus the bytes that mark the first (and only) tuple.
    # See https://www.postgresql.org/docs/current/sql-copy.html#id-1.9.3.55.9.4
    # Remove:
    #   - 11 byte header
    #   - 4 byte bit mask
    #   - 4 bytes reserved to indicate length of the rest of the header (currently unused, so 0)
    #   - 2 bytes marking the beginning of the first tuple
    #   - And 4 more bytes, for some reason
    #   - 2-byte footer at end
    with open(blob_path, "rb") as f:
        data = f.read()
    with open(blob_path, "rb") as f:
        data = f.read()
    data = data[25:-2]
    with open(blob_path, "wb") as f:
        f.write(data)

    # Some blob files are XML text.
    is_zip = True
    with open(blob_path, "rb") as f:
        header = f.read(5)
        f.seek(0)
        if header == b"<?xml":
            is_zip = False
            new_path = f"{output_dir}/{project_name}/{workbook_name}/{workbook_url}.twb"
            os.rename(blob_path, new_path)
            blob_path = new_path

    # The others are ZIP files. We could probably just save these as .twbx files, but we will extract them.
    if is_zip:
        subprocess.run(
            ["unzip", f"{output_dir}/{project_name}/{workbook_name}/{workbook_url}.blob"],
            cwd=f"{output_dir}/{project_name}/{workbook_name}"
        )
        os.remove(blob_path)


def main(output_dir):
    print(output_dir)
    workbooks = fetch_workbooks_list()
    for workbook in workbooks:
        fetch_workbook(workbook["project_name"], workbook["worobook_name"], workbook["workbook_url"], output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export workbooks direcly from Tableau's PostgreSQL database")
    parser.add_argument("-o", "--output-dir", default=".", help="output directory", type=pathlib.Path)
    args = parser.parse_args()
    main(args.output_dir)
