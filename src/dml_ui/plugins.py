from flask import url_for
import importlib.metadata

from daggerml.core import Dag, Node

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
    def __init__(self, dml, dag):
        super().__init__(dml)
        self.dag = dag
        self._current_dag_id = dag._ref.to if hasattr(dag, '_ref') else None

class NodeDashboardPlugin(DashboardPlugin):
    def __init__(self, dml, node):
        super().__init__(dml)
        self.node = node


def discover_dag_plugins():
    """Discover all available DAG dashboard plugins"""
    import logging
    logger = logging.getLogger(__name__)
    
    plugins = []
    seen_names = set()
    
    # Add built-in DAG plugins
    built_in_plugins = [ExampleDagPlugin, DagStatsPlugin]
    
    for plugin_cls in built_in_plugins:
        try:
            if plugin_cls.NAME and plugin_cls.NAME not in seen_names:
                plugins.append(plugin_cls)
                seen_names.add(plugin_cls.NAME)
        except Exception as e:
            logger.warning(f"Failed to load built-in DAG plugin {plugin_cls.__name__}: {e}")
    
    # Then discover plugins from entry points
    try:
        for entry_point in importlib.metadata.entry_points(group="dml_ui.dashboard.dag"):
            try:
                plugin_cls = entry_point.load()
                if (issubclass(plugin_cls, DagDashboardPlugin) and 
                    plugin_cls.NAME and 
                    plugin_cls.NAME not in seen_names):
                    plugins.append(plugin_cls)
                    seen_names.add(plugin_cls.NAME)
            except Exception as e:
                logger.warning(f"Failed to load DAG plugin from entry point {entry_point.name}: {e}")
    except Exception as e:
        # Entry points might not be available in development
        logger.debug(f"DAG plugin entry points not available: {e}")
    
    return plugins

def discover_node_plugins():
    """Discover all available Node dashboard plugins"""
    import logging
    logger = logging.getLogger(__name__)
    
    plugins = []
    seen_names = set()
    
    # Add built-in Node plugins
    built_in_plugins = [ExampleNodePlugin, NodeDetailsPlugin]
    
    for plugin_cls in built_in_plugins:
        try:
            if plugin_cls.NAME and plugin_cls.NAME not in seen_names:
                plugins.append(plugin_cls)
                seen_names.add(plugin_cls.NAME)
        except Exception as e:
            logger.warning(f"Failed to load built-in Node plugin {plugin_cls.__name__}: {e}")
    
    # Then discover plugins from entry points
    try:
        for entry_point in importlib.metadata.entry_points(group="dml_ui.dashboard.node"):
            try:
                plugin_cls = entry_point.load()
                if (issubclass(plugin_cls, NodeDashboardPlugin) and 
                    plugin_cls.NAME and 
                    plugin_cls.NAME not in seen_names):
                    plugins.append(plugin_cls)
                    seen_names.add(plugin_cls.NAME)
            except Exception as e:
                logger.warning(f"Failed to load Node plugin from entry point {entry_point.name}: {e}")
    except Exception as e:
        # Entry points might not be available in development
        logger.debug(f"Node plugin entry points not available: {e}")
    
    return plugins




