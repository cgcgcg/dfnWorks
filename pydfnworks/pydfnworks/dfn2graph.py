import networkx as nx
import numpy as np
import json

from networkx.algorithms.flow.shortestaugmentingpath import *
from networkx.algorithms.flow.edmondskarp import *
from networkx.algorithms.flow.preflowpush import *
from networkx.readwrite import json_graph
import matplotlib.pylab as plt
from itertools import islice

def create_graph(self, graph_type, inflow, outflow):
    """Header function to create a graph based on a DFN

    Parameters
    ----------
        self : object
            DFN Class object 
        graph_type : string
            Option for what graph representation of the DFN is requested. Currently supported are fracture, intersection, and bipartitie 
        inflow : string
            Name of inflow boundary (connect to source)
        outflow : string
            Name of outflow boundary (connect to target)

    Returns
    -------
        G : NetworkX Graph
            Graph based on DFN 

    Notes
    -----

"""


    if graph_type == "fracture":
        G = create_fracture_graph(inflow, outflow)
    elif graph_type == "intersection":
        G = create_intersection_graph(inflow, outflow)
    elif graph_type == "bipartite":
        G = create_bipartite_graph(inflow, outflow)
    else:
        print("ERROR! Unknown graph type")
        return [] 
    return G

def create_fracture_graph(inflow, outflow, topology_file = "connectivity.dat"):
    """ Create a graph based on topology of network. Fractures
    are represented as nodes and if two fractures intersect 
    there is an edge between them in the graph. 
    
    Source and Target node are added to the graph. 
    
    Parameters
    ----------
        inflow : string
            Name of inflow boundary (connect to source)
        outflow : string
            Name of outflow boundary (connect to target)
        topology_file : string
            Name of adjacency matrix file for a DFN default=connectivity.dat  

    Returns
    -------
        G : NetworkX Graph
            NetworkX Graph where vertices in the graph correspond to fractures and edges indicated two fractures intersect  

    Notes
    -----
    """ 
    print("--> Loading Graph based on topology in "+topology_file)
    G = nx.Graph(representation="fracture")
    with open(topology_file, "r") as infile:
        for i,line in enumerate(infile):
            conn = [int(n) for n in line.split()]
            for j in conn:
                G.add_edge(i,j-1) 
    ## Create Source and Target and add edges
    inflow_filename = inflow + ".dat"
    outflow_filename = outflow + ".dat"
    inflow = np.genfromtxt(inflow_filename) - 1
    outflow = np.genfromtxt(outflow_filename) - 1
    try:
        inflow = list(inflow)
    except:
        inflow = [inflow]
    try:
        outflow = list(outflow) 
    except:
        outflow = [outflow]
    G.add_node('s')
    G.add_node('t')
    G.add_edges_from(zip(['s']*(len(inflow)),inflow))
    G.add_edges_from(zip(outflow,['t']*(len(outflow))))   
    add_perm(G) 
    print("--> Graph loaded")
    return G

def boundary_index(bc_name):
    """Determines boundary index in intersections_list.dat from name

    Parameters
    ----------
        bc_name : string
            Boundary condition name

    Returns
    -------
        bc_index : int
            integer indexing of cube faces

    Notes
    -----
    top = 1
    bottom = 2
    left = 3
    front = 4
    right = 5
    back = 6
    """
    bc_dict ={"top":-1,"bottom":-2,"left":-3,"front":-4,"right":-5,"back":-6}
    try:
        return bc_dict[bc_name]
    except:
        sys.exit("Unknown boundary condition: %s\nExiting"%bc)

