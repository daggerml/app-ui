import base64
import importlib.metadata
import io

class DashboardPlugin:
    NAME = None
    DESCRIPTION = None

    def render(self, dml, dag, **kwargs):
        """
        Return HTML (or Flask Response) to embed in the dashboard.
        
        Args:
            dml: The Dml instance for accessing the API
            dag: The DAG structure from dml("dag", "describe", dag_id)
                 Contains 'nodes' and 'edges' arrays with metadata
            **kwargs: Additional context including:
                - dag_id: The DAG identifier
                - repo: Repository name
                - branch: Branch name
                - dag_object: The loaded DAG object from dml.load(dag_id) for value access
        """
        raise NotImplementedError


def discover_plugins():
    """Discover all available dashboard plugins"""
    plugins = []
    seen_names = set()
    
    # First, add built-in plugins
    built_in_plugins = [DAGInfoPlugin, SimpleStatsPlugin, MatplotlibStatsPlugin, DMLExplorerPlugin]
    
    for plugin_cls in built_in_plugins:
        if plugin_cls.NAME and plugin_cls.NAME not in seen_names:
            plugins.append(plugin_cls)
            seen_names.add(plugin_cls.NAME)
    
    # Then discover plugins from entry points
    try:
        for entry_point in importlib.metadata.entry_points(group="dml_ui.dashboard_plugins"):
            plugin_cls = entry_point.load()
            if (issubclass(plugin_cls, DashboardPlugin) and 
                plugin_cls.NAME and 
                plugin_cls.NAME not in seen_names):
                plugins.append(plugin_cls)
                seen_names.add(plugin_cls.NAME)
    except Exception:
        # Entry points might not be available in development
        pass
    
    return plugins

# Built-in plugins
class DAGInfoPlugin(DashboardPlugin):
    NAME = "DAG Info"
    DESCRIPTION = "Shows basic information about the DAG"

    def render(self, dml, dag, **kwargs):
        # Extract nodes and edges from the raw dag object
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])
        
        node_types = {}
        for node in nodes:
            node_type = node.get("node_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        html = f"""
        <div class="container-fluid">
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>DAG Overview</h5>
                        </div>
                        <div class="card-body">
                            <p><strong>Total Nodes:</strong> {len(nodes)}</p>
                            <p><strong>Total Edges:</strong> {len(edges)}</p>
                            <p><strong>DAG ID:</strong> {kwargs.get('dag_id', 'N/A')}</p>
                            <p><strong>Repository:</strong> {kwargs.get('repo', 'N/A')}</p>
                            <p><strong>Branch:</strong> {kwargs.get('branch', 'N/A')}</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Node Types</h5>
                        </div>
                        <div class="card-body">
        """
        
        for node_type, count in node_types.items():
            html += f"<p><strong>{node_type}:</strong> {count}</p>"
        
        html += """
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html

class MatplotlibStatsPlugin(DashboardPlugin):
    NAME = "Stats Chart"
    DESCRIPTION = "Shows a matplotlib chart of DAG stats"

    def render(self, dml, dag, **kwargs):
        try:
            import matplotlib.pyplot as plt
            
            # Extract nodes and edges from the raw dag object
            nodes = dag.get("nodes", [])
            edges = dag.get("edges", [])
            
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(["Nodes", "Edges"], [len(nodes), len(edges)])
            ax.set_title("DAG Statistics")
            ax.set_ylabel("Count")
            
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches='tight')
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode("utf-8")
            plt.close(fig)
            
            return f"""
            <div class="text-center">
                <h4>DAG Statistics Chart</h4>
                <img src="data:image/png;base64,{img_b64}" 
                     alt="DAG Stats Chart" 
                     class="img-fluid" 
                     style="max-width: 100%; height: auto;">
            </div>
            """
        except ImportError:
            return """
            <div class="alert alert-warning">
                <h4>Matplotlib not available</h4>
                <p>Install matplotlib to view charts: <code>pip install matplotlib</code></p>
            </div>
            """

