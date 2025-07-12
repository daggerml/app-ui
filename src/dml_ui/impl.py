import logging
from argparse import ArgumentParser

from daggerml import Dml
from flask import Flask, jsonify, render_template, request, url_for

from dml_ui.cloudwatch import CloudWatchLogs
from dml_ui.plugins import discover_dashboard_plugins
from dml_ui.util import get_dag_info, get_node_info

logger = logging.getLogger(__name__)
app = Flask(__name__)


def get_breadcrumbs(repo, branch, dag_id=None, commit_id=None):
    """Generate breadcrumb navigation data"""
    breadcrumbs = []
    if repo:
        breadcrumbs.append({
            "name": repo,
            "url": url_for("repo_route", repo=repo),
            "icon": "fa fa-star-of-david",
        })
        if branch:
            breadcrumbs.append({
                "name": branch,
                "url": url_for("commit_route", repo=repo, branch=branch),
                "icon": "fa fa-code-branch",
            })
        if commit_id:
            breadcrumbs.append({
                "name": commit_id.split("/")[-1][:8],
                "url": url_for("commit_route", repo=repo, commit_id=commit_id),
                "icon": "fa fa-code-commit",  # "fas fa-umbrella"
            })
        if dag_id:
            breadcrumbs.append({
                "name": "DAG " + dag_id.split("/")[-1][:12],
                "url": url_for("dag_route", repo=repo, dag_id=dag_id),
                "icon": "fa fa-project-diagram",
            })
    return breadcrumbs

def get_sidebar_data(dml, repo, branch, dag_id=None):
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
                "url": url_for("repo_route", repo=repo_item["name"]),
                "icon": "fa fa-star-of-david",
                "type": "repo",
                "active": is_current
            })
    except Exception as e:
        logger.warning(f"Failed to get repositories: {e}")
        repo_section['items'].append({
            'name': 'Error loading repositories',
            'url': '#',
            'icon': 'fa fa-exclamation-triangle',
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
                    'url': url_for('commit_route', repo=repo, branch=branch_name),
                    'icon': 'fa fa-code-branch',
                    'type': 'branch',
                    'active': is_current
                })
        except Exception as e:
            logger.warning(f"Failed to get branches for repo {repo}: {e}")
            branch_section['items'].append({
                'name': 'Error loading branches',
                'url': '#',
                'icon': 'fa fa-exclamation-triangle',
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
                    'url': url_for('dag_route', repo=repo, branch=branch, dag_id=dag_item["id"]),
                    'icon': 'fa fa-project-diagram',
                    'type': 'dag',
                    'active': is_current
                })
        except Exception as e:
            logger.warning(f"Failed to get DAGs for {repo}/{branch}: {e}")
            dag_section['items'].append({
                'name': 'Error loading DAGs',
                'url': '#',
                'icon': 'fa fa-exclamation-triangle',
                'type': 'error'
            })
        sidebar["sections"].append(dag_section)
    return sidebar


@app.route("/commit")
def commit_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    commit_id = request.args.get("commit_id")
    
    # If no branch is provided but we have a commit_id, we need to find a branch that contains it
    # This is for non-HEAD commits that are accessed directly by commit ID
    if not branch and commit_id and repo:
        try:
            # Create a DML instance without branch to query branches
            temp_dml = Dml(repo=repo)
            # Try to find which branch contains this commit
            branches_result = temp_dml("branch", "list")
            if branches_result and "branches" in branches_result:
                # Try each branch to see if it contains the commit
                for branch_name in branches_result["branches"]:
                    try:
                        branch_dml = Dml(repo=repo, branch=branch_name)
                        commit_data = branch_dml("commit", "describe", commit_id)
                        if commit_data:
                            # Found the commit in this branch, use it
                            branch = branch_name
                            break
                    except Exception:
                        # Commit not in this branch, try next
                        continue
        except Exception as e:
            logger.error(f"Failed to find branch for commit {commit_id}: {e}")
    
    # Create DML instance with the determined branch (or None if not found)
    dml = Dml(repo=repo, branch=branch)
    
    # Get commit data
    try:
        if commit_id:
            commit_data = dml("commit", "describe", commit_id)
        else:
            # Get current commit (HEAD) if no commit_id specified
            commit_data = dml("commit", "describe")
            commit_id = commit_data.get("id") if commit_data else None
    except Exception as e:
        logger.error(f"Failed to get commit data: {e}")
        commit_data = None
    
    # Generate breadcrumbs and sidebar
    breadcrumbs = get_breadcrumbs(repo, branch, commit_id=commit_id)
    sidebar = get_sidebar_data(dml, repo, branch)
    return render_template(
        "commit.html",
        repo=repo,
        branch=branch,
        commit_id=commit_id,
        commit_data=commit_data,
        breadcrumbs=breadcrumbs,
        sidebar=sidebar,
    )

