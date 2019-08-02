#!/usr/bin/env python

import os
import sys
import argparse
import louvain
import igraph


def _parse_arguments(desc, args):
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    help_fm = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=help_fm)
    parser.add_argument('input',
                        help='Edge file in tab delimited format')
    parser.add_argument('--directed', action='store_true',
                        help='If set, then generate directed graph')
    parser.add_argument('--configmodel', default='Default',
                        choices=['RB','RBER','CPM','Suprise','Significance','Default'],
                        help='Configuration model')
    return parser.parse_args(args)


def run_louvain(graph, config_model='RB',
                overlap=False, directed=False, interslice_weight=0.1,
                resolution_parameter=0.1):

    """
    :outdir: the output directory to comprehend the output link file
    :param graph: input file
    :param config_model: 'RB', 'RBER', 'CPM', 'Surprise', 'Significance'
    :param overlap: bool, whether to enable overlapping community detection
    :param directed
    :param interslice_weight
    :param resolution_parameter
    :return
    """

    def louvain_multiplex(graphs, partition_type, interslice_weight, resolution_parameter):
        layers, interslice_layer, G_full = louvain.time_slices_to_layers(graphs, vertex_id_attr='name', interslice_weight=interslice_weight)
        partitions = [partition_type(H, resolution_parameter) for H in layers]
        interslice_partition = partition_type(interslice_layer, resolution_parameter, weights='weight')
        optimiser = louvain.Optimiser()
        optimiser.optimise_partition_multiplex(partitions + [interslice_partition])
        quality = sum([p.quality() for p in partitions + [interslice_partition]])
        return partitions[0], quality

    multi = False
    if isinstance(graph, list):
        multi = True

    if overlap == True and multi == False:
        multi = True
        net = graph
        graph = []
        for i in range(4):
            graph.append(net)

    if config_model == 'RB':
        partition_type = louvain.RBConfigurationVertexPartition
    elif config_model == 'RBER':
        partition_type = louvain.RBERConfigurationVertexPartition
    elif config_model == 'CPM':
        partition_type = louvain.CPMVertexPartition
    elif config_model == 'Surprise':
        partition_type = louvain.SurpriseVertexPartition
    elif config_model == "Significance":
        partition_type = louvain.SignificanceVertexPartition
    else:
        sys.stderr.write("Not specifying the configuration model; perform simple Louvain.")
        partition_type = louvain.ModularityVertexPartition

    weighted = False
    if multi:
        wL = []
        G = []
        for file in graph:
            with open(file, 'r') as f:
                lines = f.read().splitlines()
            elts = lines[0].split()
            if len(elts) == 3:
                weighted = True
            else:
                weighted = False
            for i in range(len(lines)):
                elts = lines[i].split()
                for j in range(2):
                    elts[j] = int(elts[j])
                if weighted == True:
                    elts[2] = float(elts[2])
                lines[i] = tuple(elts)
            g = igraph.Graph.TupleList(lines, directed=directed, weights=weighted)
            G.append(g)
            wL.append(weighted)
            f.close()
        if True in wL and False in wL:
            raise Exception('all graphs should follow the same format')
        if partition_type == louvain.CPMVertexPartition and directed == True:
            raise Exception('graph for CPMVertexPartition must be undirected')
        if partition_type == louvain.SignificanceVertexPartition and weighted == True:
            raise Exception('SignificanceVertexPartition only support unweighted graphs')
        if partition_type == louvain.ModularityVertexPartition:
            partition, quality = louvain_multiplex(G, partition_type, interslice_weight)
        else:
            partition, quality = louvain_multiplex(G, partition_type, interslice_weight, resolution_parameter)

    else:
        with open(graph, 'r') as f:
            lines = f.read().splitlines()
        Node2Index = {}
        elts = lines[0].split()
        if len(elts) == 3:
            weighted = True
        else:
            weighted = False
        index = 0
        for i in range(len(lines)):
            elts = lines[i].split()
            for j in range(2):
                elts[j] = int(elts[j])
                if elts[j] not in Node2Index :
                    Node2Index[elts[j]] = index
                    index += 1
            if weighted == True:
                elts[2] = float(elts[2])
            lines[i] = tuple(elts)
        Index2Node = {}
        for node in Node2Index:
            Index2Node[Node2Index[node]] = node
        f.close()
        G = igraph.Graph.TupleList(lines, directed=directed, weights=weighted)
        if weighted == False:
            weights = None
        else:
            weights = G.es['weight']
        partition = louvain.find_partition(G,partition_type, weights=weights, resolution_parameter = resolution_parameter)
        optimiser = louvain.Optimiser()
        optimiser.optimise_partition(partition)

    if len(partition) == 0:
        sys.stderr.write("No cluster; Resolution parameter may be too extreme")
        return 1

    maxNode = max(list(Node2Index.keys()))

    for i in range(len(partition)):
        sys.stdout.write(str(maxNode+len(partition)+1) + ',' + str(maxNode+i+1) + ',' + 'term-term' + ';')
        for n in partition[i]:
            sys.stdout.write(str(maxNode+i+1) + ',' + str(Index2Node[n]) + ',' + 'term-gene' + ';')
    sys.stdout.flush()
    return 0

def main(args):
    """
    Main entry point for program

    :param args: command line arguments usually :py:const:`sys.argv`
    :return: 0 for success otherwise failure
    :rtype: int
    """
    desc = """
    Runs louvain on command line, sending output to standard
    out 
    """

    theargs = _parse_arguments(desc, args[1:])

    try:
        inputfile = os.path.abspath(theargs.input)

        if theargs.directed is True:
            dval = True
        else:
            dval = False

        return run_louvain(inputfile, directed=dval)
    except Exception as e:
        sys.stderr.write('Caught exception: ' + str(e))
        return 2


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
