import glob
import json
import logging
import networkx  # type: ignore
import os
import os.path
import pandas
import pickle
import ray
import shutil
import unittest
import warnings

from collections import ChainMap
from mock import patch
from rdflib import Graph, URIRef, BNode, Namespace
from rdflib.namespace import OWL, RDF, RDFS
from typing import Dict, List

from pkt_kg.__version__ import __version__
from pkt_kg.knowledge_graph import FullBuild, PartialBuild, PostClosureBuild
from pkt_kg.metadata import Metadata
from pkt_kg.utils import *

obo = Namespace('http://purl.obolibrary.org/obo/')


class TestKGBuilder(unittest.TestCase):
    """Class to test the KGBuilder class from the knowledge graph script."""

    def setUp(self):

        warnings.simplefilter('ignore', ResourceWarning)

        # initialize file location
        current_directory = os.path.dirname(__file__)
        dir_loc = os.path.join(current_directory, 'data')
        self.dir_loc = os.path.abspath(dir_loc)

        # set-up environment - make temp directory
        dir_loc_resources = os.path.join(current_directory, 'resources')
        self.dir_loc_resources = os.path.abspath(dir_loc_resources)
        os.mkdir(self.dir_loc_resources)
        os.mkdir(self.dir_loc_resources + '/knowledge_graphs')
        os.mkdir(self.dir_loc_resources + '/relations_data')
        os.mkdir(self.dir_loc_resources + '/node_data')
        os.mkdir(self.dir_loc_resources + '/ontologies')
        os.mkdir(self.dir_loc_resources + '/construction_approach')

        # handle logging
        self.logs = os.path.abspath(current_directory + '/builds/logs')
        logging.disable(logging.CRITICAL)
        if len(glob.glob(self.logs + '/*.log')) > 0: os.remove(glob.glob(self.logs + '/*.log')[0])

        # copy needed data data
        # node metadata
        shutil.copyfile(self.dir_loc + '/node_data/node_metadata_dict.pkl',
                        self.dir_loc_resources + '/node_data/node_metadata_dict.pkl')
        # ontology data
        shutil.copyfile(self.dir_loc + '/ontologies/empty_hp_with_imports.owl',
                        self.dir_loc_resources + '/ontologies/hp_with_imports.owl')
        # merged ontology data
        shutil.copyfile(self.dir_loc + '/ontologies/so_with_imports.owl',
                        self.dir_loc_resources + '/knowledge_graphs/PheKnowLator_MergedOntologies.owl')
        # relations data
        shutil.copyfile(self.dir_loc + '/RELATIONS_LABELS.txt',
                        self.dir_loc_resources + '/relations_data/RELATIONS_LABELS.txt')
        # inverse relations
        shutil.copyfile(self.dir_loc + '/INVERSE_RELATIONS.txt',
                        self.dir_loc_resources + '/relations_data/INVERSE_RELATIONS.txt')
        # empty master edges
        shutil.copyfile(self.dir_loc + '/Master_Edge_List_Dict_empty.json',
                        self.dir_loc_resources + '/Master_Edge_List_Dict_empty.json')

        # create edge list
        edge_dict = {"gene-phenotype": {"data_type": "entity-class",
                                        "edge_relation": "RO_0003302",
                                        "uri": ["http://www.ncbi.nlm.nih.gov/gene/",
                                                "http://purl.obolibrary.org/obo/"],
                                        "edge_list": [["2", "SO_0000162"], ["2", "SO_0000196"],
                                                      ["3", "SO_0000323"], ["9", "SO_0001490"],
                                                      ["10", "SO_0000301"], ["11", "SO_0001560"],
                                                      ["12", "SO_0001560"], ["17", "SO_0000444"],
                                                      ["18", "SO_0002138"], ["20", "SO_0000511"]]},
                     "gene-gene": {"data_type": "entity-entity",
                                   "edge_relation": "RO_0002435",
                                   "uri": ["http://www.ncbi.nlm.nih.gov/gene/",
                                           "http://www.ncbi.nlm.nih.gov/gene/"],
                                   "edge_list": [["1", "2"], ["2", "3"], ["3", "18"],
                                                 ["17", "19"], ["4", "17"], ["5", "11"],
                                                 ["11", "12"], ["4", "5"]]},
                     "disease-disease": {"data_type": "class-class",
                                         "edge_relation": "RO_0002435",
                                         "uri": ["http://www.ncbi.nlm.nih.gov/gene/",
                                                 "http://www.ncbi.nlm.nih.gov/gene/"],
                                         "edge_list": [["DOID_3075", "DOID_1080"], ["DOID_3075", "DOID_4267"],
                                                       ["DOID_4800", "DOID_10190"], ["DOID_4800", "DOID_80219"],
                                                       ["DOID_2729", "DOID_1962"], ["DOID_2729", "DOID_5096"],
                                                       ["DOID_8837", "DOID_6774"], ["DOID_8837", "DOID_8754"]]},
                     "entity_namespaces": {"gene": "http://purl.uniprot.org/geneid/"}
                     }

        edge_dict_inst = {"gene-phenotype": {"data_type": "entity-class",
                                             "edge_relation": "RO_0003302",
                                             "uri": ["http://www.ncbi.nlm.nih.gov/gene/",
                                                     "http://purl.obolibrary.org/obo/"],
                                             "edge_list": [["2", "SO_0000162"], ["2", "SO_0000196"],
                                                           ["3", "SO_0000323"], ["9", "SO_0001490"],
                                                           ["10", "SO_0000301"], ["11", "SO_0001560"],
                                                           ["12", "SO_0001560"], ["17", "SO_0000444"],
                                                           ["18", "SO_0002138"], ["19", "SO_0000511"]]},
                          "gene-gene": {"data_type": "entity-entity",
                                        "edge_relation": "RO_0002435",
                                        "uri": ["http://www.ncbi.nlm.nih.gov/gene/",
                                                "http://www.ncbi.nlm.nih.gov/gene/"],
                                        "edge_list": [["1", "2"], ["2", "3"], ["3", "18"],
                                                      ["17", "19"], ["4", "17"], ["5", "11"],
                                                      ["11", "12"], ["4", "5"]]},
                          "disease-disease": {"data_type": "class-class",
                                              "edge_relation": "RO_0002435",
                                              "uri": ["http://www.ncbi.nlm.nih.gov/gene/",
                                                      "http://www.ncbi.nlm.nih.gov/gene/"],
                                              "edge_list": [["DOID_3075", "DOID_1080"], ["DOID_3075", "DOID_4267"],
                                                            ["DOID_4800", "DOID_10190"], ["DOID_4800", "DOID_80219"],
                                                            ["DOID_2729", "DOID_1962"], ["DOID_2729", "DOID_5096"],
                                                            ["DOID_8837", "DOID_6774"], ["DOID_8837", "DOID_8754"]]},
                          "entity_namespaces": {"gene": "http://purl.uniprot.org/geneid/"}
                          }

        # save data
        with open(self.dir_loc_resources + '/Master_Edge_List_Dict.json', 'w') as filepath:
            json.dump(edge_dict, filepath)

        with open(self.dir_loc_resources + '/Master_Edge_List_Dict_instance.json', 'w') as filepath:
            json.dump(edge_dict_inst, filepath)

        # create subclass mapping data
        subcls_map = {"1": ['SO_0001217'], "2": ['SO_0001217'], "3": ['SO_0001217'], "4": ['SO_0001217'],
                      "5": ['SO_0001217'], "11": ['SO_0001217'], "12": ['SO_0001217'], "17": ['SO_0001217'],
                      "18": ['SO_0001217'], "5096": ['SO_0001217'], "6774": ['SO_0001217'], "19": ['SO_0001217']}

        # save data
        with open(self.dir_loc_resources + '/construction_approach/subclass_construction_map.pkl', 'wb') as f:
            pickle.dump(subcls_map, f, protocol=4)

        # set write location
        self.write_location = self.dir_loc_resources + '/knowledge_graphs'

        # build 3 different knowledge graphs
        self.kg_subclass = FullBuild(construction='subclass', node_data='yes', inverse_relations='yes',
                                     decode_owl='yes', cpus=1, write_location=self.write_location)
        self.kg_instance = PartialBuild(construction='instance', node_data='yes', inverse_relations='no',
                                        decode_owl='no', cpus=1, write_location=self.write_location)
        self.kg_instance2 = PartialBuild(construction='instance', node_data='yes', inverse_relations='yes',
                                         decode_owl='yes', cpus=1, write_location=self.write_location)
        self.kg_closure = PostClosureBuild(construction='instance', node_data='yes', inverse_relations='yes',
                                           decode_owl='no', cpus=1, write_location=self.write_location)

        # update class attributes for the location of owltools
        dir_loc_owltools = os.path.join(current_directory, 'utils/owltools')
        self.kg_subclass.owl_tools = os.path.abspath(dir_loc_owltools)
        self.kg_instance.owl_tools = os.path.abspath(dir_loc_owltools)
        self.kg_instance2.owl_tools = os.path.abspath(dir_loc_owltools)

        # create inner class instance
        args = {'construction': self.kg_subclass.construct_approach, 'edge_dict': self.kg_subclass.edge_dict,
                'kg_owl': '', 'rel_dict': self.kg_subclass.relations_dict,
                'inverse_dict': self.kg_subclass.inverse_relations_dict, 'node_data': self.kg_subclass.node_data,
                'ont_cls': self.kg_subclass.ont_classes, 'metadata': None, 'obj_props': self.kg_subclass.obj_properties,
                'write_loc': self.kg_subclass.write_location}
        self.inner_class = self.kg_subclass.EdgeConstructor(args)

        # get release
        self.current_release = 'v' + __version__

        return None

    def test_class_initialization_parameters_version(self):
        """Tests the class initialization parameters for version."""

        self.assertEqual(self.kg_subclass.kg_version, self.current_release)

        return None

    def test_class_initialization_parameters_ontologies_missing(self):
        """Tests the class initialization parameters for ontologies when the directory is missing."""

        # run test when there is no ontologies directory
        shutil.rmtree(self.dir_loc_resources + '/ontologies')
        self.assertRaises(OSError, FullBuild, 'subclass', 'yes', 'yes', 'yes', 1, self.write_location)

        return None

    def test_class_initialization_parameters_ontologies_empty(self):
        """Tests the class initialization parameters for ontologies when it's empty."""

        # create empty ontologies directory
        shutil.rmtree(self.dir_loc_resources + '/ontologies')
        os.mkdir(self.dir_loc_resources + '/ontologies')
        self.assertRaises(TypeError, FullBuild, 'subclass', 'yes', 'yes', 'yes', 1, self.write_location)

        return None

    def test_class_initialization_parameters_construction_approach(self):
        """Tests the class initialization parameters for construction_approach."""

        self.assertRaises(ValueError, FullBuild, 1, 'yes', 'yes', 'yes', 1, self.write_location)
        self.assertRaises(ValueError, FullBuild, 'subcls', 'yes', 'yes', 'yes', 1, self.write_location)
        self.assertRaises(ValueError, FullBuild, 'inst', 'yes', 'yes', 'yes', 1, self.write_location)

        return None

    def test_class_initialization_parameters_edge_data_missing(self):
        """Tests the class initialization parameters for edge_data when the file is missing."""

        # remove file to trigger OSError
        os.remove(self.dir_loc_resources + '/Master_Edge_List_Dict.json')
        self.assertRaises(OSError, FullBuild, 'subclass', 'yes', 'yes', 'yes', 1, self.write_location)

        return None

    def test_class_initialization_parameters_edge_data_empty(self):
        """Tests the class initialization parameters for edge_data when the file is empty."""

        # rename empty to be main file
        os.rename(self.dir_loc_resources + '/Master_Edge_List_Dict_empty.json',
                  self.dir_loc_resources + '/Master_Edge_List_Dict.json')
        self.assertRaises(TypeError, FullBuild, 'subclass', 'yes', 'yes', 'yes', 1, self.write_location)

        return None

    def test_class_initialization_parameter_relations_format(self):
        """Tests the class initialization parameters for relations when the input parameter is formatted wrong."""

        self.assertRaises(ValueError, FullBuild, 'subclass', 'yes', 1, 'yes', 1, self.write_location)
        self.assertRaises(ValueError, FullBuild, 'subclass', 'yes', 'ye', 'yes', 1, self.write_location)

        return None

    def test_class_initialization_parameter_relations_missing(self):
        """Tests the class initialization parameters for relations when the files are missing."""

        # remove relations and inverse relations data
        rel_loc = self.dir_loc_resources + '/relations_data/RELATIONS_LABELS.txt'
        invrel_loc = self.dir_loc_resources + '/relations_data/INVERSE_RELATIONS.txt'
        os.remove(rel_loc); os.remove(invrel_loc)
        self.assertRaises(TypeError, FullBuild, 'subclass', 'yes', 'yes', 'yes', 1, self.write_location)

        # add back deleted data
        shutil.copyfile(self.dir_loc + '/RELATIONS_LABELS.txt', rel_loc)
        shutil.copyfile(self.dir_loc + '/INVERSE_RELATIONS.txt', invrel_loc)

        return None

    def test_class_initialization_parameters_node_metadata_format(self):
        """Tests the class initialization parameters for node_metadata with different formatting."""

        self.assertRaises(ValueError, FullBuild, 'subclass', 1, 'yes', 'yes', 1, self.write_location)
        self.assertRaises(ValueError, FullBuild, 'subclass', 'ye', 'yes', 'yes', 1, self.write_location)

        return None

    def test_class_initialization_parameters_node_metadata_missing(self):
        """Tests the class initialization parameters for node_metadata."""

        # remove node metadata
        gene_phen_data = self.dir_loc_resources + '/node_data/node_metadata_dict.pkl'
        os.remove(gene_phen_data)

        # test method
        self.assertRaises(TypeError, FullBuild, 'subclass', 'yes', 'yes', 'yes', 1, self.write_location)

        # add back deleted data
        shutil.copyfile(self.dir_loc + '/node_data/node_metadata_dict.pkl', gene_phen_data)

        return None

    def test_class_initialization_parameters_decoding_owl(self):
        """Tests the class initialization parameters for decoding owl."""

        self.assertRaises(ValueError, FullBuild, 'subclass', 'yes', 'yes', 1, 1, self.write_location)
        self.assertRaises(ValueError, FullBuild, 'subclass', 'yes', 'yes', 'ye', 1, self.write_location)

        return None

    def test_class_initialization_ontology_data(self):
        """Tests the class initialization for when no merged ontology file is created."""

        # removed merged ontology file
        os.remove(self.dir_loc_resources + '/knowledge_graphs/PheKnowLator_MergedOntologies.owl')

        # run test
        self.kg_subclass = FullBuild('subclass', 'yes', 'yes', 'yes', 1, self.write_location)
        # check that there is 1 ontology file
        self.assertIsInstance(self.kg_subclass.ontologies, List)
        self.assertTrue(len(self.kg_subclass.ontologies) == 1)

        return None

    def test_class_initialization_attributes(self):
        """Tests the class initialization for class attributes."""

        self.assertTrue(self.kg_subclass.build == 'full')
        self.assertTrue(self.kg_subclass.construct_approach == 'subclass')
        self.assertTrue(self.kg_subclass.kg_version == self.current_release)
        path = os.path.abspath(self.dir_loc_resources + '/knowledge_graphs')
        self.assertTrue(self.kg_subclass.write_location == path)

        return None

    def test_class_initialization_edgelist(self):
        """Tests the class initialization for edge_list inputs."""

        self.assertIsInstance(self.kg_subclass.edge_dict, Dict)
        self.assertIn('gene-phenotype', self.kg_subclass.edge_dict.keys())
        self.assertIn('data_type', self.kg_subclass.edge_dict['gene-phenotype'].keys())
        self.assertTrue(self.kg_subclass.edge_dict['gene-phenotype']['data_type'] == 'entity-class')
        self.assertIn('uri', self.kg_subclass.edge_dict['gene-phenotype'].keys())
        self.assertTrue(len(self.kg_subclass.edge_dict['gene-phenotype']['uri']) == 2)
        self.assertIn('edge_list', self.kg_subclass.edge_dict['gene-phenotype'].keys())
        self.assertTrue(len(self.kg_subclass.edge_dict['gene-phenotype']['edge_list']) == 10)
        self.assertIn('edge_relation', self.kg_subclass.edge_dict['gene-phenotype'].keys())

        return None

    def test_class_initialization_node_metadata(self):
        """Tests the class initialization for node metadata inputs."""

        self.assertIsInstance(self.kg_subclass.node_dict, Dict)
        self.assertTrue(len(self.kg_subclass.node_dict) == 0)

        return None

    def test_class_initialization_relations(self):
        """Tests the class initialization for relations input."""

        self.assertIsInstance(self.kg_subclass.inverse_relations, List)
        self.assertIsInstance(self.kg_subclass.relations_dict, Dict)
        self.assertTrue(len(self.kg_subclass.relations_dict) == 0)
        self.assertIsInstance(self.kg_subclass.inverse_relations_dict, Dict)
        self.assertTrue(len(self.kg_subclass.inverse_relations_dict) == 0)

        return None

    def test_class_initialization_ontologies(self):
        """Tests the class initialization for ontology inputs."""

        self.assertIsInstance(self.kg_subclass.ontologies, List)
        self.assertTrue(len(self.kg_subclass.ontologies) == 1)
        self.assertTrue(os.path.exists(self.kg_subclass.merged_ont_kg))

        return None

    def test_class_initialization_owl_decoding(self):
        """Tests the class initialization for the decode_owl input."""

        self.assertTrue(self.kg_subclass.decode_owl == 'yes')

        return None

    def test_class_initialization_subclass(self):
        """Tests the subclass construction approach class initialization."""

        # check construction type
        self.assertTrue(self.kg_subclass.construct_approach == 'subclass')

        # check filepath and write location for knowledge graph
        write_file = '/PheKnowLator_' + self.current_release + '_full_subclass_inverseRelations_noOWL.owl'
        self.assertEqual(self.kg_subclass.full_kg, write_file)

        return None

    def test_class_initialization_instance(self):
        """Tests the instance construction approach class initialization."""

        # check build type
        self.assertTrue(self.kg_instance.build == 'partial')

        # check relations and owl decoding
        self.assertIsNone(self.kg_instance.decode_owl)
        self.assertIsNone(self.kg_instance.inverse_relations)

        # check construction type
        self.assertTrue(self.kg_instance.construct_approach == 'instance')

        # check filepath and write location for knowledge graph
        write_file = '/PheKnowLator_' + self.current_release + '_partial_instance_relationsOnly_OWL.owl'
        self.assertEqual(self.kg_instance.full_kg, write_file)

        return None

    def test_reverse_relation_processor(self):
        """Tests the reverse_relation_processor method."""

        self.kg_subclass.reverse_relation_processor()

        # check if data was successfully processed
        self.assertIsInstance(self.kg_subclass.inverse_relations_dict, Dict)
        self.assertTrue(len(self.kg_subclass.inverse_relations_dict) > 0)
        self.assertIsInstance(self.kg_subclass.relations_dict, Dict)
        self.assertTrue(len(self.kg_subclass.relations_dict) > 0)
        self.kg_instance.reverse_relation_processor()

        # check if data was successfully processed
        self.assertIsNone(self.kg_instance.inverse_relations_dict)
        self.assertIsInstance(self.kg_instance.relations_dict, Dict)

        return None

    def test_verifies_object_property(self):
        """Tests the verifies_object_property method."""

        # load graph
        self.kg_subclass.EdgeConstructor.graph = Graph()
        self.kg_subclass.graph.parse(self.dir_loc + '/ontologies/so_with_imports.owl')

        # get object properties
        self.kg_subclass.obj_properties = gets_object_properties(self.kg_subclass.graph)
        self.inner_class.object_properties = self.kg_subclass.obj_properties

        # check for presence of existing obj_prop
        self.assertIn(URIRef('http://purl.obolibrary.org/obo/so#position_of'), self.inner_class.object_properties)

        # test adding bad relation
        self.assertRaises(TypeError, self.inner_class.verifies_object_property, 'RO_0002200')

        # test adding a good relation
        new_relation = URIRef('http://purl.obolibrary.org/obo/' + 'RO_0002566')
        self.inner_class.verifies_object_property(new_relation)

        # update list of object properties
        self.kg_subclass.obj_properties = gets_object_properties(self.kg_subclass.graph)
        self.inner_class.object_properties = self.kg_subclass.obj_properties

        # make sure that object property was added to the graph
        self.assertTrue(new_relation in self.inner_class.obj_properties)

        return None

    def test_checks_classes(self):
        """Tests the checks_classes method for class-class edges."""

        # set-up inputs for class-class
        edge_info = {'n1': 'class', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['CHEBI_81395', 'DOID_12858']}

        self.inner_class.ont_classes = [URIRef('http://purl.obolibrary.org/obo/CHEBI_81395'),
                                        URIRef('http://purl.obolibrary.org/obo/DOID_12858')]

        self.assertTrue(self.inner_class.checks_classes(edge_info))

        # set-up inputs for class-class (FALSE)
        edge_info = {'n1': 'class', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['CHEBI_81395', 'DOID_1']}

        self.inner_class.ont_classes = ['http://purl.obolibrary.org/obo/CHEBI_81395',
                                        'http://purl.obolibrary.org/obo/DOID_128987']

        self.assertFalse(self.inner_class.checks_classes(edge_info))

        return None

    def test_checks_classes_subclasses(self):
        """Tests the checks_classes method for subclass edges."""

        # set-up inputs for subclass-subclass
        self.inner_class.ont_classes = {URIRef('http://purl.obolibrary.org/obo/DOID_12858')}

        edge_info = {'n1': 'entity', 'n2': 'entity', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['14', '134056']}

        self.assertTrue(self.inner_class.checks_classes(edge_info))

        # set-up inputs for subclass-class
        edge_info = {'n1': 'entity', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['14', 'DOID_12858']}

        self.assertTrue(self.inner_class.checks_classes(edge_info))

        # set-up inputs for class-subclass
        edge_info = {'n1': 'class', 'n2': 'entity', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['http://purl.obolibrary.org/obo/', 'https://www.ncbi.nlm.nih.gov/gene/'],
                     'edges': ['DOID_12858', '14']}

        self.assertTrue(self.inner_class.checks_classes(edge_info))

        return None

    def test_checks_relations(self):
        """Tests the checks_relations method."""

        self.kg_subclass.reverse_relation_processor()
        args = {'construction': self.kg_subclass.construct_approach, 'edge_dict': self.kg_subclass.edge_dict,
                'kg_owl': '', 'rel_dict': self.kg_subclass.relations_dict,
                'inverse_dict': self.kg_subclass.inverse_relations_dict, 'node_data': self.kg_subclass.node_data,
                'ont_cls': self.kg_subclass.ont_classes, 'metadata': None, 'obj_props': self.kg_subclass.obj_properties,
                'write_loc': self.kg_subclass.write_location}
        self.inner_class = self.kg_subclass.EdgeConstructor(args)

        # test 1
        edge_list1 = set(tuple(x) for x in self.inner_class.edge_dict['gene-phenotype']['edge_list'])
        rel1_check = self.inner_class.checks_relations('RO_0003302', edge_list1)
        self.assertIsNone(rel1_check)

        # test 2
        edge_list2 = set(tuple(x) for x in self.inner_class.edge_dict['gene-gene']['edge_list'])
        rel2_check = self.inner_class.checks_relations('RO_0002435', edge_list2)
        self.assertEqual(rel2_check, 'RO_0002435')

        return None

    def test_gets_edge_statistics(self):
        """Tests the gets_edge_statistics method."""

        # no inverse edges
        edges = [(1, 2, 3), (3, 2, 5), (4, 6, 7)]
        stats = self.inner_class.gets_edge_statistics('gene-gene', edges, [{1, 2, 3}, {1, 2, 3}, 8])
        expected_str = '3 OWL Edges, 8 Original Edges; 5 OWL Nodes, Original Nodes: 3 gene(s), 3 gene(s)'
        self.assertEqual(stats, expected_str)

        return None

    def test_gets_edge_statistics_inverse_relations(self):
        """Tests the gets_edge_statistics method when including inverse relations."""

        # no inverse edges
        edges = [(1, 2, 3), (3, 2, 5), (4, 6, 7)]
        stats = self.inner_class.gets_edge_statistics('drug-gene', edges, [{1, 2, 3}, {1, 2, 3}, 8])
        expected_str = '3 OWL Edges, 8 Original Edges; 5 OWL Nodes, Original Nodes: 3 drug(s), 3 gene(s)'
        self.assertEqual(stats, expected_str)

        return None

    def test_creates_new_edges_not_adding_metadata_to_kg(self):
        """Tests the creates_new_edges method without adding node metadata to the KG."""

        self.kg_subclass.reverse_relation_processor()

        # make sure that kg is empty
        self.kg_subclass.graph = Graph().parse(self.dir_loc + '/ontologies/so_with_imports.owl')
        self.kg_subclass.obj_properties = gets_object_properties(self.kg_subclass.graph)
        self.kg_subclass.ont_classes = gets_ontology_classes(self.kg_subclass.graph)
        # make sure to not add node_metadata
        self.kg_subclass.node_dict, self.kg_subclass.node_data = None, None
        # initialize metadata class
        meta = Metadata(self.kg_subclass.kg_version, self.kg_subclass.write_location, self.kg_subclass.full_kg,
                        self.kg_subclass.node_data, self.kg_subclass.node_dict)
        if self.kg_subclass.node_data: meta.metadata_processor(); meta.extract_metadata(self.kg_subclass.graph)
        # create graph subsets
        self.kg_subclass.graph, annotation_triples = splits_knowledge_graph(self.kg_subclass.graph)
        full_kg_owl = '_'.join(self.kg_subclass.full_kg.split('_')[0:-1]) + '_OWL.owl'
        annot, full = full_kg_owl[:-4] + '_AnnotationsOnly.nt', full_kg_owl[:-4] + '.nt'
        appends_to_existing_file(annotation_triples, self.kg_subclass.write_location + annot, ' ')
        clean_graph = updates_pkt_namespace_identifiers(self.kg_subclass.graph, self.kg_subclass.construct_approach)

        # test method
        shutil.copy(self.kg_subclass.write_location + annot, self.kg_subclass.write_location + full)
        appends_to_existing_file(set(self.kg_subclass.graph), self.kg_subclass.write_location + full, ' ')
        args = {'construction': self.kg_subclass.construct_approach, 'edge_dict': self.kg_subclass.edge_dict,
                'kg_owl': full_kg_owl, 'rel_dict': self.kg_subclass.relations_dict,
                'metadata': meta.creates_node_metadata, 'inverse_dict': self.kg_subclass.inverse_relations_dict,
                'node_data': self.kg_subclass.node_data, 'ont_cls': self.kg_subclass.ont_classes, 'obj_props':
                    self.kg_subclass.obj_properties, 'write_loc': self.kg_subclass.write_location}
        edges = [x for x in self.kg_subclass.edge_dict.keys()]
        ray.init(local_mode=True, ignore_reinit_error=True)
        actors = [ray.remote(self.kg_subclass.EdgeConstructor).remote(args) for _ in range(self.kg_subclass.cpus)]
        for i in range(0, len(edges)): actors[i % self.kg_subclass.cpus].creates_new_edges.remote(edges[i])
        res = ray.get([x.graph_getter.remote() for x in actors])
        g1 = [self.kg_subclass.graph] + [x[0] for x in res]; g2 = [clean_graph] + [x[1] for x in res]
        error_dicts = dict(ChainMap(*ray.get([x.error_dict_getter.remote() for x in actors]))); del actors
        ray.shutdown()

        # check that edges were added to the graph
        graph1 = set(x for y in [set(x) for x in g1] for x in y)
        graph2 = set(x for y in [set(x) for x in g2] for x in y)
        self.assertEqual(len(graph1), 9820)
        self.assertEqual(len(graph2), 9774)
        self.assertIsInstance(error_dicts, Dict)
        # check graph files were saved
        f_name = full_kg_owl[:-4] + '_AnnotationsOnly.nt'
        self.assertTrue(os.path.exists(self.kg_subclass.write_location + f_name))
        f_name = full_kg_owl[:-4] + '.nt'
        self.assertTrue(os.path.exists(self.kg_subclass.write_location + f_name))

        return None

    def test_creates_new_edges_adding_metadata_to_kg(self):
        """Tests the creates_new_edges method and adds node metadata to the KG."""

        self.kg_subclass.reverse_relation_processor()
        # make sure that kg is empty
        self.kg_subclass.graph = Graph().parse(self.dir_loc + '/ontologies/so_with_imports.owl')
        self.kg_subclass.obj_properties = gets_object_properties(self.kg_subclass.graph)
        self.kg_subclass.ont_classes = gets_ontology_classes(self.kg_subclass.graph)
        # make sure to add node_metadata
        meta = Metadata(self.kg_subclass.kg_version, self.kg_subclass.write_location, self.kg_subclass.full_kg,
                        self.kg_subclass.node_data, self.kg_subclass.node_dict)
        if self.kg_subclass.node_data: meta.metadata_processor(); meta.extract_metadata(self.kg_subclass.graph)
        # create graph subsets
        self.kg_subclass.graph, annotation_triples = splits_knowledge_graph(self.kg_subclass.graph)
        full_kg_owl = '_'.join(self.kg_subclass.full_kg.split('_')[0:-1]) + '_OWL.owl'
        annot, full = full_kg_owl[:-4] + '_AnnotationsOnly.nt', full_kg_owl[:-4] + '.nt'
        appends_to_existing_file(annotation_triples, self.kg_subclass.write_location + annot, ' ')
        clean_graph = updates_pkt_namespace_identifiers(self.kg_subclass.graph, self.kg_subclass.construct_approach)
        # test method
        shutil.copy(self.kg_subclass.write_location + annot, self.kg_subclass.write_location + full)
        appends_to_existing_file(set(self.kg_subclass.graph), self.kg_subclass.write_location + full, ' ')
        args = {'construction': self.kg_subclass.construct_approach, 'edge_dict': self.kg_subclass.edge_dict,
                'kg_owl': full_kg_owl, 'rel_dict': self.kg_subclass.relations_dict,
                'metadata': meta.creates_node_metadata, 'inverse_dict': self.kg_subclass.inverse_relations_dict,
                'node_data': self.kg_subclass.node_data, 'ont_cls': self.kg_subclass.ont_classes, 'obj_props':
                    self.kg_subclass.obj_properties, 'write_loc': self.kg_subclass.write_location}
        edges = [x for x in self.kg_subclass.edge_dict.keys()]
        ray.init(local_mode=True, ignore_reinit_error=True)
        actors = [ray.remote(self.kg_subclass.EdgeConstructor).remote(args) for _ in range(self.kg_subclass.cpus)]
        for i in range(0, len(edges)): actors[i % self.kg_subclass.cpus].creates_new_edges.remote(edges[i])
        res = ray.get([x.graph_getter.remote() for x in actors])
        g1 = [self.kg_subclass.graph] + [x[0] for x in res]; g2 = [clean_graph] + [x[1] for x in res]
        error_dicts = dict(ChainMap(*ray.get([x.error_dict_getter.remote() for x in actors]))); del actors
        ray.shutdown()

        # check that edges were added to the graph
        graph1 = set(x for y in [set(x) for x in g1] for x in y)
        graph2 = set(x for y in [set(x) for x in g2] for x in y)
        self.assertEqual(len(graph1), 9780)
        self.assertEqual(len(graph2), 9746)
        self.assertIsInstance(error_dicts, Dict)
        # check graph files were saved
        f_name = full_kg_owl[:-4] + '_AnnotationsOnly.nt'
        self.assertTrue(os.path.exists(self.kg_subclass.write_location + f_name))
        f_name = full_kg_owl[:-4] + '.nt'
        self.assertTrue(os.path.exists(self.kg_subclass.write_location + f_name))

        return None

    def test_creates_new_edges_instance_no_inverse(self):
        """Tests the creates_new_edges method when applied to a kg with instance-based construction without inverse
        relations."""

        self.kg_instance.reverse_relation_processor()
        # make sure that kg is empty
        self.kg_instance.graph = Graph().parse(self.dir_loc + '/ontologies/so_with_imports.owl')
        # initialize metadata class
        meta = Metadata(self.kg_instance.kg_version, self.kg_instance.write_location, self.kg_instance.full_kg,
                        self.kg_instance.node_data, self.kg_instance.node_dict)
        if self.kg_instance.node_data: meta.metadata_processor(); meta.extract_metadata(self.kg_instance.graph)
        # create graph subsets
        self.kg_instance.graph, annotation_triples = splits_knowledge_graph(self.kg_instance.graph)
        full_kg_owl = '_'.join(self.kg_instance.full_kg.split('_')[0:-1]) + '_OWL.owl'
        annot, full = full_kg_owl[:-4] + '_AnnotationsOnly.nt', full_kg_owl[:-4] + '.nt'
        appends_to_existing_file(annotation_triples, self.kg_instance.write_location + annot, ' ')
        clean_graph = updates_pkt_namespace_identifiers(self.kg_instance.graph, self.kg_instance.construct_approach)

        # test method
        shutil.copy(self.kg_instance.write_location + annot, self.kg_instance.write_location + full)
        appends_to_existing_file(set(self.kg_instance.graph), self.kg_instance.write_location + full, ' ')
        # check that edges were added to the graph
        args = {'construction': self.kg_instance.construct_approach, 'edge_dict': self.kg_instance.edge_dict,
                'kg_owl': full_kg_owl, 'rel_dict': self.kg_instance.relations_dict,
                'metadata': meta.creates_node_metadata, 'inverse_dict': self.kg_instance.inverse_relations_dict,
                'node_data': self.kg_instance.node_data, 'ont_cls': self.kg_instance.ont_classes,
                'obj_props': self.kg_instance.obj_properties, 'write_loc': self.kg_instance.write_location}
        edges = [x for x in self.kg_instance.edge_dict.keys()]
        ray.init(local_mode=True, ignore_reinit_error=True)
        actors = [ray.remote(self.kg_instance.EdgeConstructor).remote(args) for _ in range(self.kg_instance.cpus)]
        for i in range(0, len(edges)): actors[i % self.kg_instance.cpus].creates_new_edges.remote(edges[i])
        res = ray.get([x.graph_getter.remote() for x in actors])
        g1 = [self.kg_instance.graph] + [x[0] for x in res]; g2 = [clean_graph] + [x[1] for x in res]
        error_dicts = dict(ChainMap(*ray.get([x.error_dict_getter.remote() for x in actors]))); del actors
        ray.shutdown()

        # check that edges were added to the graph
        graph1 = set(x for y in [set(x) for x in g1] for x in y)
        graph2 = set(x for y in [set(x) for x in g2] for x in y)
        self.assertEqual(len(graph1), 9702)
        self.assertEqual(len(graph2), 9682)
        self.assertIsInstance(error_dicts, Dict)
        # check graph files were saved
        f_name = full_kg_owl[:-4] + '_AnnotationsOnly.nt'
        self.assertTrue(os.path.exists(self.kg_instance.write_location + f_name))
        f_name = full_kg_owl[:-4] + '.nt'
        self.assertTrue(os.path.exists(self.kg_instance.write_location + f_name))

        return None

    def test_creates_new_edges_instance_inverse(self):
        """Tests the creates_new_edges method when applied to a kg with instance-based construction with inverse
        relations."""

        self.kg_instance2.reverse_relation_processor()
        # make sure that kg is empty
        self.kg_instance2.graph = Graph().parse(self.dir_loc + '/ontologies/so_with_imports.owl')
        # initialize metadata class
        meta = Metadata(self.kg_instance2.kg_version, self.kg_instance2.write_location, self.kg_instance2.full_kg,
                        self.kg_instance2.node_data, self.kg_instance2.node_dict)
        if self.kg_instance2.node_data: meta.metadata_processor(); meta.extract_metadata(self.kg_instance2.graph)
        # create graph subsets
        self.kg_instance2.graph, annotation_triples = splits_knowledge_graph(self.kg_instance2.graph)
        full_kg_owl = '_'.join(self.kg_instance2.full_kg.split('_')[0:-1]) + '_OWL.owl'
        annot, full = full_kg_owl[:-4] + '_AnnotationsOnly.nt', full_kg_owl[:-4] + '.nt'
        appends_to_existing_file(annotation_triples, self.kg_instance2.write_location + annot, ' ')
        clean_graph = updates_pkt_namespace_identifiers(self.kg_instance2.graph, self.kg_instance2.construct_approach)

        # test method
        shutil.copy(self.kg_instance2.write_location + annot, self.kg_instance2.write_location + full)
        appends_to_existing_file(set(self.kg_instance2.graph), self.kg_instance2.write_location + full, ' ')
        # check that edges were added to the graph
        args = {'construction': self.kg_instance2.construct_approach, 'edge_dict': self.kg_instance2.edge_dict,
                'kg_owl': full_kg_owl, 'rel_dict': self.kg_instance2.relations_dict,
                'metadata': meta.creates_node_metadata, 'inverse_dict': self.kg_instance2.inverse_relations_dict,
                'node_data': self.kg_instance2.node_data, 'ont_cls': self.kg_instance2.ont_classes,
                'obj_props': self.kg_instance2.obj_properties, 'write_loc': self.kg_instance2.write_location}
        edges = [x for x in self.kg_instance2.edge_dict.keys()]
        ray.init(local_mode=True, ignore_reinit_error=True)
        actors = [ray.remote(self.kg_instance2.EdgeConstructor).remote(args) for _ in range(self.kg_instance2.cpus)]
        for i in range(0, len(edges)): actors[i % self.kg_instance2.cpus].creates_new_edges.remote(edges[i])
        res = ray.get([x.graph_getter.remote() for x in actors])
        g1 = [self.kg_instance2.graph] + [x[0] for x in res]; g2 = [clean_graph] + [x[1] for x in res]
        error_dicts = dict(ChainMap(*ray.get([x.error_dict_getter.remote() for x in actors]))); del actors
        ray.shutdown()

        # check that edges were added to the graph
        graph1 = set(x for y in [set(x) for x in g1] for x in y)
        graph2 = set(x for y in [set(x) for x in g2] for x in y)
        self.assertEqual(len(graph1), 9707)
        self.assertEqual(len(graph2), 9687)
        self.assertIsInstance(error_dicts, Dict)
        # check graph files were saved
        f_name = full_kg_owl[:-4] + '_AnnotationsOnly.nt'
        self.assertTrue(os.path.exists(self.kg_instance2.write_location + f_name))
        f_name = full_kg_owl[:-4] + '.nt'
        self.assertTrue(os.path.exists(self.kg_instance2.write_location + f_name))

        return None

    def test_creates_new_edges_adding_metadata_to_kg_bad(self):
        """Tests the creates_new_edges method and adds node metadata to the KG, but also makes sure that a log file is
        written for genes that are not in the subclass_map."""

        self.kg_subclass.reverse_relation_processor()
        # make sure that kg is empty
        self.kg_subclass.graph.parse(self.dir_loc + '/ontologies/so_with_imports.owl')
        self.kg_subclass.obj_properties = gets_object_properties(self.kg_subclass.graph)
        self.kg_subclass.ont_classes = gets_ontology_classes(self.kg_subclass.graph)
        # initialize metadata class
        meta = Metadata(self.kg_subclass.kg_version, self.kg_subclass.write_location, self.kg_subclass.full_kg,
                        self.kg_subclass.node_data, self.kg_subclass.node_dict)
        if self.kg_subclass.node_data: meta.metadata_processor(); meta.extract_metadata(self.kg_subclass.graph)
        # test method
        args = {'construction': self.kg_subclass.construct_approach, 'edge_dict': self.kg_subclass.edge_dict,
                'kg_owl': '', 'rel_dict': self.kg_subclass.relations_dict, 'ont_cls': self.kg_subclass.ont_classes,
                'metadata': meta.creates_node_metadata, 'inverse_dict': self.kg_subclass.inverse_relations_dict,
                'node_data': self.kg_subclass.node_data, 'obj_props': self.kg_subclass.obj_properties,
                'write_loc': self.kg_subclass.write_location}; edges = [x for x in self.kg_subclass.edge_dict.keys()]
        ray.init(local_mode=True, ignore_reinit_error=True)
        actors = [ray.remote(self.kg_subclass.EdgeConstructor).remote(args) for _ in range(self.kg_subclass.cpus)]
        for i in range(0, len(edges)): actors[i % self.kg_subclass.cpus].creates_new_edges.remote(edges[i])
        error_dicts = dict(ChainMap(*ray.get([x.error_dict_getter.remote() for x in actors]))); del actors
        ray.shutdown()

        # check that log file was written out
        self.assertIsInstance(error_dicts, Dict)
        self.assertEqual(len(error_dicts), 1)
        self.assertIn('gene-phenotype', error_dicts.keys())
        self.assertEqual(sorted(list(error_dicts['gene-phenotype'])), ['10', '20', '9'])

        return None

    def tests_graph_getter(self):
        """Tests graph_getter method."""

        results = self.inner_class.graph_getter()

        # verify results
        self.assertTrue(len(results) == 2)
        self.assertIsInstance(results[0], Graph)
        self.assertIsInstance(results[1], Graph)

        return None

    def tearDown(self):
        warnings.simplefilter('default', ResourceWarning)

        # remove resource directory
        shutil.rmtree(self.dir_loc_resources)

        return None
