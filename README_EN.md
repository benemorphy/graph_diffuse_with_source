# Graph Node Correlation and Central Node Calculation Algorithm with Source Identification

## Algorithm Overview

This document introduces a graph propagation-based node correlation analysis algorithm that calculates correlations between nodes in a graph and identifies central nodes through an information propagation mechanism with source identification. The core implementation of the algorithm is in the `Gds` (Graph Diffusion with Source) class, using the igraph library for graph data structure processing.

## Core Classes and Data Structures

### Gds Class

The `Gds` class is the core implementation of the algorithm, containing functions for graph initialization, information propagation, normalization, and central node calculation.
After initialization, the graph G is passed in from outside, and the nodes of the graph have an attribute r_msg that stores the node's correlation messages.

```python
class Gds():
    def __init__(self, G):
        # Graph initialization code
```

### Data Structures
- `r_msg`: Stores node correlation messages, a dictionary in JSON format with source node IDs as keys and correlation degrees as values
- `buffer`: Stores message buffers propagated from neighbor nodes, designed to implement parallel transmission
- `id_nodeid_dict`: Mapping from vertex ID to node ID
- `nodeid_id_dict`: Mapping from node ID to vertex ID

## Propagation Algorithm Principles

### 1. Initialization

```python
def __init__(self, G):
    self.G = G
    self.df_vertexs = self.G.get_vertex_dataframe()
    # Create ID mappings
    self.id_nodeid_dict = self.df_vertexs.set_index('vertex ID')['node_id'].to_dict()
    self.nodeid_id_dict = {v: k for k, v in self.id_nodeid_dict.items()}
    # Initialize node attributes
    self.G.vs["r_msg"] = json.dumps({})
    self.G.vs["buffer"] = json.dumps([])
    # Set propagation parameters
    self.FADE = 0.3  # Message attenuation coefficient
    # Set other parameters based on number of nodes
```

### 2. Adding Source Nodes

```python
def add_one_node_ids(self, node_ids):
    for node_id in node_ids:
        vid = self.nodeid_id_dict[node_id]
        node = self.G.vs[vid]
        origin_msg = json.loads(self.G.vs[int(vid)]["r_msg"])
        # Add source node message
        add_msg = {str(node_id): 1}
        origin_msg.update(add_msg)
        # Merge messages and update
        buffer = []
        buffer.append(add_msg)
        buffer.append(origin_msg)
        merged_dict = merge_dicts_with_sum(buffer)
        node['r_msg'] = json.dumps(merged_dict)
    self.normalize()
```

### 3. Message Propagation Mechanism

#### Propagation from Specified Nodes
Specify a series of nodes (node_ids), and set each node's 'r_msg' attribute to {node_id: 1}
    - node_id: Node identifier
    - 1: Weight from the source node
```python
def add_one_node_ids(self, node_ids):

```

#### Global Propagation to Buffer

Each node's message propagates to its neighbor nodes' buffers
```python
def merge_from_buffer(self):

```
Thus, each node's buffer stores messages from all neighbor nodes, forming a message list.

### 4. Message Merging and Normalization
<!-- Merge messages from buffer -->

```python
def merge_from_buffer(self):

```

### Normalization Function

```python
def normalize(self):

```

### Central Node Calculation Algorithm

```python
def show_central(self):

    return filtered_dict
```

### Visualization Function

```python
def show_nodes(self, node_data):

```

## Algorithm Parameters

- `FADE`: Message propagation attenuation coefficient, default value is 0.3
- `LIMIT`: Correlation filtering threshold, default value is `3*(1/number of nodes)`
- `MIN_SIZE`/`MAX_SIZE`/`DEFAULT_SIZE`: Node visualization size parameters

## Algorithm Flow

1. Initialize graph and parameters
2. Add source nodes and set initial messages
3. Perform message propagation (single or multiple iterations), propagating messages to buffers
4. Merge buffer messages
5. Normalize node messages
6. Calculate central nodes
7. Visualize results

## Usage Example
See tests\test.ipynb

## Algorithm Features

1. **Source Identification**: Messages retain the identification of source nodes, allowing tracking of information propagation paths
2. **Attenuation Mechanism**: Messages attenuate during propagation, avoiding excessive influence from distant nodes
3. **Dynamic Threshold**: Dynamically adjusts correlation filtering threshold based on the number of nodes
4. **Visualization**: Provides node importance visualization functionality
5. **Normalization**: Ensures the sum of node messages is 1, facilitating comparison

This algorithm is suitable for social network analysis, fraud detection, recommendation systems, and other scenarios, effectively identifying key nodes and community structures in graphs.