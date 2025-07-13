"""
DaggerML UI Utility Functions

Provides utility functions for processing and formatting DAG data for the web interface.
Handles node filtering, resource resolution, and data transformation for UI components.
"""

import logging
import re
from pprint import pformat

from daggerml import Error, Resource
from daggerml.core import Ref

from dml_util.aws.s3 import S3Store

logger = logging.getLogger(__name__)


def filter_nodes(nodes, edges):
    """Filter out internal DML nodes to show only user-relevant nodes.

    Parameters
    ----------
    nodes : list of dict
        List of node dictionaries.
    edges : list of dict
        List of edge dictionaries.

    Returns
    -------
    tuple of (list, list)
        Filtered nodes and edges with DML internal nodes removed.
    """
    filtered_nodes = []
    filtered_edges = []
    for node in nodes:
        if node["node_type"] == "dml":
            continue
        filtered_nodes.append(node)
        for edge in edges:
            if edge["source"] == node["id"]:
                filtered_edges.append(edge)
    filtered_edges = [edge for edge in filtered_edges if edge["target"] not in [n["id"] for n in nodes if n["node_type"] == "dml"]]
    return filtered_nodes, filtered_edges


def get_sub(resource):
    """Recursively resolve resource substitutions to get the final resource."""
    while (sub := (resource.data or {}).get("sub")) is not None:
        resource = sub
    return resource


def get_node_repr(dag, node_id):
    """Get a comprehensive representation of a DAG node for display in the UI.

    Returns a dictionary containing script content, HTML URIs, stack traces,
    formatted values, and argument details for the specified node.
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

    Gathers all necessary data about a DAG including its structure, nodes,
    edges, environment information, and log streams.
    """
    out = {"dag_data": dml("dag", "describe", dag_id)}
    dag_data = out["dag_data"]
    
    # Debug logging
    print(f"DEBUG: DAG {dag_id} has {len(dag_data.get('nodes', []))} nodes")
    print(f"DEBUG: DAG result node: {dag_data.get('result')}")
    
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
    # Extract result, error, and stack trace information
    for key in ["result"]:
        if dag_data.get(key) is not None:
            print(f"DEBUG: Processing result node {dag_data[key]}")
            tmp = get_node_repr(dag, dag_data[key])
            print(f"DEBUG: Result node repr keys: {list(tmp.keys())}")
            # Extract individual components
            for field in ["value", "stack_trace", "script", "html_uri"]:
                if tmp.get(field) is not None:
                    if field == "value":
                        # The result value is stored under the "result" key
                        if tmp.get("stack_trace"):
                            # If there's a stack trace, this indicates an error
                            out["error"] = tmp["value"]
                            out["stack_trace"] = tmp["stack_trace"]
                            print("DEBUG: Found error in result node")
                        else:
                            # No stack trace means this is a successful result
                            out["result"] = tmp["value"]
                            print("DEBUG: Found successful result")
                    else:
                        out[field] = tmp[field]
    
    # If no result node exists, check if any nodes have errors
    if "result" not in out and "error" not in out:
        print("DEBUG: No result found, scanning all nodes for errors...")
        for node in dag_data.get("nodes", []):
            try:
                node_value = dag[node["id"]].value()
                if isinstance(node_value, Error):
                    print(f"DEBUG: Found error in node {node['id']}")
                    # Found an error node
                    tmp = get_node_repr(dag, node["id"])
                    if tmp.get("stack_trace"):
                        out["error"] = tmp["value"]
                        out["stack_trace"] = tmp["stack_trace"]
                        print(f"DEBUG: Using error from node {node['id']}")
                        break  # Use the first error found
            except Exception as e:
                print(f"DEBUG: Could not evaluate node {node.get('id', 'unknown')}: {e}")
                continue  # Skip nodes that can't be evaluated
    
    # Final check - if still no error/result found, add debug information
    if "result" not in out and "error" not in out:
        print("DEBUG: Still no result/error found, checking DAG structure...")
        # Check if DAG description has any error information
        if dag_data.get("error"):
            out["error"] = str(dag_data["error"])
            print(f"DEBUG: Found error in DAG description: {out['error']}")
        # As a last resort, provide debug information
        else:
            print("DEBUG: No error information found anywhere")
    
    print(f"DEBUG: Final out keys: {list(out.keys())}")
    try:
        env_data, = [dag[node["id"]].value() for node in dag_data["nodes"] if node["name"] == ".dml/env"]
        log_group = env_data["log_group"]
        out["log_streams"] = {k: {"log_group": log_group, "log_stream": env_data[f"log_{k}"]} for k in ["stdout", "stderr"]}
    except Exception as e:
        logger.warning(f"Failed to extract log streams: {e}")
        out["log_streams"] = {}
    return out


def get_node_info(dml, dag_id, node_id):
    """Retrieve detailed information about a specific node in a DAG."""
    node_data = get_node_repr(dml.load(dag_id), node_id)
    try:
        node_description = dml("node", "describe", node_id)
        if node_description and "argv" in node_description:
            argv_elements = []
            for i, arg in enumerate(node_description["argv"] or []):
                argv_elements.append({
                    "index": i,
                    "data_type": arg.get("data_type"),
                    "doc": arg.get("doc"),
                    "id": arg.get("id"),
                    "dict_keys": arg.get("keys"),
                    "length": arg.get("length"),
                    "node_type": arg.get("node_type"),
                })
            node_data["argv_elements"] = argv_elements
            node_data["has_argv"] = len(argv_elements) > 0
        
        # Add the full node description for plugins or other uses
        node_data["node_description"] = node_description
        
    except Exception as e:
        logger.warning(f"Failed to get node description for {node_id}: {e}")
        # Fall back to the existing argv detection logic in get_node_repr
        pass
    
    return node_data
