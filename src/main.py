import os
import logging

from fastmcp import FastMCP
from fastmcp.tools import Tool

import click

from src.airflow.config import get_all_functions as get_config_functions
from src.airflow.connection import get_all_functions as get_connection_functions
from src.airflow.dag import get_all_functions as get_dag_functions
from src.airflow.dagrun import get_all_functions as get_dagrun_functions
from src.airflow.dagstats import get_all_functions as get_dagstats_functions
from src.airflow.dataset import get_all_functions as get_dataset_functions
from src.airflow.eventlog import get_all_functions as get_eventlog_functions
from src.airflow.importerror import get_all_functions as get_importerror_functions
from src.airflow.monitoring import get_all_functions as get_monitoring_functions
from src.airflow.plugin import get_all_functions as get_plugin_functions
from src.airflow.pool import get_all_functions as get_pool_functions
from src.airflow.provider import get_all_functions as get_provider_functions
from src.airflow.taskinstance import get_all_functions as get_taskinstance_functions
from src.airflow.variable import get_all_functions as get_variable_functions
from src.airflow.xcom import get_all_functions as get_xcom_functions
from src.enums import APIType

APITYPE_TO_FUNCTIONS = {
    APIType.CONFIG: get_config_functions,
    APIType.CONNECTION: get_connection_functions,
    APIType.DAG: get_dag_functions,
    APIType.DAGRUN: get_dagrun_functions,
    APIType.DAGSTATS: get_dagstats_functions,
    APIType.DATASET: get_dataset_functions,
    APIType.EVENTLOG: get_eventlog_functions,
    APIType.IMPORTERROR: get_importerror_functions,
    APIType.MONITORING: get_monitoring_functions,
    APIType.PLUGIN: get_plugin_functions,
    APIType.POOL: get_pool_functions,
    APIType.PROVIDER: get_provider_functions,
    APIType.TASKINSTANCE: get_taskinstance_functions,
    APIType.VARIABLE: get_variable_functions,
    APIType.XCOM: get_xcom_functions,
}


def filter_functions_for_read_only(functions: list[tuple]) -> list[tuple]:
    """
    Filter functions to only include read-only operations.

    Args:
        functions: List of (func, name, description, is_read_only) tuples

    Returns:
        List of (func, name, description, is_read_only) tuples with only read-only functions
    """
    return [
        (func, name, description, is_read_only) for func, name, description, is_read_only in functions if is_read_only
    ]


def setup_tools(app, apis, read_only):
    for api in apis:
        logging.debug(f"Adding API: {api}")
        get_function = APITYPE_TO_FUNCTIONS[APIType(api)]
        try:
            functions = get_function()
        except NotImplementedError:
            continue

        # Filter functions for read-only mode if requested
        if read_only:
            functions = filter_functions_for_read_only(functions)

        for func, name, description, *_ in functions:
            app.add_tool(
                    Tool.from_function(
                        func,
                        name=name,
                        description=description
                    )
                )


def configure_transport(transport):
    if transport in {"sse", "http"}:
        if transport == "sse":
            logging.warning("You selected the 'sse' transposrt that is going be deprecated")
        elif transport == "http":
            transport = "streamable-http"

    logging.debug(f"Starting MCP server for Apache Airflow with '{transport}' transport")
    return transport


DEFAULT_PORT = 8000
DEFAULT_HOST= "127.0.0.1"


@click.command()
@click.option(
    "--port",
    default=os.environ.get("MCP_PORT", DEFAULT_PORT),
    help=f"Port. Default is {DEFAULT_PORT}"
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "http"]),
    default=os.environ.get("MCP_TRANSPORT", "stdio"),
    help="Transport type",
)
@click.option(
    "--host",
    default=os.environ.get("MCP_HOST", DEFAULT_HOST),
    help=f"Sets the host for running MCP. Default is {DEFAULT_HOST}"
)
@click.option(
    "--apis",
    type=click.Choice([api.value for api in APIType]),
    default=[api.value for api in APIType],
    multiple=True,
    help="APIs to run, default is all",
)
@click.option(
    "--read-only",
    is_flag=True,
    help="Only expose read-only tools (GET operations, no CREATE/UPDATE/DELETE)",
)
def main(port: int, transport: str, host: str, apis: list[str], read_only: bool) -> None:
    app = FastMCP(
        "airflow-mcp",
        port=port,
        host=host
    )

    setup_tools(app, apis, read_only)

    app.run(
        transport=configure_transport(transport)
    )
