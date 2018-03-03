# -*- coding: utf-8 -*-
"""Helpers for SPQRQL"""

# Give me the object to given subject and predicate
# "Attribute" query
from rdflib.namespace import DCTERMS
from rdflib.namespace import FOAF
from rdflib.namespace import Namespace
from rdflib.namespace import RDF
from rdflib.namespace import SKOS
from rdflib.plugins.sparql import prepareQuery


DCT = DCTERMS
DCAT = Namespace('http://www.w3.org/ns/dcat#')

# List of namespaces for SPARQL Queries.
# Todo: would be good if this list came from the plone config
INIT_NS = {
    'dct': DCTERMS,
    'foaf': FOAF,
    'skos': SKOS,
    'dcat': DCAT,
    'rdf': RDF,
    }

# Give me the object to a given subject and predicate.
# E.g. give me the dct:publisher to a dcat:Catalog
QUERY_ATT = prepareQuery(
    """SELECT DISTINCT ?o
       WHERE {
          ?s ?p ?o
       }""",
    initNs=INIT_NS,
)

# Give me the objects to given predicate
# "a" query
QUERY_A = prepareQuery(
    """SELECT DISTINCT ?s
       WHERE {
          ?s a ?o
       }""",
    initNs=INIT_NS,
    )