# Runoregi

[Runoregi](https://runoregi.fi) is the Web front-end for verse
and poem similarity calculations on Finnic oral folk poetry.

## Branch `runoregi-parquet`: reading parquet files with DuckDB

This branch (Experimental-Regi, deployed at https://regi.artificial-other.com)
builds on `translations` and reads the data from parquet files with
[DuckDB](https://duckdb.org/) instead of querying MariaDB. It is deployed
together with the `filter-visualizations-parquet` branch of
[filter-visualizations](https://github.com/jakobytes/filter-visualizations).

Changes:
- `config.py`: DuckDB views over `<PARQUET_BASE>/<table>.parquet`; a cursor
  wrapper accepts the pymysql query style; logging to the database is off.
- MySQL-only SQL rewritten (`STRING_AGG`, `||`, `GROUP BY`, quoting,
  `ORDER BY`).
- Search: boolean-mode full-text search emulated with `regexp_matches`
  (also for translations); results capped at `SEARCH_LIMIT`. Verse and
  translation results show the original verse next to its English
  translation.
- Cluster dendrograms accept poem IDs as the cluster parameter.
- `fetch_parquet.py`: downloads the parquet files from an HTTP(S) URL or an
  S3 bucket (Allas) into a directory.

Running locally (parquet files in `./parquet`, filter-visualizations checked
out next to this repository):

```bash
docker compose up -d --build
```

runoregi is then at http://localhost:8000 and the visualizations at
http://localhost:3838.

| Variable | Description |
|---|---|
| `PARQUET_BASE` | URL or directory containing `<table>.parquet` |
| `VISUALIZATIONS_URL` | Base URL of the visualizations app |
| `DUCKDB_MEMORY_LIMIT`, `DUCKDB_THREADS` | Cap DuckDB below the container limits |

Rahti (project `elias26`), from `rahti/`: one Deployment `dhh26-regi` with
both apps and an init container that runs `fetch_parquet.py` to download the
files from the private bucket `s3://livonia-parquet` into a shared,
read-only `emptyDir`. The download needs a Secret with Allas S3
credentials:

```bash
oc create secret generic livonia-allas-reader \
  --from-literal=AWS_ACCESS_KEY_ID=... --from-literal=AWS_SECRET_ACCESS_KEY=...
rahti/deploy.sh --rebuild   # apply manifests, build both images
```

## Setup

Python dependencies can be installed with the usual command:
```
pip3 install -r requirements.txt
```

As Runoregi is a front-end, it requires access to a MySQL database
containing all the data (poem texts, metadata, similarities etc.) in
order to work. The access is configured by the following environment
variables:
* `DB_HOST` -- hostname,
* `DB_PORT` -- port (must be given even if it's the default `3306`),
* `DB_USER` -- username,
* `DB_PASS` -- password,
* `DB_NAME` -- name of the database.

A dump of the database, including SQL scripts to load the tables, is
available in
[hsci-r/filter-db](https://github.com/hsci-r/filter-db) (currently
not public).

In addition to the database access, the following further environment
variables can be configured:
* `DB_LOGGING` -- if set (to any value), Runoregi will write information about the requested pages and their loading times to the table `runoregi_log`,
* `VISUALIZATIONS_URL` -- the base URL of the [visualizations application](https://filter-visualizations.rahtiapp.fi) -- needed for the links to the visualizations (maps, type treemaps)!

## Running

For all the commands listed below, remember to set the environment
variables (see above).

### Local testing

The easiest way to run Runoregi for quick testing (e.g. if you're working
with the code) is to run:
```
python3 wsgi.py
```

The interface will be available for local connections under `localhost:5000`.

### Running with Gunicorn

To run Runoregi on a server and access it through the default HTTP port,
it should be enough to run:
```
gunicorn wsgi
```

See [Gunicorn documentation](https://docs.gunicorn.org/en/stable/run.html)
for more options.

### Deployment on Rahti

In our project Runoregi is hosted on the CSC's [Rahti](https://rahti.csc.fi/)
service, with a Docker image built using
[Source-to-image](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#source-build).
For deployment, you need to link to this repository, provide a pull secret
(as long as the repository is private) and set the environment variables
to access the database.

Docker images for deployment on an own platform might be provided
in the future if needed.

## License

MIT (see [LICENSE](./LICENSE))

## Publications

There are no publications so far descibing specifically the front-end.
You can cite Runoregi by referring to one of the publications that
describe the back-end calculations:

* Janicki M., Kallio K. and Sarv M. 2022. [Exploring Finnic written oral folk poetry through string similarity.](https://academic.oup.com/dsh/advance-article/doi/10.1093/llc/fqac034/6643198?login=true). *Digital Scholarship in the Humanities*.
* Janicki M. 2022. [Optimizing the weighted sequence alignment algorithm for large-scale text similarity computation.](https://aclanthology.org/2022.nlp4dh-1.13/) In: *Proceedings of the 2nd International Workshop on Natural Language Processing for Digital Humanities – NLP4DH 2022*.