# DAG Dashboard Plugins
class ExampleDagPlugin(DagDashboardPlugin):
    NAME = "Example DAG Dashboard"
    DESCRIPTION = "An example DAG dashboard showing DAG-level information"

    def render(self):
        dag_id = self.dag._ref.to if hasattr(self.dag, '_ref') else 'Unknown'
        
        # Get DAG information
        dag_nodes = []
        try:
            # Access dag nodes through the dag object
            dag_data = self.dml("dag", "describe", dag_id)
            dag_nodes = dag_data.get("nodes", [])
        except Exception:
            pass
        
        html = f"""
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h5><i class="bi bi-diagram-3"></i> DAG Dashboard Example</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>DAG Information</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>DAG ID:</strong></td><td>{dag_id}</td></tr>
                                        <tr><td><strong>Node Count:</strong></td><td>{len(dag_nodes)}</td></tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>DAG Actions</h6>
                                    <div class="d-grid gap-2">
                                        <button class="btn btn-outline-primary btn-sm" onclick="alert('DAG action executed!')">
                                            <i class="bi bi-play"></i> Execute DAG
                                        </button>
                                        <button class="btn btn-outline-secondary btn-sm" onclick="alert('DAG exported!')">
                                            <i class="bi bi-download"></i> Export DAG
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html

class DagStatsPlugin(DagDashboardPlugin):
    NAME = "DAG Statistics"
    DESCRIPTION = "Shows detailed statistics about the DAG structure"

    def render(self):
        dag_id = self.dag._ref.to if hasattr(self.dag, '_ref') else 'Unknown'
        
        try:
            dag_data = self.dml("dag", "describe", dag_id)
            nodes = dag_data.get("nodes", [])
            edges = dag_data.get("edges", [])
            
            # Analyze node types
            node_types = {}
            for node in nodes:
                node_type = node.get("node_type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            # Create statistics
            stats_html = ""
            for node_type, count in node_types.items():
                percentage = (count / len(nodes)) * 100 if nodes else 0
                stats_html += f"""
                <div class="row mb-2">
                    <div class="col-4"><strong>{node_type.title()}:</strong></div>
                    <div class="col-4">{count}</div>
                    <div class="col-4">
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar" role="progressbar" style="width: {percentage}%">
                                {percentage:.1f}%
                            </div>
                        </div>
                    </div>
                </div>
                """
            
            html = f"""
            <div class="container-fluid">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5><i class="bi bi-bar-chart"></i> DAG Statistics</h5>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-md-4 text-center">
                                <h2 class="text-primary">{len(nodes)}</h2>
                                <p class="text-muted">Total Nodes</p>
                            </div>
                            <div class="col-md-4 text-center">
                                <h2 class="text-success">{len(edges)}</h2>
                                <p class="text-muted">Total Edges</p>
                            </div>
                            <div class="col-md-4 text-center">
                                <h2 class="text-warning">{len(node_types)}</h2>
                                <p class="text-muted">Node Types</p>
                            </div>
                        </div>
                        <h6>Node Type Distribution:</h6>
                        {stats_html}
                    </div>
                </div>
            </div>
            """
            
        except Exception as e:
            html = f"""
            <div class="alert alert-danger">
                <h5>Error loading DAG statistics</h5>
                <p>{str(e)}</p>
            </div>
            """
        
        return html

# Node Dashboard Plugins
class ExampleNodePlugin(NodeDashboardPlugin):
    NAME = "Example Node Dashboard"
    DESCRIPTION = "An example node dashboard showing node-level information"

    def render(self):
        node_id = self.node.ref.to if hasattr(self.node, 'ref') else 'Unknown'
        
        # Get node value safely
        node_value = "N/A"
        node_type = "Unknown"
        try:
            # Access the node's value
            node_value = str(self.node.value())[:200] + ("..." if len(str(self.node.value())) > 200 else "")
            
            # Get node metadata - we need the DAG ID for this
            if hasattr(self, '_current_dag_id'):
                dag_data = self.dml("dag", "describe", self._current_dag_id)
                for n in dag_data.get("nodes", []):
                    if n.get("id") == node_id:
                        node_type = n.get("node_type", "Unknown")
                        break
        except Exception as e:
            node_value = f"Error loading value: {str(e)}"
        
        html = f"""
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-success text-white">
                            <h5><i class="bi bi-node-plus"></i> Node Dashboard Example</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Node Information</h6>
                                    <table class="table table-sm">
                                        <tr><td><strong>Node ID:</strong></td><td><code>{node_id}</code></td></tr>
                                        <tr><td><strong>Node Type:</strong></td><td><span class="badge bg-secondary">{node_type}</span></td></tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>Node Actions</h6>
                                    <div class="d-grid gap-2">
                                        <button class="btn btn-outline-success btn-sm" onclick="alert('Node executed!')">
                                            <i class="bi bi-play-circle"></i> Execute Node
                                        </button>
                                        <button class="btn btn-outline-info btn-sm" onclick="alert('Node inspected!')">
                                            <i class="bi bi-search"></i> Inspect Node
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-12">
                                    <h6>Node Value Preview</h6>
                                    <pre class="bg-light p-2 rounded" style="max-height: 200px; overflow-y: auto;">{node_value}</pre>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html

