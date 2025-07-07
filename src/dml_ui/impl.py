import logging
import importlib
import sys
from argparse import ArgumentParser

from daggerml import Dml
from flask import Flask, jsonify, render_template, request, url_for

from dml_ui.cloudwatch import CloudWatchLogs
from dml_ui.plugins import discover_dag_plugins, discover_node_plugins
from dml_ui.util import get_dag_info, get_node_info

logger = logging.getLogger(__name__)
app = Flask(__name__)


def get_breadcrumbs(repo, branch, dag_id, dag_data=None):
    """Generate breadcrumb navigation data"""
    breadcrumbs = []
    # Home breadcrumb
    breadcrumbs.append({
        "name": "Home",
        "url": url_for("main"),
        "icon": "bi-house"
    })
    if repo:
        # Repo breadcrumb
        breadcrumbs.append({
            "name": repo,
            "url": url_for("main", repo=repo),
            "icon": "bi-folder"
        })
        if branch:
            # Branch breadcrumb
            breadcrumbs.append({
                "name": branch,
                "url": url_for("main", repo=repo, branch=branch),
                "icon": "bi-git"
            })
            if dag_id and dag_data:
                breadcrumbs.append({
                    "name": dag_id[:12],
                    "url": url_for("dag_route", repo=repo, branch=branch, dag_id=dag_id),
                    "icon": "bi-diagram-3",
                })
    return breadcrumbs

def get_sidebar_data(dml, repo, branch, dag_id, dag_data=None):
    """Generate sidebar navigation data with all sections"""
    sidebar = {
        "title": "Navigation", 
        "sections": [],
        "current": {"repo": repo, "branch": branch, "dag_id": dag_id}
    }
    
    # Always show repositories section
    repo_section = {"title": "Repositories", "type": "repos", "items": [], "collapsed": bool(repo)}
    try:
        repos = dml("repo", "list")
        for repo_item in repos:
            is_current = repo == repo_item["name"]
            repo_section["items"].append({
                "name": repo_item["name"],
                "url": url_for("main", repo=repo_item["name"]),
                "icon": "bi-folder2" if is_current else "bi-folder",
                "type": "repo",
                "active": is_current
            })
    except Exception as e:
        logger.warning(f"Failed to get repositories: {e}")
        repo_section['items'].append({
            'name': 'Error loading repositories',
            'url': '#',
            'icon': 'bi-exclamation-triangle',
            'type': 'error'
        })
    sidebar["sections"].append(repo_section)
    
    # Show branches section if repo is selected
    if repo:
        branch_section = {"title": "Branches", "type": "branches", "items": [], "collapsed": bool(branch)}
        try:
            branches = dml("branch", "list")
            for branch_name in branches:
                is_current = branch == branch_name
                branch_section['items'].append({
                    'name': branch_name,
                    'url': url_for('main', repo=repo, branch=branch_name),
                    'icon': 'bi-git',
                    'type': 'branch',
                    'active': is_current
                })
        except Exception as e:
            logger.warning(f"Failed to get branches for repo {repo}: {e}")
            branch_section['items'].append({
                'name': 'Error loading branches',
                'url': '#',
                'icon': 'bi-exclamation-triangle',
                'type': 'error'
            })
        sidebar["sections"].append(branch_section)
    
    # Show DAGs section if branch is selected
    if repo and branch:
        dag_section = {"title": "DAGs", "type": "dags", "items": [], "collapsed": bool(dag_id)}
        try:
            dags = dml("dag", "list")
            for dag_item in dags:
                dag_name = dag_item.get("name", dag_item["id"][:8])
                is_current = dag_id == dag_item["id"]
                dag_section['items'].append({
                    'name': dag_name,
                    'display_name': f"{dag_name}" if dag_item.get("name") else dag_item["id"][:8],
                    'url': url_for('dag_route', repo=repo, branch=branch, dag_id=dag_item["id"]),
                    'icon': 'bi-diagram-3',
                    'type': 'dag',
                    'dag_id': dag_item["id"],
                    'active': is_current
                })
        except Exception as e:
            logger.warning(f"Failed to get DAGs for {repo}/{branch}: {e}")
            dag_section['items'].append({
                'name': 'Error loading DAGs',
                'url': '#',
                'icon': 'bi-exclamation-triangle',
                'type': 'error'
            })
        sidebar["sections"].append(dag_section)
    
    return sidebar


@app.route("/dag")
def dag_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    if not dag_id:
        return "DAG ID is required", 400
    dml = Dml(repo=repo, branch=branch)
    breadcrumbs = get_breadcrumbs(repo, branch, dag_id, None)
    sidebar = get_sidebar_data(dml, repo, branch, dag_id, None)
    return render_template(
        "dag.html",
        repo=repo,
        branch=branch,
        dag_id=dag_id,
        breadcrumbs=breadcrumbs,
        sidebar=sidebar,
    )

