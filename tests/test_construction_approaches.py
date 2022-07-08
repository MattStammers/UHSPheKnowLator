import glob
import json
import logging
import os
import os.path
import pandas
import pickle
import shutil
import unittest

from rdflib import Graph, URIRef, BNode
from rdflib.namespace import OWL, RDF
from typing import Dict, List, Tuple

from pkt_kg.construction_approaches import KGConstructionApproach
from pkt_kg.utils import adds_edges_to_graph


class TestKGConstructionApproach(unittest.TestCase):
    """Class to test the KGBuilder class from the knowledge graph script."""

    def setUp(self):
        # initialize file location
        current_directory = os.path.dirname(__file__)
        dir_loc = os.path.join(current_directory, 'data')
        self.dir_loc = os.path.abspath(dir_loc)

        # set-up environment - make temp directory
        dir_loc_resources = os.path.join(current_directory, 'data/resources')
        self.dir_loc_resources = os.path.abspath(dir_loc_resources)
        os.mkdir(self.dir_loc_resources)
        os.mkdir(self.dir_loc_resources + '/construction_approach')

        # handle logging
        self.logs = os.path.abspath(current_directory + '/builds/logs')
        logging.disable(logging.CRITICAL)
        if len(glob.glob(self.logs + '/*.log')) > 0: os.remove(glob.glob(self.logs + '/*.log')[0])

        # copy data
        # empty master edges
        shutil.copyfile(self.dir_loc + '/Master_Edge_List_Dict_empty.json',
                        self.dir_loc_resources + '/Master_Edge_List_Dict_empty.json')

        # create edge list
        self.edge_dict = {"gene-phenotype": {"data_type": "subclass-class",
                                             "edge_relation": "RO_0003302",
                                             "uri": ["https://www.ncbi.nlm.nih.gov/gene/",
                                                     "http://purl.obolibrary.org/obo/"],
                                             "edge_list": [["2", "HP_0002511"], ["2", "HP_0000716"],
                                                           ["2", "HP_0000100"], ["9", "HP_0030955"],
                                                           ["9", "HP_0009725"], ["9", "HP_0100787"],
                                                           ["9", "HP_0012125"], ["10", "HP_0009725"],
                                                           ["10", "HP_0010301"], ["10", "HP_0045005"]]},
                          "gene-gene": {"data_type": "subclass-subclass",
                                        "edge_relation": "RO_0002435",
                                        "uri": ["https://www.ncbi.nlm.nih.gov/gene/",
                                                "https://www.ncbi.nlm.nih.gov/gene/"],
                                        "edge_list": [["3075", "1080"], ["3075", "4267"], ["4800", "10190"],
                                                      ["4800", "80219"], ["2729", "1962"], ["2729", "5096"],
                                                      ["8837", "6774"], ["8837", "8754"]]},
                          "disease-disease": {"data_type": "class-class",
                                              "edge_relation": "RO_0002435",
                                              "uri": ["https://www.ncbi.nlm.nih.gov/gene/",
                                                      "https://www.ncbi.nlm.nih.gov/gene/"],
                                              "edge_list": [["DOID_3075", "DOID_1080"], ["DOID_3075", "DOID_4267"],
                                                            ["DOID_4800", "DOID_10190"], ["DOID_4800", "DOID_80219"],
                                                            ["DOID_2729", "DOID_1962"], ["DOID_2729", "DOID_5096"],
                                                            ["DOID_8837", "DOID_6774"], ["DOID_8837", "DOID_8754"]]}
                          }

        self.edge_dict_inst = {"gene-phenotype": {"data_type": "instance-class",
                                                  "edge_relation": "RO_0003302",
                                                  "uri": ["https://www.ncbi.nlm.nih.gov/gene/",
                                                          "http://purl.obolibrary.org/obo/"],
                                                  "edge_list": [["2", "HP_0002511"], ["2", "HP_0000716"],
                                                                ["2", "HP_0000100"], ["9", "HP_0030955"],
                                                                ["9", "HP_0009725"], ["9", "HP_0100787"],
                                                                ["9", "HP_0012125"], ["10", "HP_0009725"],
                                                                ["10", "HP_0010301"], ["10", "HP_0045005"]]},
                               "gene-gene": {"data_type": "instance-instance",
                                             "edge_relation": "RO_0002435",
                                             "uri": ["https://www.ncbi.nlm.nih.gov/gene/",
                                                     "https://www.ncbi.nlm.nih.gov/gene/"],
                                             "edge_list": [["3075", "1080"], ["3075", "4267"], ["4800", "10190"],
                                                           ["4800", "80219"], ["2729", "1962"], ["2729", "5096"],
                                                           ["8837", "6774"], ["8837", "8754"]]},
                               "disease-disease": {"data_type": "class-class",
                                                   "edge_relation": "RO_0002435",
                                                   "uri": ["https://www.ncbi.nlm.nih.gov/gene/",
                                                           "https://www.ncbi.nlm.nih.gov/gene/"],
                                                   "edge_list": [["DOID_3075", "DOID_1080"], ["DOID_3075", "DOID_4267"],
                                                                 ["DOID_4800", "DOID_10190"],
                                                                 ["DOID_4800", "DOID_80219"],
                                                                 ["DOID_2729", "DOID_1962"], ["DOID_2729", "DOID_5096"],
                                                                 ["DOID_8837", "DOID_6774"],
                                                                 ["DOID_8837", "DOID_8754"]]}
                               }

        # create subclass mapping data
        subcls_map = {"2": ['SO_0001217'], "9": ['SO_0001217'], "10": ['SO_0001217'], "1080": ['SO_0001217'],
                      "1962": ['SO_0001217'], "2729": ['SO_0001217'], "3075": ['SO_0001217'], "4267": ['SO_0001217'],
                      "4800": ['SO_0001217'], "5096": ['SO_0001217'], "6774": ['SO_0001217'], "8754": ['SO_0001217'],
                      "8837": ['SO_0001217'], "10190": ['SO_0001217'], "80219": ['SO_0001217']}

        # save data
        with open(self.dir_loc_resources + '/construction_approach/subclass_construction_map.pkl', 'wb') as f:
            pickle.dump(subcls_map, f, protocol=4)

        # instantiate class
        self.kg_builder = KGConstructionApproach(self.dir_loc_resources)

        return None

    def test_class_initialization_parameters_write_location(self):
        """Tests the class initialization parameters for write location."""

        self.assertRaises(ValueError, KGConstructionApproach, None)

        return None

    def test_class_initialization_parameters_subclass_dict(self):
        """Tests the class initialization parameters for subclass_dict."""

        # test when path does not exist
        self.assertRaises(OSError, KGConstructionApproach, self.dir_loc)

        # move files around for test
        os.remove(self.dir_loc_resources + '/construction_approach/subclass_construction_map.pkl')
        shutil.copyfile(self.dir_loc + '/subclass_construction_map_empty.pkl',
                        self.dir_loc_resources + '/construction_approach/subclass_construction_map_empty.pkl')

        # run tests
        self.assertRaises(TypeError, KGConstructionApproach, self.dir_loc_resources)

        # clean up environment
        os.remove(self.dir_loc_resources + '/construction_approach/subclass_construction_map_empty.pkl')

        return None

    def test_class_initialization(self):
        """Tests the class initialization."""

        # check write_location
        self.assertIsInstance(self.kg_builder.write_location, str)

        # subclass dict
        self.assertIsInstance(self.kg_builder.subclass_dict, Dict)
        self.assertTrue(len(self.kg_builder.subclass_dict) == 15)

        # subclass_error dict
        self.assertIsInstance(self.kg_builder.subclass_error, Dict)
        self.assertTrue(len(self.kg_builder.subclass_error) == 0)

        return None

    def test_maps_node_to_class(self):
        """Tests the maps_node_to_class method"""

        # test when entity in subclass_dict
        result = self.kg_builder.maps_node_to_class('gene-phenotype', '2')
        self.assertEqual(['SO_0001217'], result)

        # test when entity not in subclass_dict
        # update subclass dict to remove an entry
        del self.kg_builder.subclass_dict['2']
        result = self.kg_builder.maps_node_to_class('gene-phenotype', '2')
        self.assertEqual(None, result)

        return None

    def test_subclass_core_constructor_with_inverse(self):
        """Tests the class_edge_constructor method with inverse relations."""

        # prepare input vars
        # nodes
        node1, node2 = URIRef('https://www.ncbi.nlm.nih.gov/gene/2'), URIRef('https://www.ncbi.nlm.nih.gov/gene/10')

        # relations
        relation = URIRef('http://purl.obolibrary.org/obo/RO_0002435')
        inverse_relation = URIRef('http://purl.obolibrary.org/obo/RO_0002435')

        # add edges
        edges = self.kg_builder.subclass_core_constructor(node1, node2, relation, inverse_relation)

        self.assertIsInstance(edges, Tuple)
        self.assertEqual(len(edges), 18)

        return None

    def test_instance_core_constructor_with_inverse(self):
        """Tests the class_edge_constructor method with inverse relations."""

        # prepare input vars
        # nodes
        node1, node2 = URIRef('https://www.ncbi.nlm.nih.gov/gene/2'), URIRef('https://www.ncbi.nlm.nih.gov/gene/10')

        # relations
        relation = URIRef('http://purl.obolibrary.org/obo/RO_0002435')
        inverse_relation = URIRef('http://purl.obolibrary.org/obo/RO_0002435')

        # add edges
        edges = self.kg_builder.instance_core_constructor(node1, node2, relation, inverse_relation)

        self.assertIsInstance(edges, Tuple)
        self.assertEqual(len(edges), 8)

        return None

    def test_subclass_core_constructor_without_inverse(self):
        """Tests the class_edge_constructor method without inverse relations."""

        # prepare input vars
        # nodes
        node1, node2 = URIRef('https://www.ncbi.nlm.nih.gov/gene/2'), URIRef('https://www.ncbi.nlm.nih.gov/gene/10')

        # relations
        relation = URIRef('http://purl.obolibrary.org/obo/RO_0002435')
        inverse_relation = None

        # add edges
        edges = self.kg_builder.subclass_core_constructor(node1, node2, relation, inverse_relation)

        self.assertIsInstance(edges, Tuple)
        self.assertEqual(len(edges), 9)

        return None

    def test_instance_core_constructor_without_inverse(self):
        """Tests the class_edge_constructor method without inverse relations."""

        # prepare input vars
        # nodes
        node1, node2 = URIRef('https://www.ncbi.nlm.nih.gov/gene/2'), URIRef('https://www.ncbi.nlm.nih.gov/gene/10')

        # relations
        relation = URIRef('http://purl.obolibrary.org/obo/RO_0002435')
        inverse_relation = None

        # add edges
        edges = self.kg_builder.instance_core_constructor(node1, node2, relation, inverse_relation)

        self.assertIsInstance(edges, Tuple)
        self.assertEqual(len(edges), 6)

        return None

    def test_subclass_constructor_bad_map(self):
        """Tests the subclass_constructor method for an edge that contains an identifier that is not included in the
        subclass_map_dict."""

        # prepare input vars
        del self.kg_builder.subclass_dict['2']

        # edge_info
        edge_info = {'n1': 'subclass', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['2', 'HP_0000716']}

        # test method
        edges = self.kg_builder.subclass_constructor(edge_info, 'gene-phenotype')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 0)

        # check subclass error log
        self.assertIsInstance(self.kg_builder.subclass_error, Dict)
        self.assertIn('gene-phenotype', self.kg_builder.subclass_error.keys())
        self.assertEqual(self.kg_builder.subclass_error['gene-phenotype'], ['2'])

        return None

    def test_subclass_constructor_class_entity_without_inverse(self):
        """Tests the subclass_constructor method for edge with class-entity data type."""

        # prepare input vars - NO INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'subclass', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['2', 'HP_0110035']}

        # test method
        edges = self.kg_builder.subclass_constructor(edge_info, 'gene-phenotype')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 11)

        return None

    def test_subclass_constructor_class_entity_inverse(self):
        """Tests the subclass_constructor method for edge with class-entity data type with inverse relations."""

        # prepare input vars - WITH INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'subclass', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': 'RO_0003302',
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['2', 'HP_0110035']}

        # test method
        edges = self.kg_builder.subclass_constructor(edge_info, 'gene-phenotype')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 20)
        self.assertEqual(len(set(edges)), 17)

        return None

    def test_subclass_constructor_class_class_no_inverse(self):
        """Tests the subclass_constructor method for edge with class-class data type with relations only."""

        # prepare input vars - NO INVERSE
        # edge information
        edge_info = {'n1': 'class', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['http://purl.obolibrary.org/obo/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['DOID_3075', 'DOID_1080']}

        # test method
        edges = self.kg_builder.subclass_constructor(edge_info, 'disease-disease')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 9)

        return None

    def test_subclass_constructor_class_class_inverse(self):
        """Tests the subclass_constructor method for edge with class-class data type with inverse relations."""

        # prepare input vars - WITH INVERSE
        # edge information
        edge_info = {'n1': 'class', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': 'RO_0003302',
                     'uri': ['http://purl.obolibrary.org/obo/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['DOID_3075', 'DOID_1080']}

        # test method
        edges = self.kg_builder.subclass_constructor(edge_info, 'disease-disease')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 18)
        self.assertEqual(len(set(edges)), 15)

        return None

    def test_subclass_constructor_entity_entity_relations(self):
        """Tests the subclass_constructor method for edge with entity-entity data type with single relations."""

        # prepare input vars - NO INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'subclass', 'n2': 'subclass', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'https://www.ncbi.nlm.nih.gov/gene/'],
                     'edges': ['2', '10']}

        # test method
        edges = self.kg_builder.subclass_constructor(edge_info, 'gene-gene')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 13)
        self.assertEqual(len(set(edges)), 12)

        return None

    def test_subclass_constructor_entity_entity_inverse_relations(self):
        """Tests the subclass_constructor method for edge with entity-entity data type with inverse relations."""

        # prepare input vars - WITH INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'subclass', 'n2': 'subclass', 'rel': 'RO_0003302', 'inv_rel': 'RO_0003302',
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'https://www.ncbi.nlm.nih.gov/gene/'],
                     'edges': ['2', '10']}

        # test method
        edges = self.kg_builder.subclass_constructor(edge_info, 'gene-gene')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 22)
        self.assertEqual(len(set(edges)), 18)

        return None

    def test_instance_constructor_class_class_relations(self):
        """Tests the instance_constructor method for edge with class-class data type with a single relation."""

        # prepare input vars -- NO INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'class', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['http://purl.obolibrary.org/obo/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['DOID_3075', 'DOID_1080']}

        # test method
        edges = self.kg_builder.instance_constructor(edge_info, 'disease-disease')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 6)

        return None

    def test_instance_constructor_class_class_inverse_relations(self):
        """Tests the instance_constructor method for edge with class-class data type with inverse relations."""

        # prepare input vars -- WITH INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'class', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': 'RO_0003302',
                     'uri': ['http://purl.obolibrary.org/obo/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['DOID_3075', 'DOID_1080']}

        # test method
        edges = self.kg_builder.instance_constructor(edge_info, 'disease-disease')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 8)
        self.assertEqual(len(set(edges)), 7)

        return None

    def test_instance_constructor_entity_entity_relations(self):
        """Tests the instance_constructor method for edge with entity-entity data type with single relations."""

        # prepare input vars - NO INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'instance', 'n2': 'instance', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'https://www.ncbi.nlm.nih.gov/gene/'],
                     'edges': ['2', '10']}

        # test method
        edges = self.kg_builder.instance_constructor(edge_info, 'gene-gene')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 12)
        self.assertEqual(len(set(edges)), 11)

        return None

    def test_instance_constructor_entity_entity_inverse_relations(self):
        """Tests the instance_constructor method for edge with entity-entity data type with inverse relations."""

        # prepare input vars - WITH INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'instance', 'n2': 'instance', 'rel': 'RO_0003302', 'inv_rel': 'RO_0003302',
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'https://www.ncbi.nlm.nih.gov/gene/'],
                     'edges': ['2', '10']}

        # test method
        edges = self.kg_builder.instance_constructor(edge_info, 'gene-gene')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 14)
        self.assertEqual(len(set(edges)), 12)

        return None

    def test_instance_constructor_entity_class_relations(self):
        """Tests the instance_constructor method for edge with entity-class data type with relations only."""

        # prepare input vars - NO INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'instance', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': None,
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['2', 'HP_0110035']}

        # test method
        edges = self.kg_builder.instance_constructor(edge_info, 'gene-phenotype')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 9)

        return None

    def test_instance_constructor_entity_class_inverse(self):
        """Tests the instance_constructor method for edge with entity-class data type with inverse relations."""

        # prepare input vars - WITH INVERSE RELATIONS
        # edge information
        edge_info = {'n1': 'instance', 'n2': 'class', 'rel': 'RO_0003302', 'inv_rel': 'RO_0003302',
                     'uri': ['https://www.ncbi.nlm.nih.gov/gene/', 'http://purl.obolibrary.org/obo/'],
                     'edges': ['2', 'HP_0110035']}

        # test method
        edges = self.kg_builder.instance_constructor(edge_info, 'gene-phenotype')

        # check returned results
        self.assertIsInstance(edges, List)
        self.assertEqual(len(edges), 11)
        self.assertEqual(len(set(edges)), 10)

        return None

    def tearDown(self):

        # remove resource directory
        shutil.rmtree(self.dir_loc_resources)

        return None