class NodeDetailsPlugin(NodeDashboardPlugin):
    NAME = "Node Details"
    DESCRIPTION = "Shows detailed information about a node including dependencies"

    def render(self):
        node_id = self.node.ref.to if hasattr(self.node, 'ref') else 'Unknown'
        
        try:
            # We need the DAG ID to get detailed information
            if not hasattr(self, '_current_dag_id'):
                return """
                <div class="alert alert-warning">
                    <h5>DAG context required</h5>
                    <p>Cannot determine DAG context for detailed node information.</p>
                </div>
                """
            
            dag_data = self.dml("dag", "describe", self._current_dag_id)
            nodes = dag_data.get("nodes", [])
            edges = dag_data.get("edges", [])
            
            # Find current node
            current_node = None
            for n in nodes:
                if n.get("id") == node_id:
                    current_node = n
                    break
            
            if not current_node:
                return f"""
                <div class="alert alert-warning">
                    <h5>Node not found</h5>
                    <p>Node {node_id} was not found in DAG {self._current_dag_id}</p>
                </div>
                """
            
            # Find dependencies (incoming edges)
            dependencies = []
            dependents = []
            for edge in edges:
                if edge.get("target") == node_id:
                    dependencies.append(edge.get("source"))
                elif edge.get("source") == node_id:
                    dependents.append(edge.get("target"))
            
            dep_html = ""
            if dependencies:
                dep_html = "<ul>" + "".join([f"<li><code>{dep}</code></li>" for dep in dependencies]) + "</ul>"
            else:
                dep_html = "<p class='text-muted'>No dependencies</p>"
            
            dependent_html = ""
            if dependents:
                dependent_html = "<ul>" + "".join([f"<li><code>{dep}</code></li>" for dep in dependents]) + "</ul>"
            else:
                dependent_html = "<p class='text-muted'>No dependents</p>"
            
            html = f"""
            <div class="container-fluid">
                <div class="card">
                    <div class="card-header bg-warning text-dark">
                        <h5><i class="bi bi-info-circle"></i> Node Details</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <h6>Node Properties</h6>
                                <table class="table table-sm">
                                    <tr><td><strong>ID:</strong></td><td><code>{current_node.get('id', 'N/A')}</code></td></tr>
                                    <tr><td><strong>Name:</strong></td><td>{current_node.get('name', 'N/A')}</td></tr>
                                    <tr><td><strong>Type:</strong></td><td><span class="badge bg-primary">{current_node.get('node_type', 'N/A')}</span></td></tr>
                                    <tr><td><strong>Data Type:</strong></td><td>{current_node.get('data_type', 'N/A')}</td></tr>
                                </table>
                            </div>
                            <div class="col-md-4">
                                <h6>Dependencies ({len(dependencies)})</h6>
                                {dep_html}
                            </div>
                            <div class="col-md-4">
                                <h6>Dependents ({len(dependents)})</h6>
                                {dependent_html}
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Documentation</h6>
                                <div class="bg-light p-2 rounded">
                                    {current_node.get('doc', 'No documentation available') or 'No documentation available'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
            
        except Exception as e:
            html = f"""
            <div class="alert alert-danger">
                <h5>Error loading node details</h5>
                <p>{str(e)}</p>
            </div>
            """
        
        return html

