import logging

from dml_ui.plugins import DagDashboardPlugin, NodeDashboardPlugin

logger = logging.getLogger(__name__)

# DAG Dashboard Plugins
class ExampleDagPlugin(DagDashboardPlugin):
    """Educational DAG dashboard demonstrating DAG operations, backend methods, and data visualization."""
    NAME = "DAG Operations Tutorial"

    def render(self):
        dag_id = self.dag._ref.to if hasattr(self.dag, '_ref') else 'Unknown'
        
        # 1. DAG Operations Demo
        node_names = list(self.dag.keys())
        node_count = len(node_names)
        
        # Get node values and analyze them
        node_data = []
        numeric_values = []
        
        for node_name in node_names[:10]:  # Limit to first 10 nodes for display
            try:
                node = self.dag[node_name]
                value = node.value()
                node_data.append({
                    'name': node_name,
                    'value': str(value)[:100] + ('...' if len(str(value)) > 100 else ''),
                    'type': type(value).__name__,
                    'raw_value': value
                })
                
                # Check if value is numeric for charting
                if isinstance(value, (int, float)):
                    numeric_values.append({'name': node_name, 'value': float(value)})
                elif hasattr(value, '__len__') and not isinstance(value, str):
                    try:
                        # Try to get length for collections
                        numeric_values.append({'name': f"{node_name} (length)", 'value': len(value)})
                    except Exception:
                        pass
            except Exception as e:
                node_data.append({
                    'name': node_name,
                    'value': f"Error: {str(e)}",
                    'type': 'Error',
                    'raw_value': None
                })
        
        # Create node list HTML
        node_list_html = ""
        for node in node_data:
            badge_color = 'success' if node['type'] != 'Error' else 'danger'
            node_list_html += f"""
            <tr>
                <td><code>{node['name']}</code></td>
                <td><span class="badge bg-{badge_color}">{node['type']}</span></td>
                <td><small>{node['value']}</small></td>
            </tr>
            """
        
        # Create chart for numeric values
        chart_html = ""
        if numeric_values:
            max_val = max(v['value'] for v in numeric_values) if numeric_values else 1
            chart_html = """
            <h6><i class="fas fa-chart-bar"></i> Numeric Values Visualization</h6>
            <div class="mb-3">
            """
            for item in numeric_values[:8]:  # Limit to 8 bars for readability
                percentage = (item['value'] / max_val * 100) if max_val > 0 else 0
                chart_html += f"""
                <div class="d-flex align-items-center mb-2">
                    <div style="width: 120px; font-size: 0.8em;" class="text-truncate">
                        <code>{item['name']}</code>
                    </div>
                    <div class="flex-grow-1 mx-2">
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar bg-info" role="progressbar" 
                                 style="width: {percentage}%" 
                                 title="{item['value']}">
                            </div>
                        </div>
                    </div>
                    <div style="width: 80px; font-size: 0.8em;" class="text-end">
                        <strong>{item['value']}</strong>
                    </div>
                </div>
                """
            chart_html += "</div>"
        else:
            chart_html = """
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i> No numeric values found in the first 10 nodes for visualization.
            </div>
            """

        html = f"""
        <div class="container-fluid">
            <!-- Header -->
            <div class="row mb-3">
                <div class="col-12">
                    <div class="alert alert-primary">
                        <h5><i class="fas fa-graduation-cap"></i> DAG Operations Tutorial</h5>
                        <p>This plugin demonstrates key DAG operations and backend methods in DaggerML. 
                           Study the code examples below to learn how to interact with DAGs programmatically.</p>
                        <strong>Current DAG:</strong> <code>{dag_id}</code> | 
                        <strong>Total Nodes:</strong> {node_count}
                    </div>
                </div>
            </div>
            
            <!-- Section 1: DAG Operations -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h5><i class="fas fa-code"></i> 1. DAG Operations</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Code Examples:</h6>
                                    <pre class="bg-light p-3 rounded"><code># Get all node names in the DAG
node_names = list(self.dag.keys())
print(f"Found {{len(node_names)}} nodes")

# Access a specific node
node = self.dag[node_name]

# Get the node's computed value
value = node.value()

# Analyze the value type
value_type = type(value).__name__</code></pre>
                                </div>
                                <div class="col-md-6">
                                    <h6>Results:</h6>
                                    <div class="bg-success bg-opacity-10 p-3 rounded">
                                        <strong>Node Names:</strong><br>
                                        <code>{', '.join(node_names[:5])}{', ...' if len(node_names) > 5 else ''}</code>
                                        <br><br>
                                        <strong>Total Nodes:</strong> {node_count}
                                    </div>
                                </div>
                            </div>
                            
                            <h6 class="mt-4">Node Details Table:</h6>
                            <div class="table-responsive">
                                <table class="table table-sm table-striped">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>Node Name</th>
                                            <th>Value Type</th>
                                            <th>Value Preview</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {node_list_html}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Section 2: Data Visualization -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-warning text-dark">
                            <h5><i class="fas fa-chart-line"></i> 2. Data Visualization</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Code Example:</h6>
                                    <pre class="bg-light p-3 rounded"><code># Extract numeric values for visualization
numeric_values = []
for node_name in node_names:
    node = self.dag[node_name]
    value = node.value()
    
    if isinstance(value, (int, float)):
        numeric_values.append({{
            'name': node_name, 
            'value': float(value)
        }})
    elif hasattr(value, '__len__'):
        # Use length for collections
        numeric_values.append({{
            'name': f"{{node_name}} (length)", 
            'value': len(value)
        }})</code></pre>
                                </div>
                                <div class="col-md-6">
                                    {chart_html}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Section 3: Backend Operations -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-success text-white">
                            <h5><i class="fas fa-server"></i> 3. Backend Operations</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>Code Example:</h6>
                                    <pre class="bg-light p-3 rounded"><code># Backend method with HTMX integration
def analyze_dag_stats(self):
    node_count = len(self.dag.keys())
    total_size = 0
    
    for node_name in self.dag.keys():
        try:
            value = self.dag[node_name].value()
            if hasattr(value, '__sizeof__'):
                total_size += value.__sizeof__()
        except Exception:
            pass
    
    return analysis_html</code></pre>
                                </div>
                                <div class="col-md-6">
                                    <h6>Interactive Demo:</h6>
                                    <div class="d-grid gap-2">
                                        <button class="btn btn-outline-success btn-sm" 
                                                hx-get="{self.method_call_url('analyze_dag_stats')}"
                                                hx-target="#dagStatsResult"
                                                hx-swap="innerHTML">
                                            <i class="fas fa-calculator"></i> Analyze DAG Statistics
                                        </button>
                                    </div>
                                    
                                    <div id="dagStatsResult" class="mt-3">
                                        <!-- DAG stats will appear here -->
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Include HTMX for interactive features -->
        <script src="https://unpkg.com/htmx.org@1.8.4"></script>
        """
        return html

    def analyze_dag_stats(self):
        """Analyze DAG statistics including node types, values, and memory usage."""
        try:
            node_names = list(self.dag.keys())
            node_count = len(node_names)
            
            # Analyze node values
            value_types = {}
            total_memory = 0
            numeric_count = 0
            string_count = 0
            collection_count = 0
            
            for node_name in node_names:
                try:
                    node = self.dag[node_name]
                    value = node.value()
                    value_type = type(value).__name__
                    
                    # Count by type
                    value_types[value_type] = value_types.get(value_type, 0) + 1
                    
                    # Memory estimation
                    if hasattr(value, '__sizeof__'):
                        total_memory += value.__sizeof__()
                    
                    # Category analysis
                    if isinstance(value, (int, float)):
                        numeric_count += 1
                    elif isinstance(value, str):
                        string_count += 1
                    elif hasattr(value, '__len__'):
                        collection_count += 1
                        
                except Exception:
                    value_types['Error'] = value_types.get('Error', 0) + 1
            
            # Create type distribution chart
            type_chart_html = ""
            if value_types:
                max_count = max(value_types.values())
                for vtype, count in sorted(value_types.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / max_count * 100) if max_count > 0 else 0
                    type_chart_html += f"""
                    <div class="d-flex align-items-center mb-2">
                        <div style="width: 100px; font-size: 0.85em;">
                            <code>{vtype}</code>
                        </div>
                        <div class="flex-grow-1 mx-2">
                            <div class="progress" style="height: 18px;">
                                <div class="progress-bar bg-primary" role="progressbar" 
                                     style="width: {percentage}%" title="{count} nodes">
                                </div>
                            </div>
                        </div>
                        <div style="width: 40px; font-size: 0.85em;" class="text-end">
                            <strong>{count}</strong>
                        </div>
                    </div>
                    """
            
            return f"""
            <div class="alert alert-info">
                <h6><i class="fas fa-chart-pie"></i> DAG Analysis Results</h6>
                <div class="row">
                    <div class="col-md-6">
                        <h6>Summary Statistics:</h6>
                        <ul class="mb-0">
                            <li><strong>Total Nodes:</strong> {node_count}</li>
                            <li><strong>Numeric Values:</strong> {numeric_count}</li>
                            <li><strong>String Values:</strong> {string_count}</li>
                            <li><strong>Collections:</strong> {collection_count}</li>
                            <li><strong>Est. Memory:</strong> {total_memory:,} bytes</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h6>Value Type Distribution:</h6>
                        {type_chart_html}
                    </div>
                </div>
            </div>
            """
        except Exception as e:
            return f"""<div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-triangle"></i> Analysis Error</h6>
                <p>Failed to analyze DAG: {str(e)}</p>
            </div>"""

# Node Dashboard Plugins
class ExampleNodePlugin(NodeDashboardPlugin):
    """An example node dashboard showing node-level information."""
    NAME = "Example Node Dashboard"

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
                            <h5><i class="fas fa-plus-circle"></i> Node Dashboard Example</h5>
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
                                            <i class="fas fa-play-circle"></i> Execute Node
                                        </button>
                                        <button class="btn btn-outline-info btn-sm" onclick="alert('Node inspected!')">
                                            <i class="fas fa-search"></i> Inspect Node
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