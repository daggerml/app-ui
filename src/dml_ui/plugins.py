import importlib.metadata
import logging

from flask import url_for
from daggerml.core import Dag, Dml, Node

logger = logging.getLogger(__name__)

class DashboardPlugin:
    """Base dashboard plugin class."""
    NAME = None

    @classmethod
    def _id(cls):
        """Unique identifier for the plugin, used in URLs and storage."""
        return f"{cls.__module__}:{cls.__name__}"

    def render(self):
        """Return HTML content for the dashboard."""
        raise NotImplementedError

    def url_for(self, obj):
        """Returns the URL for the provided DAG or Node object.
        
        Users can call this from within their `render` to get the URLs for other
        DAGs and nodes in their dashboards.
        """
        if isinstance(obj, Dag):
            return url_for("dag_route", dag_id=obj._ref.to)
        if isinstance(obj, Node):
            return url_for("node_route", dag_id=obj.dag._ref.to, node_id=obj.ref.to)
        return "#"

class DagDashboardPlugin(DashboardPlugin):

    def __init__(self, repo, branch, dag_id):
        self.repo = repo
        self.branch = branch
        self.dag_id = dag_id
        self.dml = Dml(repo=repo, branch=branch)
        self.dag = self.dml.load(dag_id)

    def method_call_url(self, method_name, *args):
        """Returns a URL to call a method on this plugin with the given arguments."""
        return url_for(
            "api_dashboard_content",
            kind="dag",
            repo=self.repo,
            branch=self.branch,
            dag_id=self.dag_id,
            plugin_id=self._id(),
            method=method_name,
            # method_args=args,
        )

class NodeDashboardPlugin(DashboardPlugin):
    def __init__(self, repo, branch, dag_id, node_id):
        self.repo = repo
        self.branch = branch
        self.dag_id = dag_id
        self.node_id = node_id
        self.dml = Dml(repo=repo, branch=branch)
        self.dag = self.dml.load(dag_id)
        self.node = self.dag[node_id]

    def method_call_url(self, method_name, *args):
        """Returns a URL to call a method on this plugin with the given arguments."""
        return url_for(
            "api_dashboard_content",
            kind="node",
            repo=self.repo,
            branch=self.branch,
            dag_id=self.dag_id,
            node_id=self.node_id,
            plugin_id=self._id(),
            method=method_name,
            # method_args=args,
        )

def discover_dashboard_plugins(group):
    """Discover all available plugins for a given group"""
    plugins = {}
    for entry_point in importlib.metadata.entry_points(group=f"dml_ui.dashboard.{group}"):
        try:
            plugin_cls = entry_point.load()
            plugins[plugin_cls._id()] = plugin_cls
        except Exception as e:
            logger.warning(f"Failed to load plugin from entry point {entry_point.name}: {e}")
    return plugins