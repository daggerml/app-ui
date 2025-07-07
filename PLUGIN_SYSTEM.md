# DML UI Plugin System

This document describes the new plugin system for DML UI that supports separate DAG and Node dashboards.

## Plugin Types

### Dashboard Plugin Base Class

```python
class DashboardPlugin:
    def __init__(self, dml: Dml):
        self.dml = dml

    def render(self):
        pass

    def url_for(self, obj: Dag | Node):
        """returns the url for the provided dag or node object

        Users can call this from within their `render` to get the URLs for other
        dags and nodes in their dashboards.
        """
```

### DAG Dashboard Plugins

#### The base class

```python
class DagDashboardPlugin:
    def __init__(self, dml: Dml, dag: Dag):
        super().__init__(dml)
        self.dag = dag
```

DAG plugins are displayed on the DAG view page and are instantiated with:
- `dml`: The DML instance
- `dag`: The loaded DAG object from `dml.load(dag_id)`

**Entry Point:** `dml_ui.dashboard.dag`

**Base Class:** `DagDashboardPlugin`

**Example:**
```python
from dml_ui.plugins import DagDashboardPlugin

class MyDagPlugin(DagDashboardPlugin):
    NAME = "My DAG Plugin"
    DESCRIPTION = "Shows custom DAG information"
    
    def render(self):
        dag_id = self.dag._ref.to
        url_for_node0 = self.url_for(next(iter(self.dag.nodes)))
        return f"<h3>DAG {dag_id} has {len(self.dag.nodes)} nodes</h3> <href target={url_for_node0}</href>"
```

### Node Dashboard Plugins

#### The base class

```python
class NodeDashboardPlugin:
    def __init__(self, dml: Dml, node: Node, dag_id: str = None):
        super().__init__(dml)
        self.node = node
        self._current_dag_id = dag_id
```

Node plugins are displayed on the Node view page and are instantiated with:
- `dml`: The DML instance  
- `node`: The node object from the DAG

**Entry Point:** `dml_ui.dashboard.node`

**Base Class:** `NodeDashboardPlugin`

**Example:**
```python
from dml_ui.plugins import NodeDashboardPlugin

class MyNodePlugin(NodeDashboardPlugin):
    NAME = "My Node Plugin"
    DESCRIPTION = "Shows custom node information"
    
    def render(self):
        node_id = self.node.ref.to if hasattr(self.node, 'ref') else 'Unknown'
        value = str(self.node.value())[:100]
        return f"<h3>Node {node_id}</h3><p>Value: {value}</p>"
```

## API Endpoints

### DAG Plugin Endpoints

- `GET /api/dag/plugins` - List all DAG plugins
- `GET /api/dag/plugins/<plugin_id>?dag_id=<id>&repo=<repo>&branch=<branch>` - Render DAG plugin

### Node Plugin Endpoints

- `GET /api/node/plugins` - List all Node plugins  
- `GET /api/node/plugins/<plugin_id>?dag_id=<id>&node_id=<id>&repo=<repo>&branch=<branch>` - Render Node plugin

## Built-in Plugins

### DAG Plugins
- **Example DAG Dashboard**: Basic DAG information and actions
- **DAG Statistics**: Detailed statistics about DAG structure

### Node Plugins  
- **Example Node Dashboard**: Basic node information and actions
- **Node Details**: Detailed node information including dependencies

## Entry Point Configuration

Add to your `pyproject.toml`:

```toml
[project.entry-points."dml_ui.dashboard.dag"]
my_dag_plugin = "my_package.plugins:MyDagPlugin"

[project.entry-points."dml_ui.dashboard.node"]  
my_node_plugin = "my_package.plugins:MyNodePlugin"
```
