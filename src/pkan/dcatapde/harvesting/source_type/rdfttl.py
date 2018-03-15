# -*- coding: utf-8 -*-
"""Harvesting adapter."""
from DateTime.DateTime import time
from pkan.dcatapde import _
from pkan.dcatapde.constants import HARVESTER_DEFAULT_KEY
from pkan.dcatapde.constants import HARVESTER_DEXTERITY_KEY
from pkan.dcatapde.constants import HARVESTER_ENTITY_KEY
from pkan.dcatapde.constants import MAX_QUERY_PREVIEW_LENGTH
from pkan.dcatapde.constants import RDF_FORMAT_JSONLD
from pkan.dcatapde.constants import RDF_FORMAT_METADATA
from pkan.dcatapde.constants import RDF_FORMAT_TURTLE
from pkan.dcatapde.constants import RDF_FORMAT_XML
from pkan.dcatapde.content.harvester import IHarvester
from pkan.dcatapde.harvesting.errors import RequiredPredicateMissing
from pkan.dcatapde.harvesting.source_type.interfaces import IRDFJSONLD
from pkan.dcatapde.harvesting.source_type.interfaces import IRDFTTL
from pkan.dcatapde.harvesting.source_type.interfaces import IRDFXML
from pkan.dcatapde.harvesting.source_type.visitors import DCATVisitor
from pkan.dcatapde.harvesting.source_type.visitors import InputVisitor
from pkan.dcatapde.harvesting.source_type.visitors import Node
from pkan.dcatapde.harvesting.source_type.visitors import NS_ERROR
from pkan.dcatapde.harvesting.source_type.visitors import NS_WARNING
from pkan.dcatapde.harvesting.source_type.visitors import NT_DEFAULT
from pkan.dcatapde.harvesting.source_type.visitors import NT_DX_DEFAULT
from pkan.dcatapde.harvesting.source_type.visitors import NT_SPARQL
from pkan.dcatapde.harvesting.source_type.visitors import Scribe
from pkan.dcatapde.log.log import TranslatingFormatter
from pkan.dcatapde.structure.sparql import QUERY_A
from pkan.dcatapde.structure.sparql import QUERY_ATT
from pkan.dcatapde.structure.structure import IMP_REQUIRED
from pkan.dcatapde.structure.structure import StructDCATCatalog
from pkan.dcatapde.structure.structure import StructDCATDataset
from pkan.dcatapde.structure.structure import StructRDFSLiteral
from plone.api import content
from plone.api import portal
from plone.dexterity.utils import safe_unicode
from plone.memoize import ram
from pyparsing import ParseException
from rdflib import Graph
from rdflib.namespace import FOAF
from rdflib.plugins.memory import IOMemory
from rdflib.store import Store
from xml.sax import SAXParseException
from zope.annotation import IAnnotations
from zope.component import adapter
from zope.interface import implementer

import io
import logging
import vkbeautify as vkb


IFaceToRDFFormatKey = {
    IRDFTTL: RDF_FORMAT_TURTLE,
    IRDFJSONLD: RDF_FORMAT_JSONLD,
    IRDFXML: RDF_FORMAT_XML,
}


def cache_key(func, self):
    """cache key factory for rdf graph. With timeout 300 seconds
    :param func:
    :param self:
    :return:
    """
    key = u'{0}_{1}'.format(
        time() // 300,
        self.harvester.url,
    )
    return key