def create_intersection_graph(inflow, outflow, intersection_file="intersection_list.dat"):
    """ Create a graph based on topology of network.
    Edges are represented as nodes and if two intersections
    are on the same fracture, there is an edge between them in the graph. 
    
    Source and Target node are added to the graph. 
   
    Parameters
    ----------
        inflow : string
            Name of inflow boundary
        outflow : string
            Name of outflow boundary
        intersection_file : string
             File containing intersection information
             File Format:
             fracture 1, fracture 2, x center, y center, z center, intersection length

    Returns
    -------
        G : NetworkX Graph
            Vertices have attributes x,y,z location and length. Edges has attribute length

    Notes
    -----
    Aperture and Perm on edges can be added using add_app and add_perm functions
    """ 

    print("Creating Graph Based on DFN")
    print("Intersections being mapped to nodes and Fractures to Edges")
    inflow_index=boundary_index(inflow)
    outflow_index=boundary_index(outflow)

    f=open(intersection_file)
    f.readline()
    frac_edges = []
    for line in f:
        frac_edges.append(line.rstrip().split())
    f.close()

    # Tag mapping
    G = nx.Graph(representation="intersection")
    remove_list=[]

    # each edge in the DFN is a node in the graph
    for i in range(len(frac_edges)):
        f1 = int(frac_edges[i][0]) - 1
        keep=True
        if frac_edges[i][1] is 's' or frac_edges[i][1] is 't':
            f2 = frac_edges[i][1]
        elif int(frac_edges[i][1]) > 0:
            f2 = int(frac_edges[i][1]) - 1  
        elif int(frac_edges[i][1]) == inflow_index:
            f2 = 's'
        elif int(frac_edges[i][1]) == outflow_index:
            f2 = 't'
        elif int(frac_edges[i][1]) < 0:
            keep=False

        if keep: 
            # note fractures of the intersection 
            G.add_node(i,frac=(f1,f2))
            # keep intersection location and length
            G.node[i]['x'] = float(frac_edges[i][2])
            G.node[i]['y'] = float(frac_edges[i][3])
            G.node[i]['z'] = float(frac_edges[i][4])
            G.node[i]['length'] = float(frac_edges[i][5])
    
    nodes = list(nx.nodes(G))    
    f1 = nx.get_node_attributes(G,'frac') 
    # identify which edges are on whcih fractures
    for i in nodes:
        e = set(f1[i])
        for j in nodes:
            if i != j:
                tmp = set(f1[j])
                x = e.intersection(tmp)
                if len(x) > 0:
                    x = list(x)[0]
                    # Check for Boundary Intersections
                    # This stops boundary fractures from being incorrectly
                    # connected 
                    # If not, add edge between
                    if x != 's' and x != 't':
                        xi = G.node[i]['x']
                        yi = G.node[i]['y']
                        zi = G.node[i]['z']

                        xj = G.node[j]['x']
                        yj = G.node[j]['y']
                        zj = G.node[j]['z']
            
                        distance = np.sqrt((xi-xj)**2 + (yi-yj)**2 + (zi-zj)**2)
                        G.add_edge(i,j,frac = x, length = distance)

    # Add Sink and Source nodes
    G.add_node('s')
    G.add_node('t')

    for i in nodes:
        e = set(f1[i])
        if len(e.intersection(set('s'))) > 0 or len(e.intersection(set([-1]))) > 0:
            G.add_edge(i,'s',frac='s', length=0.0)
        if len(e.intersection(set('t'))) > 0 or len(e.intersection(set([-2]))) > 0:
            G.add_edge(i,'t',frac='t', length=0.0)     
    add_perm(G) 
    print("Graph Construction Complete")
    return G

def create_bipartite_graph(inflow, outflow, intersection_list='intersection_list.dat',
                           fracture_info='fracture_info.dat'):
    """Creates a bipartite graph of the DFN.
    Nodes are in two sets, fractures and intersections, with edges connecting them.


    Parameters
    ----------
        inflow : str
            name of inflow boundary
        outflow : str
            name of outflow boundary
        intersection_list: str
             filename of intersections generated from DFN
        fracture_infor : str
                filename for fracture information

    Returns
    -------
        B : NetworkX Graph

    Notes
    -----
    See Hyman et al. 2018 "Identifying Backbones in Three-Dimensional Discrete Fracture Networks: A Bipartite Graph-Based Approach" SIAM Multiscale Modeling and Simulation for more details 
"""

    print("--> Creating Bipartite Graph")

    # generate sequential letter sequence as ids for fractures
    # e..g aaaaa aaaaab aaaaac
    from itertools import product
    def intersection_id_generator(length=5):
        chars='abcdefghijklmnopqrstuvwxyz'
        for p in  product(chars, repeat=length):
            yield(''.join(p))

    B = nx.Graph(representation="bipartite")
    # keep track of the sets of fractures and intersections
    B.fractures = set()
    B.intersections = set()
    intersection_id= intersection_id_generator()

    inflow_index=boundary_index(inflow)
    outflow_index=boundary_index(outflow)


    with open(intersection_list) as f:
        header = f.readline()
        data = f.read().strip()
        for line in data.split('\n'):
            fracture1,fracture2,x,y,z,length = line.split(' ')
            fracture1 = int(fracture1)
            fracture2 = int(fracture2)
            if fracture2 < 0:
                if fracture2 == inflow_index:
                    fracture2 = 's'
                elif fracture2 == outflow_index:
                    fracture2 = 't'
            intersection = next(intersection_id)
            # add intersection node explicitly to include intersection properties
            B.add_node(intersection, x=float(x), y=float(y), z=float(z), length=float(length))
            B.intersections.add(intersection)
            
            B.add_edge(intersection, fracture1,frac=fracture1)
            B.fractures.add(fracture1)
            if fracture2 > 0 or fracture2 == 's' or fracture2 == 't':
                B.add_edge(intersection, fracture2,frac=fracture2)
                B.fractures.add(fracture2)

    # add  source and sink for intersections so they will appear in intersection projection
    B.add_edge('intersection_s','s')
    B.add_edge('intersection_t','t')

    # add fracture info
    with open(fracture_info) as f:
        header = f.readline()
        data = f.read().strip()
        for fracture,line in enumerate(data.split('\n'),1):
            c,perm,aperture = line.split(' ')
            B.node[fracture]['perm']=float(perm)
            B.node[fracture]['aperture']=float(aperture)

    print("--> Complete")

    return B