@app.route("/dag")
def dag_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    if not dag_id:
        return "DAG ID is required", 400
    dml = Dml(repo=repo, branch=branch)
    breadcrumbs = get_breadcrumbs(repo, branch, dag_id=dag_id)
    sidebar = get_sidebar_data(dml, repo, branch, dag_id=dag_id)
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
    breadcrumbs = get_breadcrumbs(repo, branch, dag_id=dag_id)
    sidebar = get_sidebar_data(dml, repo, branch, dag_id=dag_id)
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
    # If both repo and branch are selected, redirect to commit page
    if repo and branch:
        from flask import redirect
        return redirect(url_for("commit_route", repo=repo, branch=branch))
    # If only repo is selected, redirect to repo page
    elif repo:
        from flask import redirect
        return redirect(url_for("repo_route", repo=repo))
    dml = Dml(repo=repo, branch=branch)
    breadcrumbs = get_breadcrumbs(repo, branch)
    sidebar = get_sidebar_data(dml, repo, branch)
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
        error_response = {
            "error": f"Log stream {stream} not found for DAG {dag_id}",
            "available_streams": list(log_streams.keys())
        }
        return jsonify(error_response), 404
    # Get the log stream details
    stream_details = log_streams[stream]
    log_group = stream_details["log_group"]
    log_stream = stream_details["log_stream"]
    # Get the logs from CloudWatch
    logger.info(f"Fetching logs for DAG {dag_id}, stream {stream} with limit {limit}")
    cloudwatch_logs = CloudWatchLogs()
    logs = cloudwatch_logs.get_log_events(
        log_group_name=log_group,
        log_stream_name=log_stream,
        next_token=next_token,
        limit=min(limit, 1000),  # Limit to 1000 events max
        start_from_head=True
    )
    # Add AWS region and log stream details for console link
    logs["aws_region"] = cloudwatch_logs.region
    logs["log_group"] = log_group
    logs["log_stream"] = log_stream
    return jsonify(logs)


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
            **data  # Include script, error, result, html_uri etc.
        }
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error fetching DAG data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/<string:kind>/plugins", methods=["GET"])
def api_plugins(kind):
    """
    API endpoint to list all available dashboard plugins.
    Returns JSON array of plugin metadata.
    """
    logger.info(f"Fetching {kind} plugins")
    try:
        plugins_list = []
        for _id, plugin_cls in discover_dashboard_plugins(kind).items():
            logger.info(f"Found plugin: {_id} - {plugin_cls.NAME}")
            plugins_list.append({
                "id": _id,
                "name": plugin_cls.NAME,
                "description": plugin_cls.__doc__ or 'No description available',
            })
        logger.info(f"Total {kind} plugins found: {len(plugins_list)}")
        return jsonify(plugins_list)
    except Exception as e:
        logger.error(f"Error loading {kind} plugins: {e}")
        return jsonify({"error": f"Failed to load {kind} plugins"}), 500