class SimpleStatsPlugin(DashboardPlugin):
    NAME = "Simple Stats"
    DESCRIPTION = "Shows basic DAG statistics without external dependencies"

    def render(self, dml, dag, **kwargs):
        # Extract nodes and edges from the raw dag object
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])
        
        node_types = {}
        for node in nodes:
            node_type = node.get("node_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # Create a simple bar chart using CSS
        max_count = max(node_types.values()) if node_types else 1
        
        html = f"""
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5>DAG Statistics</h5>
                        </div>
                        <div class="card-body">
                            <div class="row mb-4">
                                <div class="col-md-4">
                                    <div class="text-center">
                                        <h2 class="text-primary">{len(nodes)}</h2>
                                        <p class="text-muted">Total Nodes</p>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="text-center">
                                        <h2 class="text-success">{len(edges)}</h2>
                                        <p class="text-muted">Total Edges</p>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="text-center">
                                        <h2 class="text-info">{len(node_types)}</h2>
                                        <p class="text-muted">Node Types</p>
                                    </div>
                                </div>
                            </div>
                            
                            <h6>Node Type Distribution:</h6>
                            <div class="mt-3">
        """
        
        colors = ["#0d6efd", "#198754", "#ffc107", "#dc3545", "#6f42c1", "#fd7e14"]
        
        for i, (node_type, count) in enumerate(node_types.items()):
            percentage = (count / max_count) * 100
            color = colors[i % len(colors)]
            
            html += f"""
                <div class="mb-2">
                    <div class="d-flex justify-content-between">
                        <span><strong>{node_type}</strong></span>
                        <span>{count}</span>
                    </div>
                    <div class="progress" style="height: 20px;">
                        <div class="progress-bar" role="progressbar" 
                             style="width: {percentage}%; background-color: {color};"
                             aria-valuenow="{count}" aria-valuemin="0" aria-valuemax="{max_count}">
                        </div>
                    </div>
                </div>
            """
        
        html += """
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html

class DMLExplorerPlugin(DashboardPlugin):
    NAME = "DML Explorer"
    DESCRIPTION = "Interactive explorer with direct DML API access"

    def render(self, dml, dag, **kwargs):
        dag_id = kwargs.get('dag_id', 'Unknown')
        
        # Demonstrate direct DML API access
        try:
            # Get repository information
            repos = dml("repo", "list")
            repo_count = len(repos) if repos else 0
            
            # Get branch information if repo is available
            repo_name = kwargs.get('repo')
            branches = []
            if repo_name:
                try:
                    branches = dml("branch", "list", repo_name)
                except Exception:
                    branches = []
            
            # Get DAG list
            try:
                dags = dml("dag", "list")
                dag_count = len(dags) if dags else 0
            except Exception:
                dag_count = 0
            
            # Extract detailed node information
            nodes = dag.get("nodes", [])
            edges = dag.get("edges", [])
            
            # Find function nodes with additional details
            function_nodes = [node for node in nodes if node.get("node_type") == "fn"]
            
            html = f"""
            <div class="container-fluid">
                <div class="row mb-4">
                    <div class="col-12">
                        <div class="alert alert-info">
                            <h5><i class="bi bi-info-circle"></i> DML API Explorer</h5>
                            <p>This plugin demonstrates direct access to the DML API and raw DAG data.</p>
                        </div>
                    </div>
                </div>
                
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="text-primary">{repo_count}</h3>
                                <p class="text-muted">Repositories</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="text-success">{len(branches)}</h3>
                                <p class="text-muted">Branches</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="text-warning">{dag_count}</h3>
                                <p class="text-muted">Total DAGs</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h3 class="text-info">{len(function_nodes)}</h3>
                                <p class="text-muted">Functions</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>Current DAG: {dag_id}</h5>
                            </div>
                            <div class="card-body">
                                <p><strong>Nodes:</strong> {len(nodes)}</p>
                                <p><strong>Edges:</strong> {len(edges)}</p>
                                <p><strong>Repository:</strong> {kwargs.get('repo', 'N/A')}</p>
                                <p><strong>Branch:</strong> {kwargs.get('branch', 'N/A')}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>Function Nodes</h5>
                            </div>
                            <div class="card-body" style="max-height: 300px; overflow-y: auto;">
            """
            
            if function_nodes:
                for func_node in function_nodes[:10]:  # Show first 10
                    name = func_node.get('name', 'Unnamed')
                    node_id = func_node.get('id', 'Unknown')[:8]
                    doc = func_node.get('doc', 'No documentation')[:100]
                    html += f"""
                    <div class="mb-2 p-2 border-start border-primary border-3">
                        <strong>{name}</strong> <small class="text-muted">({node_id})</small><br>
                        <small>{doc}{'...' if len(func_node.get('doc', '')) > 100 else ''}</small>
                    </div>
                    """
                if len(function_nodes) > 10:
                    html += f"<p class='text-muted'>... and {len(function_nodes) - 10} more functions</p>"
            else:
                html += "<p class='text-muted'>No function nodes found in this DAG.</p>"
            
            html += """
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5>Raw DAG Structure (First 10 Nodes)</h5>
                            </div>
                            <div class="card-body">
                                <pre style="max-height: 400px; overflow-y: auto; background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
            """
            
            # Show first 10 nodes in a readable format
            import json
            sample_nodes = nodes[:10] if nodes else []
            html += json.dumps(sample_nodes, indent=2, default=str)
            
            html += """
                                </pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
            
        except Exception as e:
            html = f"""
            <div class="container-fluid">
                <div class="alert alert-danger">
                    <h4>Error accessing DML API</h4>
                    <p>Failed to fetch data from DML: {str(e)}</p>
                </div>
            </div>
            """
        
        return html