@app.route("/node")
def node_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    node_id = request.args.get("node_id")
    dml = Dml(repo=repo, branch=branch)
    
    # Get DAG data for breadcrumbs and sidebar
    dag_info = get_dag_info(dml, dag_id)
    dag_data = dag_info.get("dag_data")
    breadcrumbs = get_breadcrumbs(repo, branch, dag_id, dag_data)
    sidebar = get_sidebar_data(dml, repo, branch, dag_id, dag_data)
    
    data = get_node_info(dml, dag_id, node_id)
    return render_template(
        "node.html",
        breadcrumbs=breadcrumbs,
        sidebar=sidebar,
        dag_id=dag_id,
        dag_link=url_for("dag_route", repo=repo, branch=branch, dag_id=dag_id),
        node_id=node_id,
        **data,
    )

@app.route("/")
def main():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dml = Dml(repo=repo, branch=branch)
    breadcrumbs = get_breadcrumbs(repo, branch, None, None)
    sidebar = get_sidebar_data(dml, repo, branch, None, None)
    return render_template("index.html", breadcrumbs=breadcrumbs, sidebar=sidebar)

@app.route("/logs", methods=["GET"])
def get_logs():
    """
    Fetch logs for a specific DAG with pagination.

    Query Parameters:
    - stream: The log stream name to fetch (e.g. stdout, stderr)
    - next_token: Token for pagination
    - limit: Maximum number of log events to return
    """
    dml = Dml(repo=request.args.get("repo"), branch=request.args.get("branch"))
    dag_id = request.args.get("dag_id")
    stream = request.args.get("stream_name")
    next_token = request.args.get("next_token")
    limit = request.args.get("limit", 100, type=int)
    # Get the dag info to find the log stream details
    dag_info = get_dag_info(dml, dag_id)
    log_streams = dag_info.get("log_streams", {})
    # If the stream name doesn't exist in the log_streams, return an error
    if stream not in log_streams:
        return jsonify({
            "error": f"Log stream {stream} not found for DAG {dag_id}",
            "available_streams": list(log_streams.keys())
        }), 401
    # Get the log stream details
    stream_details = log_streams[stream]
    log_group = stream_details["log_group"]
    log_stream = stream_details["log_stream"]
    # Get the logs from CloudWatch
    cloudwatch_logs = CloudWatchLogs()
    logs = cloudwatch_logs.get_log_events(
        log_group_name=log_group,
        log_stream_name=log_stream,
        next_token=next_token,
        limit=min(limit, 1000),  # Limit to 1000 events max
        start_from_head=True
    )
    return jsonify(logs)

def reload_plugins():
    """Reload plugin modules to detect changes"""
    # Import and reload the plugins module to detect changes
    import dml_ui.plugins
    importlib.reload(dml_ui.plugins)
    
    # Get all modules related to plugins
    plugin_modules = []
    for module_name in list(sys.modules.keys()):
        if 'plugin' in module_name.lower() or module_name.startswith('dml_ui'):
            plugin_modules.append(module_name)
    
    # Reload the modules
    for module_name in plugin_modules:
        if module_name in sys.modules:
            try:
                importlib.reload(sys.modules[module_name])
            except Exception as e:
                logger.warning(f"Failed to reload module {module_name}: {e}")

# Legacy plugin endpoints removed - use /api/dag/plugins and /api/node/plugins instead


