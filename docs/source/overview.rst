========
Overview
========

Conception
==========

Data flow
---------

PKAN features three major operations :

- Harvesting
- Creation
- Marshalling (being harvested)

and all combinations which is called curation. An addition feature is editing which is only available in a limited fashion.
The following figure shows the operation and the overall data flow due to the operations.

- Harvesting: The external datasources A and B were harvested by PKAN.
- Creation: The lokal data L, K, M is created by the PKAN user utilzing web formulars.
- Marshalling: The data (harvested and created) can be arranged, combined and edited to form new semantic web datasources

For example the datasource A is harvested and then edited. Afterwards it is aggregated with the local dataset M to form a new datasource (Biggest red box).

.. figure:: ../figures/flow.*

   Data flow

Harvesting
^^^^^^^^^^
The harvester works in multiple steps to clean the data.

.. figure:: ../figures/harvesting.*

   Harvesting Overview

1. Valid RDF is read into a temporary RDF Store.
2. With the help of the Entity Mapping the information for creating the object ist collected and reordered to dcat-ap.de objects/attributes.
3. With the help of a Source Level Adapter missing values can be added or wrong values can be changed/deleted.
4. With the help of a Value Mapping special values can be replaced by exisiting Plone Objects.
5. All data is validated. Validation log will be printed in DRY_RUN-Mode.
6. Only valid objects will be created or updated in triple store and Plone ZODB. Missing objects will be marked as deprecated. Objects which are deprecated for more than 30 days will be deleted.

Plone Workflow
^^^^^^^^^^^^^^

You can add, edit and delete data in Plone. Deleting objects is risky and can be only done by the Site Manager.
All changes get active during marshalling. There is no synchronisation between the Plone ZODB and the Triple Store.

Marshalling
^^^^^^^^^^^

TheThe Marshaller walks over all Plone Objects. It takes the existent Plone objects as base and just adds additional rdf attributes from triple storage.
If an object only exists in triple store, it will be ignored. Because only existing in triple store means it was deleted on the Plone Page.

Building blocks
---------------

PKAN consists of several building blocks:

- The foundation is the application server Plone with its ZODB Object database.
- The web frontend consists of mostly autogenerated formulars for the entities and the usual Plone user interface for authoring.
- The harvesting module has configuration views to determine the harvesting source and other harvesting parameters. Additional entity mapping views can be used to define a mappign of non DCAT data to DCAT-AP.de.
- The marshalling module adds export functionality like to-RDF-Links at the documents.
- The SPARQL-Endpoint as well as the harvesting module operate on the triple store which acts as a second database. A synchronisation between the ZODB data and the triple does not take place. For the SPARQL Endpoint the result of a full site marshalling process is stored in triple store.
 [see synchronisation, see user manual]

.. figure:: ../figures/PKAN-blocks.*

   Block diagram


Operation
=========


.. _overview_figure_acceptance-rules-org2:

Acceptance procedure for incoming entities
-------------------------------------------

On a simple example we will illustrate the function of PKAN as editing gateway/gatekeeper for semantic web information.
DCAT-AP.de utilizes two entities dcat:Catalog and foaf:Agent to define the dct:Publisher predicate.

.. figure:: ../figures/uml_cat_pub.*

   UML diagram

This UML diagram reads: There is a 1:1 relation between a dcat:Catalog entity and a foaf:Agent entity which defines dct:Publisher.
The publisher of the catalog is the entity denoted by the foaf:Agent base class. Important is here the fact that the publisher entity
has not to be strict a foaf:Agent instance. Any instance that derives from foaf:Agent is sufficient.

PKAN will now test three sets of catalog, publisher candidates for compliance with DCAT-AP.de aka the UML diagram above. The incoming dcat:Catalog is always in order.

.. figure:: ../figures/acceptance-rules-hulk.*

   First: Incoming the Hulk als Publisher.

PKAN checks the namespace of the incoming pulisher instance 'hulk'. But there is no namespace definition to be found in terms of a OWL-definition of the hulk namespace
in the internet. So PKAN cannot determine is the entity hulk:Person is derived from foaf:Agent. PKAN does not accept this publisher entity.

.. figure:: ../figures/acceptance-rules-org1.*

   Second: Incoming an organization.

Now we have an org:Organization entity for the dct:publisher. PKAN looks up the `org:namespace <https://www.w3.org/TR/vocab-org/#class-organization>`_ and
finds out (here PKAN acts as a reasoner) that org:Organization is a subclass of foaf:agent. So we have a entity of the correct type.

Now PKAN checks for the attributes of the entity. PKAN learns from the org: OWL that org:Organziation does not specify an additional mandatory attributes for org:Organization.
The base class foaf:agent has to have as minimal requirement a foaf:name attribute. But this requirement is not fullfilled. Also the publisher entity will not be accepted.

.. figure:: ../figures/acceptance-rules-org2.*

   Third: Incoming an other organization.

In this final case everything is correct: The type of the entity and all required attributes are given. The entity will be accepted.


Separation of the incoming data
--------------------------------

PKAN is not able to validate all possible input data it harvests. Imagine an incoming publisher entity like this::

    <foaf:Agent>
       <foaf:name>Historic Publishing Ltd.</foaf:name>
       <... here comes the History of the HP Ltd. in fine detail and half the wikipedia ... >
    </foaf:Agent>

The main purpose of PKAN is to enforce its norms (currently discussed DCAT-AP.de). So anything about the "History of HP Ldt".
is not relevant to answer: Is this correct DCAT-AP.de. This is some sort of minimal checking approach. We check if the norm is fullfilled by the
data then everything else (as stupid it may be) is accepted.

But this approach also leads to two kinds of information. The information that strictly passes the norm (DCAT-AP.de) and the information that is
additional to the norm, e.g. the history of the famous "HP Ltd. publishers". Both parts of the data have their value so neither should be neglected.

The norm conform part goes into the ZODB in form of the 22 entity content-types and can further be edited etc. But more so these 22 content types act
as handles to grab the data and reshape it. [see curatoring]

The second part one can denote the residuum to the norm. But often this residuum may be larger than the norm part. Because of this
and out of practical considerations we do not derive this second part at all. The whole incoming data is stored in the triple store - as is - for further usage.
The simplest of these use cases is the most often: to be marshalled unmodified upstream.


Storage representation of incoming entities
-------------------------------------------

The storage of PKAN is twofold.

- The ZODB stores only that parts of the entities that are strictly defined in DCAT-AP.de norm.

- All the other incoming data goes right into the triple store.

The following example from the last topics may illustrate the data separation

.. figure:: ../figures/acceptance-rules-storage.*

   Storage of entities.

As you can see the entities from :ref:`_overview_figure_acceptance-rules-org2` are stored directly into the triple store.
The data stored into the ZODB looks a bit different. The dcat:Catalog is the same. But the org:Organzation has become a
foaf:Agent and lost nearly all its attributes. But this is correct since the norm only knows foaf:Agents to deal with.

The most important detail in this diagram are the orange dotted lines. These lines indicate the association between the ZODB-Entities
with their counterparts in the triple store. The association between ZODB and Tripel store is organized by the UID of the ZOBD-Entity.
The incoming entities that go to the triple store were tagged with the predicate pkan:ZODBUID and the UID of the ZODB Entity they belong to.