def k_shortest_paths(G, k, source, target, weight):
    """Returns the k shortest paths in a graph 
    
    Parameters
    ----------
        G : NetworkX Graph
            NetworkX Graph based on a DFN 
        k : int
            Number of requested paths
        source : node 
            Starting node
        target : node
            Ending node
        weight : string
            Edge weight used for finding the shortest path

    Returns 
    -------
        paths : sets of nodes
            a list of lists of nodes in the k shortest paths

    Notes
    -----
    Edge weights must be numerical and non-negative
"""
    return list(islice(nx.shortest_simple_paths(G, source, target, weight=weight), k))

def k_shortest_paths_backbone(self, G, k, source='s', target='t', weight=None):
    """Returns the subgraph made up of the k shortest paths in a graph 
   
    Parameters
    ----------
        G : NetworkX Graph
            NetworkX Graph based on a DFN 
        k : int
            Number of requested paths
        source : node 
            Starting node
        target : node
            Ending node
        weight : string
            Edge weight used for finding the shortest path

    Returns 
    -------
        H : NetworkX Graph
            Subgraph of G made up of the k shortest paths 

    Notes
    -----
        See Hyman et al. 2017 "Predictions of first passage times in sparse discrete fracture networks using graph-based reductions" Physical Review E for more details
"""

    print("\n--> Determining %d shortest paths in the network"%k)
    H = G.copy()
    k_shortest= set([])
    for path in k_shortest_paths(G, k, source, target, weight):
        k_shortest |= set(path)
    path_nodes = sorted(list(k_shortest))
    nodes = list(G.nodes())
    secondary = list(set(nodes) - set(path_nodes)) 
    for n in secondary:
        H.remove_node(n)
    return H
    print("--> Complete\n")

def pull_source_and_target(nodes,source='s',target='t'):
    """Removes source and target from list of nodes, useful for dumping subnetworks to file for remeshing

    Parameters
    ----------
        nodes :list 
            List of nodes in the graph
        source : node 
            Starting node
        target : node
            Ending node
    Returns
    -------
        nodes : list
            List of nodes with source and target nodes removed

    Notes
    -----

"""
    for node in [source, target]:
        try:
           nodes.remove(node)
        except:
            pass 
    return nodes 

def dump_fractures(self, G, filename):
    """Write fracture numbers assocaited with the graph G out into an ASCII file inputs

    Parameters
    ----------
        self : object
            DFN Class
        G : NetworkX graph
            NetworkX Graph based on the DFN
        filename : string
            Output filename 

    Returns
    -------

    Notes
    ----- 
    """
     
    if G.graph['representation'] == "fracture":
        nodes = list(G.nodes())
    elif G.graph['representation'] == "intersection":
        nodes = []
        for u,v,d in G.edges(data=True):
            nodes.append(G[u][v]['frac'])
        nodes = list(set(nodes))
    elif G.graph['representation'] == "bipartite":
        nodes = []
        for u,v,d in G.edges(data=True):
            nodes.append(G[u][v]['frac'])
        nodes = list(set(nodes))

    nodes = pull_source_and_target(nodes) 
    fractures = [int(i) + 1 for i in nodes] 
    fractures = sorted(fractures)
    print("--> Dumping %s"%filename)
    np.savetxt(filename, fractures, fmt = "%d")

def greedy_edge_disjoint(self, G, source='s', target='t', weight='None',k=''):
    """
    Greedy Algorithm to find edge disjoint subgraph from s to t. 
    See Hyman et al. 2018 SIAM MMS

    Parameters
    ----------
        self : object 
            DFN Class Object
        G : NetworkX graph
            NetworkX Graph based on the DFN
        source : node 
            Starting node
        target : node
            Ending node
        weight : string
            Edge weight used for finding the shortest path
        k : int
            Number of edge disjoint paths requested
    
    Returns
    -------
        H : NetworkX Graph
            Subgraph of G made up of the k shortest of all edge-disjoint paths from source to target

    Notes
    -----
        1. Edge weights must be numerical and non-negative.
        2. See Hyman et al. 2018 "Identifying Backbones in Three-Dimensional Discrete Fracture Networks: A Bipartite Graph-Based Approach" SIAM Multiscale Modeling and Simulation for more details 

    """
    print("--> Identifying edge disjoint paths")
    if G.graph['representation'] != "intersection":
        print("--> ERROR!!! Wrong type of DFN graph representation\nRepresentation must be intersection\nReturning Empty Graph\n")
        return nx.Graph()
    Gprime = G.copy()
    Hprime = nx.Graph()
    Hprime.graph['representation'] = G.graph['representation']
    cnt = 0
    # if a number of paths in not provided k will equal the min cut between s and t
    if k != '':
        k = len(nx.minimum_edge_cut(G,'s','t'))
    while nx.has_path(Gprime, source, target):
        path = nx.shortest_path(Gprime, source, target, weight=weight)
        H = Gprime.subgraph(path)
        Hprime.add_edges_from(H.edges(data=True))
        for u,v,d in H.edges(data = True):
            Gprime.remove_edge(u,v)
        cnt += 1
        if cnt > k:
            break
    print("--> Complete")
    return Hprime

