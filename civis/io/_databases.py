from civis import APIClient
from civis._utils import maybe_get_random_name
from civis.polling import PollableResult, _DEFAULT_POLLING_INTERVAL


def query_civis(sql, database, api_key=None, credential_id=None,
                preview_rows=10,
                polling_interval=_DEFAULT_POLLING_INTERVAL):
    """Execute a SQL statement as a Civis query.

    Run a query that may return no results or where only a small
    preview is required. To execute a query that returns a large number
    of rows, see :func:`~civis.io.read_civis_sql`.

    Parameters
    ----------
    sql : str
        The SQL statement to execute.
    database : str or int
        The name or ID of the database.
    api_key : str, optional
        Your Civis API key. If not given, the :envvar:`CIVIS_API_KEY`
        environment variable will be used.
    credential_id : str or int, optional
        The ID of the database credential. If ``None``, the default
        credential will be used.
    preview_rows : int, optional
        The maximum number of rows to return. No more than 100 rows can be
        returned at once.
    polling_interval : int or float, optional
        Number of seconds to wait between checks for query completion.

    Returns
    -------
    results : :class:`~civis.polling.PollableResult`
        A `PollableResult` object.

    Examples
    --------
    >>> run = query_civis(sql="DELETE schema.table", database='database')
    >>> run.result()  # Wait for query to complete
    """
    client = APIClient(api_key=api_key)
    database_id = client.get_database_id(database)
    cred_id = credential_id or client.default_credential
    resp = client.queries.post(database_id, sql, preview_rows,
                               credential=cred_id)
    return PollableResult(client.queries.get, (resp.id, ), polling_interval)


def transfer_table(source_db, dest_db, source_table, dest_table,
                   job_name=None, api_key=None, source_credential_id=None,
                   dest_credential_id=None,
                   polling_interval=_DEFAULT_POLLING_INTERVAL,
                   **advanced_options):
    """Transfer a table from one location to another.

    Parameters
    ----------
    source_db : str or int
        The name of the database where the source table is located.
        Optionally, could be the database ID.
    dest_db : str or int
        The name of the database where the table will be transfered.
        Optionally, could be the database ID.
    source_table : str
        Full name of the table to transfer, e.g., ``'schema.table'``.
    dest_table : str
        Full name of the table in the destination database, e.g.,
        ``'schema.table'``.
    job_name : str, optional
        A name to give the job. If omitted, a random job name will be
        used.
    api_key : str, optional
        Your Civis API key. If not given, the :envvar:`CIVIS_API_KEY`
        environment variable will be used.
    source_credential_id : str or int, optional
        Optional credential ID for the source database. If ``None``, the
        default credential will be used.
    dest_credential_id : str or int, optional
        Optional credential ID for the destination database. If ``None``,
        the default credential will be used.
    polling_interval : int or float, optional
        Number of seconds to wait between checks for job completion.
    **advanced_options : kwargs
        Extra keyword arguments will be passed to the import sync job. See
        :func:`~civis.resources._resources.Imports.post_syncs`.

    Returns
    -------
    results : :class:`~civis.polling.PollableResult`
        A `PollableResult` object.

    Examples
    --------
    >>> transfer_table(source_db='Cluster A', dest_db='Cluster B',
    ...                source_table='schma.tbl', dest_table='schma.tbl')
    """
    client = APIClient(api_key=api_key)
    source_cred_id = source_credential_id or client.default_credential
    dest_cred_id = dest_credential_id or client.default_credential
    job_name = maybe_get_random_name(job_name)
    source = {
        'remote_host_id': client.get_database_id(source_db),
        'credential_id': source_cred_id
    }
    destination = {
        'remote_host_id': client.get_database_id(dest_db),
        'credential_id': dest_cred_id
    }
    job_id = client.imports.post(job_name, "Dbsync", True, source=source,
                                 destination=destination).id

    client.imports.post_syncs(id=job_id,
                              source={'path': source_table},
                              destination={'path': dest_table},
                              advanced_options=advanced_options)
    run_id = client.imports.post_runs(id=job_id).run_id

    poll = PollableResult(client.imports.get_files_runs,
                          (job_id, run_id),
                          polling_interval)
    return poll