@app.route("/api/dag", methods=["GET"])
def api_dag_data():
    """
    API endpoint to get DAG data dynamically.
    Returns JSON with all DAG information including nodes, edges, stats, etc.
    """
    try:
        repo = request.args.get("repo")
        branch = request.args.get("branch")
        dag_id = request.args.get("dag_id")
        prune = request.args.get("prune", "false").lower() == "true"
        
        if not dag_id:
            return jsonify({"error": "dag_id parameter is required"}), 400
        
        dml = Dml(repo=repo, branch=branch)
        data = get_dag_info(dml, dag_id, prune=prune)
        
        # Extract components, keeping argv for frontend
        log_streams = data.pop("log_streams", {})
        dag_data = data.pop("dag_data")
        
        # Process argv data for frontend display
        # Use the new argv structure from node descriptions
        argv_data = []
        if dag_data.get("argv"):
            try:
                argv_node_ids = dag_data["argv"]
                # Normalize argv_node_ids to always be a list for consistent processing
                if isinstance(argv_node_ids, str):
                    argv_node_ids = [argv_node_ids]
                elif isinstance(argv_node_ids, list):
                    pass  # Already a list
                else:
                    argv_node_ids = []
                
                # For each argv node, get its description to extract argv node descriptions
                for node_id in argv_node_ids:
                    try:
                        # Get node description with argv data
                        node_description = dml("node", "describe", node_id)
                        if node_description and "argv" in node_description:
                            argv_list = node_description["argv"]
                            if argv_list is not None and isinstance(argv_list, list):
                                # Each item in argv_list is a dict describing an argv node
                                for argv_node_desc in argv_list:
                                    # Add navigation link to each argv node
                                    argv_node_with_link = argv_node_desc.copy()
                                    if "id" in argv_node_desc:
                                        argv_node_with_link["link"] = url_for(
                                            "node_route",
                                            repo=repo,
                                            branch=branch,
                                            dag_id=dag_id,
                                            node_id=argv_node_desc["id"]
                                        )
                                    argv_data.append(argv_node_with_link)
                    except Exception as e:
                        logger.warning(f"Failed to get argv data for node {node_id}: {e}")
                        # Fall back to basic node info without argv descriptions
                        node_info = next((node for node in dag_data["nodes"] if node["id"] == node_id), None)
                        if node_info:
                            node_with_link = node_info.copy()
                            node_with_link["link"] = url_for(
                                "node_route",
                                repo=repo,
                                branch=branch,
                                dag_id=dag_id,
                                node_id=node_id
                            )
                            argv_data.append(node_with_link)
            except Exception as e:
                logger.error(f"Error processing argv data: {e}")
                argv_data = []
        
        # Add node links for frontend navigation
        for node in dag_data["nodes"]:
            node["link"] = url_for(
                "node_route",
                repo=repo,
                branch=branch,
                dag_id=dag_id,
                node_id=node["id"] or "",
            )
            if node["node_type"] in ["import", "fn"]:
                node["parent_link"] = url_for("dag_route", repo=repo, branch=branch, dag_id=node["parent"])
                if node["node_type"] == "fn":
                    node["sublist"] = [
                        [
                            x,
                            url_for(
                                "node_route",
                                repo=repo,
                                branch=branch,
                                dag_id=dag_id,
                                node_id=x,
                            ),
                        ]
                        for x in node["sublist"]
                    ]
        
        # Prepare response data
        response_data = {
            "dag_data": dag_data,
            "log_streams": log_streams,
            "argv": argv_data,
            **data  # Include script, error, result, html_uri etc.
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching DAG data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/dag/plugins", methods=["GET"])
def api_dag_plugins():
    """
    API endpoint to list all available DAG dashboard plugins.
    Returns JSON array of plugin metadata.
    """
    print("Fetching DAG plugins")
    try:
        # Reload plugins to detect changes
        reload_plugins()
        print("Plugins reloaded successfully")
        
        plugins_list = []
        for plugin_cls in discover_dag_plugins():
            print(f"Found DAG plugin: {plugin_cls.NAME}")
            plugins_list.append({
                "id": plugin_cls.NAME,
                "name": plugin_cls.NAME,
                "description": plugin_cls.DESCRIPTION or 'No description available',
            })
        print(f"Total DAG plugins found: {len(plugins_list)}")
        return jsonify(plugins_list)
    except Exception as e:
        logger.error(f"Error loading DAG plugins: {e}")
        return jsonify({"error": "Failed to load DAG plugins"}), 500

@app.route("/api/dag/plugins/<string:plugin_id>", methods=["GET"])
def api_dag_plugin_content(plugin_id):
    """
    API endpoint to get DAG plugin content for a specific plugin.
    Returns HTML content that will be embedded in an iframe.
    """
    print(f"Fetching content for DAG plugin: {plugin_id}")
    try:
        # Reload plugins to detect changes
        reload_plugins()
        
        # Find the plugin by ID
        plugins = [x for x in discover_dag_plugins() if x.NAME == plugin_id]
        if not plugins:
            return f"<div style='text-align: center; padding: 50px;'><h3>DAG Plugin '{plugin_id}' not found</h3></div>", 404
        
        if len(plugins) > 1:
            return f"<div style='text-align: center; padding: 50px;'><h3>Multiple DAG plugins found with name '{plugin_id}'</h3></div>", 500
        
        plugin_cls = plugins[0]
        
        # Get DAG data
        dag_id = request.args.get("dag_id")
        if not dag_id:
            return "<div style='text-align: center; padding: 50px;'><h3>No DAG ID provided</h3></div>", 400
        
        repo = request.args.get("repo")
        branch = request.args.get("branch")
        dml = Dml(repo=repo, branch=branch)
        
        # Load the actual DAG object
        dag = dml.load(dag_id)
        
        # Initialize and render the plugin with dml instance and loaded dag
        plugin_instance = plugin_cls(dml, dag)
        try:
            rendered_content = plugin_instance.render()
        except Exception as plugin_error:
            logger.error(f"DAG Plugin {plugin_id} failed to render: {plugin_error}")
            rendered_content = f"""
            <div class="alert alert-danger">
                <h4><i class="bi bi-exclamation-triangle"></i> DAG Plugin Error</h4>
                <p><strong>Plugin:</strong> {plugin_cls.NAME}</p>
                <p><strong>Error:</strong> {str(plugin_error)}</p>
                <details class="mt-3">
                    <summary>Technical Details</summary>
                    <pre class="mt-2 p-2 bg-light"><code>{repr(plugin_error)}</code></pre>
                </details>
            </div>
            """
        
        # Wrap content in a complete HTML document for iframe
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{plugin_cls.NAME}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }}
                .plugin-container {{
                    max-width: 100%;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            <div class="plugin-container">
                {rendered_content}
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        
        return html_content, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        logger.error(f"Error rendering DAG plugin {plugin_id}: {e}", exc_info=True)
        return f"<div class='alert alert-danger'>Error: {str(e)}</div>", 500

@app.route("/api/node/plugins", methods=["GET"])
def api_node_plugins():
    """
    API endpoint to list all available Node dashboard plugins.
    Returns JSON array of plugin metadata.
    """
    try:
        # Reload plugins to detect changes
        reload_plugins()
        
        plugins_list = []
        for plugin_cls in discover_node_plugins():
            plugins_list.append({
                "id": plugin_cls.NAME,
                "name": plugin_cls.NAME,
                "description": getattr(plugin_cls, 'DESCRIPTION', 'No description available')
            })
        
        return jsonify(plugins_list)
    except Exception as e:
        logger.error(f"Error loading Node plugins: {e}")
        return jsonify({"error": "Failed to load Node plugins"}), 500

@app.route("/api/node/plugins/<string:plugin_id>", methods=["GET"])
def api_node_plugin_content(plugin_id):
    """
    API endpoint to get Node plugin content for a specific plugin.
    Returns HTML content that will be embedded in an iframe.
    """
    try:
        # Reload plugins to detect changes
        reload_plugins()
        
        # Find the plugin by ID
        plugins = [x for x in discover_node_plugins() if x.NAME == plugin_id]
        if not plugins:
            return f"<div style='text-align: center; padding: 50px;'><h3>Node Plugin '{plugin_id}' not found</h3></div>", 404
        
        if len(plugins) > 1:
            return f"<div style='text-align: center; padding: 50px;'><h3>Multiple Node plugins found with name '{plugin_id}'</h3></div>", 500
        
        plugin_cls = plugins[0]
        
        # Get Node data
        dag_id = request.args.get("dag_id")
        node_id = request.args.get("node_id")
        if not dag_id or not node_id:
            return "<div style='text-align: center; padding: 50px;'><h3>DAG ID and Node ID are required</h3></div>", 400
        
        repo = request.args.get("repo")
        branch = request.args.get("branch")
        dml = Dml(repo=repo, branch=branch)
        
        # Load the DAG and get the node
        dag = dml.load(dag_id)
        node = dag[node_id]
        
        # Initialize and render the plugin with dml instance and node
        plugin_instance = plugin_cls(dml, node)
        # Set the DAG ID for plugins that need it (like NodeDetailsPlugin)
        plugin_instance._current_dag_id = dag_id
        try:
            rendered_content = plugin_instance.render()
        except Exception as plugin_error:
            logger.error(f"Node Plugin {plugin_id} failed to render: {plugin_error}")
            rendered_content = f"""
            <div class="alert alert-danger">
                <h4><i class="bi bi-exclamation-triangle"></i> Node Plugin Error</h4>
                <p><strong>Plugin:</strong> {plugin_cls.NAME}</p>
                <p><strong>Error:</strong> {str(plugin_error)}</p>
                <details class="mt-3">
                    <summary>Technical Details</summary>
                    <pre class="mt-2 p-2 bg-light"><code>{repr(plugin_error)}</code></pre>
                </details>
            </div>
            """
        
        # Wrap content in a complete HTML document for iframe
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{plugin_cls.NAME}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }}
                .plugin-container {{
                    max-width: 100%;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            <div class="plugin-container">
                {rendered_content}
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """
        
        return html_content, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        logger.error(f"Error rendering Node plugin {plugin_id}: {e}", exc_info=True)
        return f"<div class='alert alert-danger'>Error: {str(e)}</div>", 500

def run():
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG)
    app.run(debug=args.debug, port=args.port)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
