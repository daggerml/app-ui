import base64
import importlib.metadata
import io

import matplotlib.pyplot as plt

class DashboardPlugin:
    NAME = None
    DESCRIPTION = None

    def render(self, dag_data, **kwargs):
        """Return HTML (or Flask Response) to embed in the dashboard."""
        raise NotImplementedError


def discover_plugins():
    plugins = []
    for entry_point in importlib.metadata.entry_points(group="dml_ui.dashboard_plugins"):
        plugin_cls = entry_point.load()
        if issubclass(plugin_cls, DashboardPlugin):
            plugins.append(plugin_cls)
    return plugins

# In a separate package or your plugins directory
class MatplotlibStatsPlugin(DashboardPlugin):
    NAME = "Stats Chart"
    DESCRIPTION = "Shows a matplotlib chart of DAG stats"

    def render(self, dag_data, **kwargs):
        fig, ax = plt.subplots()
        ax.bar(["Nodes", "Edges"], [len(dag_data["nodes"]), len(dag_data["edges"])])
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return f'<img src="data:image/png;base64,{img_b64}" alt="DAG Stats Chart">'