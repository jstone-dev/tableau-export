# tableau-export
Script for exporting workbooks direcly from Tableau's PostgreSQL database

## Purpose

This script exports all Tableau workbooks directly from a Tableau server's PostgreSQL database. It can be used even if the Tableau installation has no active licenses. It is an alternative to manually exporting each workbook through Tableau's web interface, which requires a Tableau software license and can be laborious when the server hosts many workbooks. The resulting export format is slightly different:

- Using this script, we wind up with one .twb file per workbook, which is an XML document containing all of the workbook's configuration and code. If the workbook includes static data files or image resources, these are exported as separate files.
- Using the Tableau web interface to export workbooks, we wind up with one .twb or .twbx file per workbook. The latter is a Zip archive that includes the .twb file and supporting resources (static data files and images). The web interface also allows you to export a workbook screenshot.

The script operates by fetching a list of workbooks, then, for each workbook, fetching and concatenating all the BLOBs (binary large objects) that store the workbook. Each BLOB is either an XML file, which can be saved as `{workbook_url}.twb`, or a Zip archive that bundles the .twb file with supporting resources.

Since the script uses `psql` rather than a PostgreSQL client library, psql's `\copy` command is used to save the BLOB to disk. The resulting file has some binary header and footer bytes that we strip out before saving the result as XML or extracing the Zip archive.

## Dependencies

For ease of use, the script has minimal dependencies. It does not use a Python PostgreSQL client like psycopg2; instead it runs queries by spawning a subprocess to run [psql](https://www.postgresql.org/docs/current/app-psql.html).

There are two dependencies:
- The `psql` command must be installed.
- The `unzip` command must be installed.

No Python libraries are used, aside from the standard library.

## Usage

If your psql binary is not in your `$PATH` environment variable, edit the script and change the value of `PSQL` to the actual binary path.

Ensure that the following environment variables are set as needed, to allow connections to Tableau's PostgreSQL database server. Notice that by default, Tableau Server uses a nonstandard PostgreSQL port number of 8060. You will typically want to use Tableau's PostgreSQL admin user, tblwgadmin.

- TABLEAU_POSTGRES_HOST: The hostname or IP address of the PostgreSQL server. (default=`localhost`)
- TABLEAU_POSTGRES_HOST: The TCP post number of the PostgreSQL server (default=`8060`)
- TABLEAU_POSTGRES_USER: A PostgreSQL user (login role) that has full read permissions (default=`tblwgadmin`)
- TABLEAU_POSTGRES_PASSWORD: The PostgreSQL user's password (default=empty)

Now run the script:

```sh
export_tableau_workbooks.py [-h] [-o OUTPUT_DIR]
```

```
optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        output directory
```

## Output

In the specified output directory, subdirectories of the form PROJECT/WORKBOOK are created for each project and workbook. A .twb file is saved in each workbook folder. If the workbook has supporting resources (static data files or images), these are saved in subdirectories using Tableau's file organization, i.e. in subdirectories named Data and Image, sometimes with further nested subdirectories.