@adapter(IHarvester)
@implementer(IRDFTTL)
@implementer(IRDFJSONLD)
@implementer(IRDFXML)
class RDFProcessor(object):
    """Generic RDF Processor. Works for JSONLD, XML and Turtle RDF sources"""

    def __init__(self, harvester):
        # remember the harvester
        self.harvester = harvester
        # look if we have a harvesting type adapter
        try:
            self.harvesting_type = \
                self.harvester.harvesting_type(self.harvester)
        except TypeError:
            self.harvesting_type = None

        # fetch the preprocessor adapter
        self.data_cleaner = self.harvester.data_cleaner(self.harvester)
        self.cleaned_data = None
        # self.field_config = get_field_config(self.harvester)
        self.context = portal.get()
        if self.harvester:
            if self.harvester.base_object:
                # Todo: check why sometime to_object and sometimes not
                self.context = getattr(self.harvester.base_object,
                                       'to_object',
                                       self.harvester.base_object)

        # determine the source format serializer string for rdflib from our
        # own interface. Todo this is a bit ugly
        self.rdf_format_key = IFaceToRDFFormatKey[self.harvester.source_type]
        self.rdf_format = RDF_FORMAT_METADATA[self.rdf_format_key]
        self.serialize_format = self.rdf_format['serialize_as']
        self.def_lang = unicode(portal.get_default_language()[:2])
        self.setup_logger()
        self.get_entity_mapping()

    def read_rdf_file(self, uri):
        """Load the rdf data"""
        rdfstore = Store()
        # self.session = self.harvester.rdfstore.session
        # self.harvester.rdfstore.store.load_triples(source=uri, format=format)
        graph = Graph(rdfstore)
        # graph.open(uri)
        graph.parse(source=uri)
        return rdfstore, graph

    def get_entity_mapping(self):
        """Fill the mappings for the entities"""
        annotations = IAnnotations(self.harvester)
        self.mapping_sparql = {}
        self.mapping_dexterity = {}
        self.mapping_default = {}
        if HARVESTER_ENTITY_KEY in annotations:
            self.mapping_sparql = annotations[HARVESTER_ENTITY_KEY]
        if HARVESTER_DEXTERITY_KEY in annotations:
            self.mapping_dexterity = annotations[HARVESTER_DEXTERITY_KEY]
        if HARVESTER_DEFAULT_KEY in annotations:
            self.mapping_default = \
                annotations[HARVESTER_DEFAULT_KEY]

    @property
    @ram.cache(cache_key)
    def graph(self):
        """In Memory representation of the incoming RDF graph"""
        rdfstore = IOMemory()
        _graph = Graph(rdfstore)
        _graph.parse(source=self.harvester.url, format=self.serialize_format)
        return _graph

    def read_classes(self):
        """Read the classes of the rdf data for the vocabulary to assign
         to DX classes"""
        SPARQL = """SELECT DISCTINCT ?o WHERE {?s a ?o .}"""
        result = self.harvester.graph.query(SPARQL)
        return result

    def read_dcat_fields(self, *args, **kwargs):
        """Dummy"""
        return []

    def read_fields(self, *args, **kwargs):
        """Dummy"""
        return []

    def clean_data(self, *arg, **kwargs):
        """Dummy"""

    def setup_logger(self):
        """Log to a io.stream that can later be embedded in the view output"""
        # get a logger named after the serializing format we use
        log = logging.getLogger(self.serialize_format)
        # get and remember the stream
        self.log_stream = io.StringIO()
        # construct a streamhandler
        stream_handler = logging.StreamHandler(self.log_stream)
        # and a formatter for HTML output
        format = '<p>%(asctime)s - %(name)s - %(levelname)s - %(message)s</p>'
        request = getattr(self.context, 'REQUEST', None)
        formatter = TranslatingFormatter(format, request=request)
        # and plug things together
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)
        self.log = log

    def reap_logger(self):
        """return the log output"""
        # rewind the stream
        self.log_stream.seek(0)
        # read the stream into a string
        log = self.log_stream.read()
        # get rid of the stream
        self.log_stream.close()
        # and return return the log
        return log

    def dry_run(self):
        """Dry Run: Returns Log-Information.
        """
        # Just to have the posibility to reset
        self.harvester._graph = None
        self.harvester._rdfstore = None

        self.log.info(u'starting harvestdry run')
        uri = self.harvester.url

        msg = _(
            u'Reading {kind} file {uri}',
            mapping={'kind': self.serialize_format, 'uri': uri},
        )
        self.log.info(msg)

        visitor = DCATVisitor()

        # start on the top nodes
        self.top_nodes(visitor)

        msg = _(
            u'{kind} file {uri} read succesfully',
            mapping={'kind': self.serialize_format, 'uri': uri},
        )
        self.log.info(msg)
        self.log.info(u'Harvesting real run successfully')

        return visitor.scribe.html_log()

    def top_nodes(self, visitor):
        """Find top nodes: Catalogs or datasets"""
        # check if we get a base object
        if self.harvester.base_object:
            self.context = content.get(UID=self.harvester.base_object)
            self.struct_class = StructDCATDataset
        else:
            self.context = portal.get()
            self.struct_class = StructDCATCatalog

        struct = self.struct_class(self.harvester)
        # Get Mapping from the harvester
        if struct.rdf_type in self.harvester.mapper:
            query = self.harvester.mapper[struct.rdf_type]
            bindings = {'o': struct.rdf_type}
        else:
            # Since we have no rdf_parent we have to look for types of nodes
            query = QUERY_A
            bindings = {'o': struct.rdf_type}
        res = self.graph.query(query, initBindings=bindings)
        # Todo : handle more than one hit
        catalog = res.bindings[0]['s']

        struct = self.struct_class(self.harvester)
        args = {
            'structure': struct,
        }
        node = Node(**args)
        visitor.push_node(node)

        self.crawl(
            visitor,
            context=self.context,
            rdf_node=catalog,
            target_struct=self.struct_class,
        )

    def scribe(self, level=None, msg=None, **kwargs):
        message = _(msg, mapping=kwargs)
        getattr(self.log, level)(message)

    def handle_list(self, visitor, res, **kwargs):
        obj_data = kwargs['obj_data']
        field_name = kwargs['field_name']
        field = kwargs['field']
        context = kwargs['context']

        obj_data[field_name] = []
        for i in res.bindings:
            # If the field is a Literal we simply store it.
            if field['object'] == StructRDFSLiteral:
                obj_data[field_name].append(i['o'])
                visitor.end_node(**kwargs)

            # if not we have to create a sub object recursively
            else:
                node = visitor.end_node(**kwargs)
                visitor.push_node(node)
                sub = self.crawl(
                    visitor,
                    context=context,
                    rdf_node=i['o'],
                    target_struct=field['object'],
                )
                obj_data[field_name].append(sub)

            visitor.scribe.write(
                level='info',
                msg=u'{type} object {obj}: attribute {att}:= {val}',
                val=i['o'],
                obj=kwargs['rdf_node'],
                type=kwargs['struct'].rdf_type,
            )

    def handle_dict(self, visitor, res, **kwargs):
        obj_data = kwargs['obj_data']
        field_name = kwargs['field_name']
        field = kwargs['field']

        obj_data[field_name] = {}
        for i in res.bindings:
            # special handling of literals without language
            if not ('o1' in i):
                obj_data[field_name][self.def_lang] = unicode(i['o'])
                visitor.scribe.write(
                    level='info',
                    msg=u'{type} object {obj}: attribute {att}:= {val}',
                    val=i['o'],
                    att=field['predicate'],
                    obj=kwargs['rdf_node'],
                    type=kwargs['struct'].rdf_type,
                )
            else:
                obj_data[field_name][i['o1']] = unicode(i['o2'])
                visitor.scribe.write(
                    level='info',
                    msg=u'{type} object {obj}: attribute {att}:= {val}',
                    val=str(i['o1']) + ':' + str(i['o1']),
                    att=field['predicate'],
                    obj=kwargs['rdf_node'],
                    type=kwargs['struct'].rdf_type,
                )

            visitor.end_node(**kwargs)

    def properties(self, visitor, **kwargs):
        """At first we run over the fields and references only, to collect
        the data necessary to construct the CT instance.
        With the contained instances will be dealed if the CT instance
        is constructed"""

        obj_data = kwargs['obj_data']
        context = kwargs['context']

        field_and_references = kwargs['struct'].fields_and_referenced

        for field_name, field in field_and_references.items():

            params = kwargs.copy()
            params['field_name'] = field_name
            params['field'] = field
            params['obj_data'] = obj_data
            params['context'] = context

            self.property(visitor, **params)

    def property(self, visitor, **kwargs):

            field = kwargs['field']
            field_name = kwargs['field_name']
            obj_data = kwargs['obj_data']
            context = kwargs['context']

            visitor.scribe.write(
                level='info',
                msg=u'{type} object {obj}: '
                    u'searching {imp} attribute {att}',
                att=field['predicate'],
                imp=field['importance'],
                obj=kwargs['rdf_node'],
                type=kwargs['struct'].rdf_type,
            )
            # query for an attibute
            query = QUERY_ATT

            # query the entity manager for replacement entities
            if kwargs['struct'].rdf_type == FOAF.Agent and \
                    field_name == 'foaf_name':
                pass

            params = kwargs.copy()

            token = kwargs['struct'].field2token(field_name, field)
            if token in self.mapping_dexterity:
                uid = self.mapping_dexterity[token]
                obj = content.get(UID=uid)
                obj_data[field_name] = obj
                params['node_type'] = NT_DX_DEFAULT
                node = visitor.end_node(**params)
                visitor.push_node(node)
                self.crawl_dx(
                    visitor,
                    context=obj,
                    target_struct=field['object'],
                )
                return

            if token in self.mapping_default:
                obj_data[field_name] = self.mapping_default[token]
                params['node_type'] = NT_DEFAULT
                visitor.end_node(**params)
                return

            if token in self.mapping_sparql:
                params['node_type'] = NT_SPARQL
                query = self.mapping_sparql[token]
            # Query the RDF db. Subject is the node we like
            # to construct. Predicate
            # is the attribute we like to find in the RDF
            bindings = {
                's': kwargs['rdf_node'],
                'p': field['predicate'],
            }
            res = self.graph.query(query, initBindings=bindings)

            # Dealing with required fields not delivered
            if len(res) == 0:
                if field['importance'] == IMP_REQUIRED:
                    visitor.scribe.write(
                        level='error',
                        msg=u'{type} object {obj}: required '
                            u'attribute {att} not found',
                        att=field['predicate'],
                        obj=kwargs['rdf_node'],
                        type=kwargs['struct'].rdf_type,
                    )
                    params['status'] = NS_ERROR
                    visitor.end_node(**params)
                else:
                    visitor.scribe.write(
                        level='warn',
                        msg=u'{type} object {obj}: {imp} '
                            u'attribute {att} not found',
                        att=field['predicate'],
                        imp=field['importance'],
                        obj=kwargs['rdf_node'],
                        type=kwargs['struct'].rdf_type,
                    )
                    params['status'] = NS_WARNING
                    visitor.end_node(**params)
                return
            else:
                # dealing with list like fields
                if field['type'] == list:
                    self.handle_list(visitor, res, **params)

                # dealing with dict like fields aka Literals
                elif field['type'] == dict:
                    self.handle_dict(visitor, res, **params)
                # Iten/list collision checking. Attribute is Item in DCATapded,
                # but a list is delivered.
                elif len(res) > 1:
                    visitor.scribe.write(
                        level='error',
                        msg=u'{type} object {obj}: '
                            u'attribute {att} to many values',
                        att=field['predicate'],
                        obj=kwargs['rdf_node'],
                        type=kwargs['struct'].rdf_type,
                    )
                    # Todo: Error handling
                    return
                # Simple case of a single item
                else:
                    # If the field is a Literal we simply store it.
                    if field['object'] == StructRDFSLiteral:
                        obj_data[field_name] = res.bindings[0]['o']
                        visitor.end_node(**params)
                    # if not we have to create a sub object recursively
                    else:
                        node = visitor.end_node(**params)
                        visitor.push_node(node)
                        sub = self.crawl(
                            visitor,
                            context=context,
                            rdf_node=res.bindings[0]['o'],
                            target_struct=field['object'],
                        )
                        obj_data[field_name] = sub
                    visitor.scribe.write(
                        level='info',
                        msg=u'{type} object {obj}: attribute {att}:= {val}',
                        val=obj_data[field_name],
                        att=field['predicate'],
                        obj=kwargs['rdf_node'],
                        type=kwargs['struct'].rdf_type,
                    )

    def contained(self, visitor, **kwargs):
        """At first we run over the fields and references only, to collect
        the data necessary to construct the CT instance.
        With the contained instances will be dealed if the CT instance
        is constructed"""

        struct = kwargs['struct']
        rdf_node = kwargs['rdf_node']
        obj = kwargs['obj']

        # query for an attibute
        query = QUERY_ATT
        #   Handle the contained objects
        for field_name, field in struct.contained.items():
            # Todo : query the entity mapper
            # if struct.rdf_type in self.harvester.mapper:
            #                query = self.harvester.mapper[struct.rdf_type]
            visitor.scribe.write(
                level='info',
                msg=u'{type} object {obj}: searching contained {att}',
                att=field['predicate'],
                obj=kwargs['rdf_node'],
                type=kwargs['struct'].rdf_type,
            )

            # Query the RDF db. Subject is still the rdf_node
            # Predicate is the attribute we like to find in the RDF
            bindings = {
                's': rdf_node,
                'p': field['predicate'],
            }
            res = self.graph.query(query, initBindings=bindings)

            for i in res.bindings:
                params = {
                    'field': field,
                    'field_name': field_name,
                    'rdf_node': i['o'],
                    'struct': struct,
                }
                node = visitor.end_node(**params)
                visitor.push_node(node)

                self.crawl(
                    visitor,
                    context=obj,
                    rdf_node=i['o'],
                    target_struct=field['object'],
                )
                visitor.scribe.write(
                    level='info',
                    msg=u'Crawling to sub obj {obj} of type {type} '
                        u'attribute {att}',
                    att=field['predicate'],
                    obj=kwargs['rdf_node'],
                    type=kwargs['struct'].rdf_type,
                )

    def crawl(
        self,
        visitor,
        target_struct=None,
        context=None,
        rdf_node=None,
    ):
        """Analyse the RDF structure"""

        # Activate the struct
        struct = target_struct(self.harvester)

        # here we collect the data to generate our DX object
        obj_data = {}

        # Go for the properties of the current node
        self.properties(
            visitor,
            context=context,
            rdf_node=rdf_node,
            struct=struct,
            obj_data=obj_data,
        )

        try:
            # Create an instance of the node as dexterity object
            try:
                title = unicode(obj_data[struct.title_field].items()[0][1])
            except KeyError:
                raise RequiredPredicateMissing
            obj = content.create(
                context,
                target_struct.portal_type,
                title=title,
                **obj_data)
            obj.reindexObject()
            visitor.scribe.write(
                level='info',
                msg=u'{type} dxobject {obj} created at {context}',
                context=context.virtual_url_path(),
                obj=rdf_node,
                type=struct.rdf_type,
            )
        except RequiredPredicateMissing:
            visitor.scribe.write(
                level='error',
                msg=u'{type} dxobject {obj} cannot be created at {context}',
                context=context.virtual_url_path(),
                obj=rdf_node,
                type=struct.rdf_type,
            )
            obj = None
            title = None

        self.contained(
            visitor,
            context=context,
            rdf_node=rdf_node,
            struct=struct,
            obj_data=obj_data,
            obj=obj,
        )
        node = visitor.pop_node()
        node.title = title
        return obj

    def crawl_dx(
        self,
        visitor,
        target_struct=None,
        context=None,
        rdf_node=None,
    ):

        struct = target_struct(context)
        field_and_references = struct.fields_and_referenced
        obj_data = {}

        for field_name, field in field_and_references.items():

            params = {
                'field': field,
                'field_name': field_name,
                'struct': target_struct,
            }
            # If the field is a Literal we simply store it.
            if field['object'] == StructRDFSLiteral:
                obj_data[field_name] = getattr(context, field_name)
                visitor.end_node(**params)
            # if not we have to create a sub object recursively
            else:
                node = visitor.end_node(**params)
                visitor.push_node(node)
                sub = self.crawl_dx(
                    visitor,
                    context=context,
                    target_struct=field['object'],
                )
                obj_data[field_name] = sub
            visitor.scribe.write(
                level='info',
                msg=u'{type} object {obj}: attribute {att}:= {val}',
                val=obj_data[field_name],
                att=field['predicate'],
            )

        node = visitor.pop_node()
        node.title = context.title

    def parse_dcat_data(self):
        """Parsing the data in respect to the dcat ap.de diagram
        """
        self.log.info(u'Parsing for dcat information')
        uri = self.harvester.url

        msg = _(
            u'Reading {kind} file {uri} into rdflib',
            mapping={'kind': self.serialize_format, 'uri': uri},
        )
        self.log.info(msg)

        self.scribe = Scribe()
        visitor = DCATVisitor()

        # start on the top nodes
        self.top_nodes(visitor)

        self.log.info(u'DCAT parsed successfully')

        return visitor.to_cytoscape()

    def parse_input_data(self):
        """Parsing the data with focus on the input data
        """
        self.log.info(u'Parsing for input information')
        uri = self.harvester.url

        msg = _(
            u'Reading {kind} file {uri} into rdflib',
            mapping={'kind': self.serialize_format, 'uri': uri},
        )
        self.log.info(msg)

        self.scribe = Scribe()
        visitor = InputVisitor()

        # start on the top nodes
        self.top_nodes(visitor)

        self.log.info(u'Input data parsed successfully')

        for line in visitor.scribe.read():
            self.log.info(line)

        return visitor.to_cytoscape()

    def get_preview(self, query, bindings={}):
        """
        Preview for sparqle_query

        if url and rdf_format are given and different to self.harvester
        we make a temporary graph
        """
        preview = _(u'Result: ')
        try:
            res = self.graph.query(query, initBindings=bindings)
        except ParseException:
            preview += _(u'Wrong Syntax')
        except SAXParseException:
            preview += _(u'Could not read source.')
        except ValueError:
            preview += _(u'Did not find correct parameters to request data.')
        except TypeError:
            preview += _(u'Did not find correct parameters to request data.')
        else:
            preview += safe_unicode(vkb.xml(res.serialize()))
        if preview and len(preview) > MAX_QUERY_PREVIEW_LENGTH:
            preview = preview[:MAX_QUERY_PREVIEW_LENGTH] + '...'
        return preview
