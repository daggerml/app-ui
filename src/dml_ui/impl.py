import logging
import importlib
import sys
from argparse import ArgumentParser

from daggerml import Dml
from daggerml.core import Ref
from flask import Flask, jsonify, render_template, request, url_for

from dml_ui.cloudwatch import CloudWatchLogs
from dml_ui.plugins import discover_plugins
from dml_ui.util import get_dag_info, get_node_info

logger = logging.getLogger(__name__)
app = Flask(__name__)


def get_dropdowns(dml, repo, branch, dag_id):
    dropdowns = {"repos": {x["name"]: url_for("main", repo=x["name"]) for x in dml("repo", "list")}}
    if repo is not None:
        dropdowns["branches"] = {x: url_for("main", repo=repo, branch=x) for x in dml("branch", "list")}
    if branch is not None:
        tmp = {x["name"]: x["id"] for x in dml("dag", "list")}
        dropdowns["dags"] = {k: url_for("dag_route", repo=repo, branch=branch, dag_id=v) for k, v in tmp.items()}
    return dropdowns

def get_breadcrumbs(dml, repo, branch, dag_id, dag_data=None):
    """Generate breadcrumb navigation data"""
    breadcrumbs = []
    # Home breadcrumb
    breadcrumbs.append({
        'name': 'Home',
        'url': url_for('main'),
        'icon': 'bi-house'
    })
    if repo:
        # Repo breadcrumb
        breadcrumbs.append({
            'name': repo,
            'url': url_for('main', repo=repo),
            'icon': 'bi-folder'
        })
        if branch:
            # Branch breadcrumb
            breadcrumbs.append({
                'name': branch,
                'url': url_for('main', repo=repo, branch=branch),
                'icon': 'bi-git'
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
    
    # Show nodes section if DAG is selected
    if repo and branch and dag_id and dag_data:
        node_section = {"title": "Nodes", "type": "nodes", "items": [], "collapsed": False}
        nodes = dag_data.get("nodes", [])
        for node in nodes:
            node_name = node.get("name", f"#{node['id'][:8]}")
            node_section['items'].append({
                'name': node_name,
                'display_name': node_name,
                'url': url_for('node_route', repo=repo, branch=branch, dag_id=dag_id, node_id=node["id"]),
                'icon': f'bi-{get_node_icon(node.get("node_type", "unknown"))}',
                'type': 'node',
                'node_type': node.get("node_type", "unknown"),
                'node_id': node["id"]
            })
        sidebar["sections"].append(node_section)
    
    return sidebar

def get_node_icon(node_type):
    """Get appropriate icon for node type"""
    icon_map = {
        'fn': 'gear',
        'import': 'box-arrow-in-down',
        'literal': 'file-text',
        'argv': 'terminal'
    }
    return icon_map.get(node_type, 'circle')


cloudwatch_logs = CloudWatchLogs()

@app.route("/dag")
def dag_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    dml = Dml(repo=repo, branch=branch)
    data = get_dag_info(dml, dag_id)
    data.pop("argv", None)
    # data.update(data.pop("result", {}))
    log_streams = data.pop("log_streams", {})
    dag_data = data.pop("dag_data")
    
    # Generate breadcrumbs and sidebar data
    breadcrumbs = get_breadcrumbs(dml, repo, branch, dag_id, dag_data)
    sidebar = get_sidebar_data(dml, repo, branch, dag_id, dag_data)
    
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
    return render_template("dag.html", data=dag_data, log_streams=log_streams, breadcrumbs=breadcrumbs, sidebar=sidebar, **data)

@app.route("/node")
def node_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    node_id = request.args.get("node_id")
    dml = Dml(repo=repo, branch=branch)
    dropdowns = get_dropdowns(dml, repo, branch, dag_id)
    
    # Get DAG data for breadcrumbs and sidebar
    dag_info = get_dag_info(dml, dag_id)
    dag_data = dag_info.get("dag_data")
    breadcrumbs = get_breadcrumbs(dml, repo, branch, dag_id, dag_data)
    sidebar = get_sidebar_data(dml, repo, branch, dag_id, dag_data)
    
    data = get_node_info(dml, dag_id, node_id)
    return render_template(
        "node.html",
        dropdowns=dropdowns,
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
    dropdowns = get_dropdowns(dml, repo, branch, None)
    breadcrumbs = get_breadcrumbs(dml, repo, branch, None, None)
    sidebar = get_sidebar_data(dml, repo, branch, None, None)
    return render_template("index.html", dropdowns=dropdowns, breadcrumbs=breadcrumbs, sidebar=sidebar)

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

@app.route("/api/plugins", methods=["GET"])
def api_plugins():
    """
    API endpoint to list all available dashboard plugins.
    Returns JSON array of plugin metadata.
    """
    try:
        # Reload plugins to detect changes
        reload_plugins()
        
        plugins_list = []
        for plugin_cls in discover_plugins():
            plugins_list.append({
                "id": plugin_cls.NAME,
                "name": plugin_cls.NAME,
                "description": getattr(plugin_cls, 'DESCRIPTION', 'No description available')
            })
        
        return jsonify(plugins_list)
    except Exception as e:
        logger.error(f"Error loading plugins: {e}")
        return jsonify({"error": "Failed to load plugins"}), 500

@app.route("/api/plugins/<string:plugin_id>", methods=["GET"])
def api_plugin_content(plugin_id):
    """
    API endpoint to get plugin content for a specific plugin.
    Returns HTML content that will be embedded in an iframe.
    """
    try:
        # Reload plugins to detect changes
        reload_plugins()
        
        # Find the plugin by ID
        plugins = [x for x in discover_plugins() if x.NAME == plugin_id]
        if not plugins:
            return f"<div style='text-align: center; padding: 50px;'><h3>Plugin '{plugin_id}' not found</h3></div>", 404
        
        if len(plugins) > 1:
            return f"<div style='text-align: center; padding: 50px;'><h3>Multiple plugins found with name '{plugin_id}'</h3></div>", 500
        
        plugin_cls = plugins[0]
        
        # Get DAG data
        dag_id = request.args.get("dag_id")
        if not dag_id:
            return "<div style='text-align: center; padding: 50px;'><h3>No DAG ID provided</h3></div>", 400
        
        repo = request.args.get("repo")
        branch = request.args.get("branch")
        dml = Dml(repo=repo, branch=branch)
        
        # Use the same DAG retrieval logic as get_dag_info
        # First get the DAG description for structure/metadata
        dag_data = dml("dag", "describe", dag_id)
        # Then load the actual DAG object for value access
        dag = dml.load(dag_id)
        
        # Initialize and render the plugin with dml instance and loaded dag
        plugin_instance = plugin_cls()
        try:
            rendered_content = plugin_instance.render(
                dml, 
                dag_data,  # Pass the described DAG structure (like in get_dag_info)
                dag_id=dag_id,
                repo=repo,
                branch=branch,
                dag_object=dag  # Also pass the loaded DAG object for value access if needed
            )
        except Exception as plugin_error:
            logger.error(f"Plugin {plugin_id} failed to render: {plugin_error}")
            rendered_content = f"""
            <div class="alert alert-danger">
                <h4><i class="bi bi-exclamation-triangle"></i> Plugin Error</h4>
                <p><strong>Plugin:</strong> {plugin_cls.NAME}</p>
                <p><strong>Error:</strong> {str(plugin_error)}</p>
                <details class="mt-3">
                    <summary>Technical Details</summary>
                    <pre class="mt-2 p-2 bg-light"><code>{repr(plugin_error)}</code></pre>
                </details>
                <div class="mt-3">
                    <small class="text-muted">
                        This plugin may not be compatible with the current DAG structure or data format.
                        Check the plugin implementation or try a different plugin.
                    </small>
                </div>
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
        logger.error(f"Error rendering plugin {plugin_id}: {e}", exc_info=True)
        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Plugin Error</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css">
        </head>
        <body>
            <div class="container mt-5">
                <div class="alert alert-danger">
                    <h4><i class="bi bi-exclamation-triangle"></i> Plugin System Error</h4>
                    <p><strong>Plugin ID:</strong> {plugin_id}</p>
                    <p><strong>Error:</strong> {str(e)}</p>
                    <details class="mt-3">
                        <summary>Technical Details</summary>
                        <pre class="mt-2 p-2 bg-light"><code>{repr(e)}</code></pre>
                    </details>
                    <div class="mt-3">
                        <small class="text-muted">
                            This error occurred in the plugin system infrastructure. 
                            Please check the server logs for more details.
                        </small>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return error_html, 500, {'Content-Type': 'text/html'}

@app.route("/plugins/<string:plugin_name>")
def plugins(plugin_name):
    """
    Legacy plugin endpoint - kept for backwards compatibility.
    """
    plugins = [x for x in discover_plugins() if x.NAME == plugin_name]
    if not plugins:
        return jsonify({"error": f"Plugin {plugin_name} not found"}), 404
    if len(plugins) > 1:
        return jsonify({"error": f"Multiple plugins found with name {plugin_name}"}), 500
    plugin = plugins[0]
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dml = Dml(repo=repo, branch=branch)
    dag_id = request.args.get("dag_id")
    
    # Get raw DAG object instead of processed dag_data
    dag = dml("dag", "get", dag_id)
    
    # Render plugin with new signature
    rendered_html = plugin().render(dml, dag, repo=repo, branch=branch, dag_id=dag_id)
    return render_template("plugin.html", plugin=plugin, rendered_html=rendered_html, dag=dag)

@app.route("/idx")
def idx():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dml = Dml(repo=repo, branch=branch)
    dropdowns = get_dropdowns(dml, repo, branch, None)
    breadcrumbs = get_breadcrumbs(dml, repo, branch, None, None)
    sidebar = get_sidebar_data(dml, repo, branch, None, None)
    return render_template("indexes.html", dropdowns=dropdowns, breadcrumbs=breadcrumbs, sidebar=sidebar)

@app.route("/kill-indexes", methods=["POST"])
def kill_idx():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dml = Dml(repo=repo, branch=branch)
    body = request.form.getlist("del-idx", type=str)
    for idx in body:
        dml("index", "delete", idx)
    idxs = dml("index", "list")
    for idx in idxs:
        idx["dag_link"] = url_for("dag_route", repo=repo, branch=branch, dag_id=idx["dag"])
    return jsonify({"deleted": len(body), "indexes": idxs})


def run():
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG)
    app.run(debug=args.debug, port=args.port)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
