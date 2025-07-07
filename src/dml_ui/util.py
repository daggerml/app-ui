"""
DaggerML UI Utility Functions

This module provides utility functions for processing and formatting DAG data
for display in the web interface. Key functionality includes:

- Node filtering and pruning for cleaner visualization
- Resource resolution and substitution handling  
- Node representation extraction including error traces, scripts, and HTML content
- Special handling for command-line argument (argv) nodes
- DAG information aggregation for comprehensive UI display

The functions in this module bridge between the DaggerML core data structures
and the frontend UI components, handling data transformation and formatting.
"""

import logging
import re
from pprint import pformat

from daggerml import Error, Resource
from daggerml.core import Ref

from dml_util.aws.s3 import S3Store

logger = logging.getLogger(__name__)


def filter_nodes(nodes, edges):
    """Filter out nodes that are dml created and can be pruned.

    This function removes internal DML nodes from the visualization to show only
    user-relevant nodes and their connections.

    Parameters
    ----------
    nodes : list of dict
        List of node dictionaries containing node metadata including 'node_type' and 'id'.
    edges : list of dict
        List of edge dictionaries containing 'source' and 'target' node IDs.

    Returns
    -------
    tuple of (list, list)
        A tuple containing (filtered_nodes, filtered_edges) with DML internal nodes removed.

    Examples
    --------
    >>> node1 = dag._put("asdf")
    >>> node2 = dag._put([node1])
    >>> node3 = node2[0]
    >>> dag.result = dag.fn(node3)

    `filter_nodes` will remove the edge from `node3` to `dag.result` and replace it with an edge from `node1`.
    It will then look for all nodes that have no edges and remove those from the nodes list.
    """
    filtered_nodes = []
    filtered_edges = []
    for node in nodes:
        print(node.keys())
        if node["node_type"] == "dml":
            continue
        filtered_nodes.append(node)
        for edge in edges:
            if edge["source"] == node["id"]:
                filtered_edges.append(edge)
    filtered_edges = [edge for edge in filtered_edges if edge["target"] not in [n["id"] for n in nodes if n["node_type"] == "dml"]]
    return filtered_nodes, filtered_edges


def get_sub(resource):
    """Recursively resolve resource substitutions to get the final resource.

    Parameters
    ----------
    resource : Resource
        A DaggerML Resource object that may contain substitutions.

    Returns
    -------
    Resource
        The final resolved resource after following all substitution chains.
    """
    while (sub := (resource.data or {}).get("sub")) is not None:
        resource = sub
    return resource


def get_node_repr(dag, node_id):
    """Get a comprehensive representation of a DAG node for display in the UI.

    This function extracts various metadata about a node including its value, error traces,
    associated scripts, HTML content, and command-line arguments if applicable.

    Parameters
    ----------
    dag : DAG
        The DaggerML DAG object containing the node.
    node_id : str
        The unique identifier of the node to represent.

    Returns
    -------
    dict
        A dictionary containing:
        - script : str or None
            Associated script content if the node represents a script execution.
        - html_uri : str or None
            Pre-signed S3 URL for HTML content if the node contains HTML output.
        - stack_trace : str or None
            Formatted stack trace if the node contains an error.
        - value : str
            Pretty-formatted string representation of the node's value.
        - argv_elements : list or None
            List of dictionaries containing argument details if this is an argv-like node.
            Each element contains 'index', 'value', and 'type' keys.
        - node_type : str or None
            Type classification of the node (e.g., 'argv' for argument nodes).
    """
    val = dag[node_id].value()
    stack_trace = html_uri = script = None
    if isinstance(val, Error):
        try:
            stack_trace = "\n".join([x.strip() for x in val.context["trace"] if x.strip()])
        except Exception:
            pass
    elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], Resource):
        script = (get_sub(val[0]).data or {}).get("script")
    elif isinstance(val, Resource):
        script = (get_sub(val).data or {}).get("script")
        s3 = S3Store()
        if re.match(r"^s3://.*\.html$", val.uri) and s3.exists(val):
            bucket, key = s3.parse_uri(val)
            html_uri = s3.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ResponseContentDisposition": "inline",
                    "ResponseContentType": "text/html",
                },
                ExpiresIn=3600,  # URL expires in 1 hour
            )
    
    # Check if this is an argv node and parse the arguments
    # Argv nodes typically contain lists of basic Python types (strings, numbers, etc.)
    argv_elements = []
    if isinstance(val, list) and len(val) > 0:
        # Check if this looks like command line arguments
        if all(isinstance(item, (str, int, float, bool)) for item in val):
            argv_elements = val
    
    return {
        "script": script,
        "html_uri": html_uri,
        "stack_trace": stack_trace,
        "value": pformat(val, depth=3),
        "argv_elements": argv_elements,
    }


def get_dag_info(dml, dag_id, prune=False):
    """Retrieve comprehensive information about a DAG for display in the UI.

    This function gathers all necessary data about a DAG including its structure,
    nodes, edges, environment information, and log streams.

    Parameters
    ----------
    dml : DML
        The DaggerML client object.
    dag_id : str
        The unique identifier of the DAG.
    prune : bool, optional
        Whether to prune internal DML nodes from the result (default: False).

    Returns
    -------
    dict
        A dictionary containing:
        - dag_data : dict
            Core DAG structure including nodes and edges.
        - script : str or None
            Script content associated with the DAG's argv if available.
        - result : various types or None
            The DAG's result value if it has been computed.
        - log_streams : dict
            Dictionary containing log stream information with 'stdout' and 'stderr' keys.
    """
    out = {"dag_data": dml("dag", "describe", dag_id)}
    dag_data = out["dag_data"]
    for node in dag_data["nodes"]:
        if node["node_type"] in ["import", "fn"]:
            if node["node_type"] == "fn":
                node["sublist"] = [
                    x["source"] for x in dag_data["edges"] if x["type"] == "node" and x["target"] == node["id"]
                ]
            (node["parent"],) = [x["source"] for x in dag_data["edges"] if x["type"] == "dag" and x["target"] == node["id"]]
    if dag_data.get("argv"):
        node = dml.get_node_value(Ref(dag_data["argv"]))
        out["script"] = (get_sub(node[0]).data or {}).get("script")
    dag = dml.load(dag_id)
    
    # Process DAG result node if available
    # Extract the actual result value, excluding argv_elements from the unpacking
    for key in ["result"]:
        if dag_data.get(key) is not None:
            tmp = get_node_repr(dag, dag_data[key])
            out[key], = [v for k, v in tmp.items() if v is not None and k != "argv_elements"]
    try:
        env_data, = [dag[node["id"]].value() for node in dag_data["nodes"] if node["name"] == ".dml/env"]
        log_group = env_data["log_group"]
        out["log_streams"] = {k: {"log_group": log_group, "log_stream": env_data[f"log_{k}"]} for k in ["stdout", "stderr"]}
    except Exception as e:
        logger.warning(f"Failed to extract log streams: {e}")
        out["log_streams"] = {}
    return out


def get_node_info(dml, dag_id, node_id):
    """Retrieve detailed information about a specific node in a DAG.

    This is a convenience wrapper around get_node_repr that loads the DAG
    and extracts information for a single node.

    Parameters
    ----------
    dml : DML
        The DaggerML client object.
    dag_id : str
        The unique identifier of the DAG containing the node.
    node_id : str
        The unique identifier of the node to retrieve information for.

    Returns
    -------
    dict
        Node representation dictionary as returned by get_node_repr().
    """
    return get_node_repr(dml.load(dag_id), node_id)