# @app.route("/api/node/plugins/<string:plugin_id>", methods=["GET"])
@app.route("/api/<string:kind>/plugins/<string:plugin_id>", methods=["GET"])
def api_dashboard_content(kind, plugin_id):
    """
    API endpoint to get Dashboard content for a specific plugin.
    Returns HTML content that will be embedded in an iframe.
    """
    try:
        # Find the plugin by ID
        plugin_cls = discover_dashboard_plugins(kind).get(plugin_id)
        if not plugin_cls:
            return f"<div style='text-align: center; padding: 50px;'><h3>{kind.capitalize()} Plugin '{plugin_id}' not found</h3></div>", 404
        
        kw = request.args.to_dict()
        method = kw.pop("method", None)
        kw.pop("method_args", None)  # Remove method_args if present
        # Remove VS Code specific parameters that shouldn't be passed to plugins
        kw.pop("id", None)
        kw.pop("vscodeBrowserReqId", None)
        # Get method_args as a list, even if there's only one value
        method_args = request.args.getlist("method_args")
        
        # Handle missing branch parameter for plugins (similar to commit route)
        repo = kw.get("repo")
        branch = kw.get("branch")
        dag_id = kw.get("dag_id")
        
        if not branch and repo and dag_id:
            logger.info(f"No branch provided for plugin, trying to find branch for DAG {dag_id} in repo {repo}")
            try:
                # Create a DML instance without branch to query branches
                temp_dml = Dml(repo=repo)
                # Try to find which branch contains this DAG
                branches_result = temp_dml("branch", "list")
                logger.info(f"Available branches result: {branches_result}")
                if branches_result and "branches" in branches_result and branches_result["branches"]:
                    # Try each branch to see if it contains the DAG
                    for branch_name in branches_result["branches"]:
                        try:
                            logger.info(f"Trying branch: {branch_name}")
                            branch_dml = Dml(repo=repo, branch=branch_name)
                            # Try to load the DAG to see if it exists in this branch
                            dag_data = branch_dml("dag", "describe", dag_id)
                            if dag_data:
                                # Found the DAG in this branch, use it
                                logger.info(f"Found DAG {dag_id} in branch {branch_name}")
                                branch = branch_name
                                kw["branch"] = branch
                                break
                        except Exception as e:
                            # DAG not in this branch, try next
                            logger.info(f"DAG {dag_id} not found in branch {branch_name}: {e}")
                            continue
                    
                    # If we still don't have a branch, use the first available branch as fallback
                    if not branch:
                        logger.warning(f"Could not find branch containing DAG {dag_id}, using first available branch as fallback")
                        branch = branches_result["branches"][0]
                        kw["branch"] = branch
                        logger.info(f"Using fallback branch: {branch}")
                else:
                    logger.warning(f"No branches found in repository {repo}, using 'main' as fallback")
                    # Ultimate fallback - use "main" if no branches can be listed
                    branch = "main"
                    kw["branch"] = branch
                    logger.info(f"Using ultimate fallback branch: {branch}")
            except Exception as e:
                logger.error(f"Failed to find branch for DAG {dag_id}: {e}")
                # Ultimate fallback - use "main" if all else fails
                if not branch:
                    branch = "main"
                    kw["branch"] = branch
                    logger.info(f"Exception fallback, using branch: {branch}")
        
        # Final safety check - ensure we always have a branch
        if not kw.get("branch"):
            kw["branch"] = "main"
            logger.info("Final safety fallback, using branch: main")
        
        plugin_instance = plugin_cls(**kw)
        if method:
            # If a method is specified, call it with the provided arguments and return the result
            if not hasattr(plugin_instance, method):
                return f"<div style='text-align: center; padding: 50px;'><h3>Method '{method}' not found in {kind.capitalize()} Plugin '{plugin_id}'</h3></div>", 404
            method_result = getattr(plugin_instance, method)(*method_args)
            # For HTMX requests, return HTML directly
            if isinstance(method_result, str):
                return method_result, 200, {'Content-Type': 'text/html'}
            else:
                return jsonify(method_result), 200
        rendered_content = plugin_instance.render()
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
            <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        </body>
        </html>
        """
        return html_content, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        logger.error(f"Error rendering {kind.capitalize()} plugin {plugin_id}: {e}", exc_info=True)
        rendered_content = f"""
        <div class="alert alert-danger">
            <h4><i class="fas fa-exclamation-triangle"></i> {kind.capitalize()} Plugin Error</h4>
            <p><strong>Plugin:</strong> {plugin_id}</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <details class="mt-3">
                <summary>Technical Details</summary>
                <pre class="mt-2 p-2 bg-light"><code>{repr(e)}</code></pre>
            </details>
        </div>
        """
        return rendered_content, 500

@app.route("/repo")
def repo_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")  # Optional for repo view
    if not repo:
        return "Repository is required", 400
    
    # For repo view, we don't need a specific branch context
    dml = Dml(repo=repo) if not branch else Dml(repo=repo, branch=branch)
    breadcrumbs = get_breadcrumbs(repo, branch)
    sidebar = get_sidebar_data(dml, repo, branch)
    
    return render_template(
        "repo.html",
        repo=repo,
        branch=branch,
        breadcrumbs=breadcrumbs,
        sidebar=sidebar,
    )

@app.route("/api/commit-log", methods=["GET"])
def get_commit_log():
    """
    Get commit log for repository visualization.
    
    Query Parameters:
    - repo: Repository name
    """
    repo = request.args.get("repo")
    
    if not repo:
        return jsonify({"error": "Repository is required"}), 400
    
    try:
        # We create Dml with repo only to get all commits from all branches
        dml = Dml(repo=repo)
        # Call dml commit log with JSON output to get all commits
        commits = dml("commit", "log", "--output", "json")
        return jsonify(commits)
    except Exception as e:
        logger.error(f"Failed to get commit log: {e}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 error handler"""
    return render_template("404.html"), 404

def run():
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG)
    app.run(debug=args.debug, port=args.port)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
