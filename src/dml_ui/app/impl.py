import logging
from argparse import ArgumentParser

from daggerml import Dml
from flask import Flask, jsonify, render_template, request, url_for

from dml_ui.app.util import get_dag_info, get_node_info
from dml_ui.cloudwatch import CloudWatchLogs
from dml_ui.plugins import discover_plugins

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


cloudwatch_logs = CloudWatchLogs()

@app.route("/dag")
def dag_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    dml = Dml()
    dropdowns = get_dropdowns(dml, repo, branch, dag_id)
    data = get_dag_info(dml, dag_id)
    data.pop("argv", None)
    log_streams = data.pop("log_streams", {})
    dag_data = data.pop("dag_data")
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

    # Dashboard plugin discovery
    from dml_ui.plugins import discover_plugins
    dashboard_plugins = [
        {"id": plugin_cls.NAME.lower().replace(" ", "_"), "name": plugin_cls.NAME, "description": getattr(plugin_cls, "DESCRIPTION", "")}
        for plugin_cls in discover_plugins()
        if getattr(plugin_cls, "NAME", None)
    ]

    return render_template(
        "dag.html",
        dropdowns=dropdowns,
        data=dag_data,
        log_streams=log_streams,
        dashboard_plugins=dashboard_plugins,
        **data
    )


# Serve dashboard plugin content in isolation
@app.route("/dashboard_plugin/<plugin_id>")
def dashboard_plugin_route(plugin_id):
    from dml_ui.plugins import discover_plugins
    plugins = [p for p in discover_plugins() if getattr(p, "NAME", "").lower().replace(" ", "_") == plugin_id]
    if not plugins:
        return f"<div class='alert alert-danger'>Dashboard plugin '{plugin_id}' not found.</div>", 404
    plugin_cls = plugins[0]
    dml = Dml()
    dag_id = request.args.get("dag_id")
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_data = get_dag_info(dml, dag_id)
    plugin_instance = plugin_cls()
    try:
        html = plugin_instance.render(dag_data, repo=repo, branch=branch, dag_id=dag_id)
    except Exception as e:
        html = f"<div class='alert alert-danger'>Error rendering dashboard: {e}</div>"
    return f"""
    <html><head><meta charset='utf-8'><title>{plugin_cls.NAME}</title></head>
    <body style='margin:0;padding:0;'>
    {html}
    </body></html>
    """

@app.route("/node")
def node_route():
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    node_id = request.args.get("node_id")
    dml = Dml()
    dropdowns = get_dropdowns(dml, repo, branch, dag_id)
    data = get_node_info(dml, dag_id, node_id)
    return render_template(
        "node.html",
        dropdowns=dropdowns,
        dag_id=dag_id,
        dag_link=url_for("dag_route", repo=repo, branch=branch, dag_id=dag_id),
        node_id=node_id,
        **data,
    )

@app.route("/")
def main():
    dml = Dml()
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dropdowns = get_dropdowns(dml, repo, branch, None)
    return render_template("index.html", dropdowns=dropdowns)

@app.route("/logs", methods=["GET"])
def get_logs():
    """
    Fetch logs for a specific DAG with pagination.

    Query Parameters:
    - stream: The log stream name to fetch (e.g. stdout, stderr)
    - next_token: Token for pagination
    - limit: Maximum number of log events to return
    """
    dml = Dml()
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

@app.route("/plugins/<string:plugin_name>")
def plugins(plugin_name):
    """
    Discover and list all available dashboard plugins.
    """
    plugins = [x for x in discover_plugins() if x.NAME == plugin_name]
    if not plugins:
        return jsonify({"error": f"Plugin {plugin_name} not found"}), 404
    if len(plugins) > 1:
        return jsonify({"error": f"Multiple plugins found with name {plugin_name}"}), 500
    plugin = plugins[0]
    dml = Dml()
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dag_id = request.args.get("dag_id")
    dag_data = get_dag_info(dml, dag_id)
    rendered_html = plugin.render(dag_data, repo=repo, branch=branch, dag_id=dag_id)
    return render_template("plugin.html", plugin=plugin, rendered_html=rendered_html, dag_data=dag_data)

@app.route("/idx")
def idx():
    dml = Dml()
    repo = request.args.get("repo")
    branch = request.args.get("branch")
    dropdowns = get_dropdowns(dml, repo, branch, None)
    return render_template("indexes.html", dropdowns=dropdowns)

@app.route("/kill-indexes", methods=["POST"])
def kill_idx():
    dml = Dml()
    repo = request.args.get("repo")
    branch = request.args.get("branch")
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
