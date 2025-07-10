import importlib.metadata
import logging

from flask import url_for
from daggerml.core import Dag, Node

logger = logging.getLogger(__name__)

class DashboardPlugin:
    NAME = None
    DESCRIPTION = None

    def __init__(self, dml):
        self.dml = dml

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
    def __init__(self, dml, dag: Dag):
        super().__init__(dml)
        self.dag = dag
        self._current_dag_id = dag._ref.to if hasattr(dag, '_ref') else None

class NodeDashboardPlugin(DashboardPlugin):
    def __init__(self, dml, node: Node):
        super().__init__(dml)
        self.node = node

def discover_dashboard_plugins(group):
    """Discover all available plugins for a given group"""
    plugins = {}
    for entry_point in importlib.metadata.entry_points(group=f"dml_ui.dashboard.{group}"):
        try:
            plugin_cls = entry_point.load()
            plugins[f"{plugin_cls.__module__}:{plugin_cls.__name__}"] = plugin_cls
        except Exception as e:
            logger.warning(f"Failed to load plugin from entry point {entry_point.name}: {e}")
    return plugins