def plot_graph(self,G, source='s', target='t',output_name="dfn_graph"):
    """ Create a png of a graph with source nodes colored blue, target red, and all over nodes black
    
    Parameters
    ---------- 
        G : NetworkX graph
            NetworkX Graph based on the DFN
        source : node 
            Starting node
        target : node
            Ending node
        output_name : string
            Name of output file (no .png)

    Returns
    -------

    Notes
    -----
    Image is written to output_name.png

    """ 
    print("\n--> Plotting Graph")
    print("--> Output file: %s.png"%output_name)
    # get positions for all nodes
    pos=nx.spring_layout(G)
    nodes=list(G.nodes)
    # draw nodes
    nx.draw_networkx_nodes(G,pos,
                           nodelist=nodes,
                           node_color='k',
                           node_size=10,
                       alpha=1.0)
    nx.draw_networkx_nodes(G,pos,
                           nodelist=[source],
                           node_color='b',
                           node_size=50,
                       alpha=1.0)
    nx.draw_networkx_nodes(G,pos,
                           nodelist=[target],
                           node_color='r',
                           node_size=50,
                       alpha=1.0)
    
    nx.draw_networkx_edges(G,pos,width=1.0,alpha=0.5)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_name+".png")
    plt.clf()
    print("--> Plotting Graph Complete\n") 

def dump_json_graph(self, G, name):
    """Write graph out in json format
 
    Parameters
    ---------- 
        self : object 
            DFN Class
        G :networkX graph
            NetworkX Graph based on the DFN
        name : string
             Name of output file (no .json)

    Returns
    -------

    Notes
    -----

"""
    print("--> Dumping Graph into file: "+name+".json")
    jsondata = json_graph.node_link_data(G)
    with open(name+'.json', 'w') as fp:
        json.dump(jsondata, fp)
    print("--> Complete")

def load_json_graph(self,name):
    """Read in graph from json format

    Parameters
    ---------- 
        self : object 
            DFN Class
        name : string
             Name of input file (no .json)

    Returns
    -------
        G :networkX graph
            NetworkX Graph based on the DFN

   Notes
   -----

"""
    print("Loading Graph in file: "+name+".json")
    fp = open(name+'.json')
    G = json_graph.node_link_graph(json.load(fp))
    print("Complete")
    return G

def add_perm(G):
    """ Add fracture permeability to Graph. If Graph representation is
    fracture, then permeability is a node attribute. If graph representation 
    is intersection, then permeability is an edge attribute


    Parameters
    ---------- 
        G :networkX graph
            NetworkX Graph based on the DFN
   
    Returns
    -------
 
    Notes
    -----

"""

    perm = np.genfromtxt('fracture_info.dat', skip_header =1)[:,1]
    if G.graph['representation'] == "fracture":
        nodes = list(nx.nodes(G))
        for n in nodes:
            if n != 's' and n != 't':
                G.node[n]['perm'] = perm[n]
                G.node[n]['iperm'] = 1.0/perm[n]
            else:
                G.node[n]['perm'] = 1.0
                G.node[n]['iperm'] = 1.0

    elif G.graph['representation'] == "intersection":
        edges = list(nx.edges(G))
        for u,v in edges:
            x = G[u][v]['frac']
            if x != 's' and x != 't':
                G[u][v]['perm'] = perm[x]
                G[u][v]['iperm'] = 1.0/perm[x]
            else:   
                G[u][v]['perm'] = 1.0
                G[u][v]['iperm'] = 1.0
    elif G.graph['representation'] == "bipartite":
        # add fracture info
        with open('fracture_info.dat') as f:
            header = f.readline()
            data = f.read().strip()
            for fracture,line in enumerate(data.split('\n'),1):
                c,perm,aperture = line.split(' ')
                G.node[fracture]['perm']=float(perm)
                G.node[fracture]['iperm']=1.0/float(perm)
                G.node[fracture]['aperture']=float(aperture)

