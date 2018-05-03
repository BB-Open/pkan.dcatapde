# -*- coding: utf-8 -*-

from pkan.dcatapde import constants
from pkan.dcatapde import testing
from pkan.dcatapde.content.vcard_kind import IVCARDKind
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.dexterity.interfaces import IDexterityFTI
from zope.component import createObject
from zope.component import getUtility
from zope.component import queryUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.interfaces import IVocabularyTokenized

import unittest


class TestVCARDKindVocabulary(unittest.TestCase):
    """Validate the `SKOSConceptScheme` vocabulary."""

    layer = testing.INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.item1 = api.content.create(
            container=self.portal.get(constants.FOLDER_VCARD_KIND),
            type=constants.CT_VCARD_KIND,
            id='contact-1',
            dct_title={u'en': u'Concept Scheme 1'},
        )
        self.item2 = api.content.create(
            container=self.portal.get(constants.FOLDER_VCARD_KIND),
            type=constants.CT_VCARD_KIND,
            id='contact-2',
            dct_title={u'en': u'Concept Scheme 2'},
        )

    def test_vocabulary(self):
        """Validate the vocabulary."""
        vocab_name = 'pkan.dcatapde.vocabularies.VCARDKind'
        factory = getUtility(IVocabularyFactory, vocab_name)
        self.assertTrue(IVocabularyFactory.providedBy(factory))

        vocabulary = factory(self.portal)
        self.assertTrue(IVocabularyTokenized.providedBy(vocabulary))

        self.assertEqual(len(vocabulary), 2)
        self.assertEqual(
            vocabulary.getTerm(self.item1.UID()).title,
            self.item1.Title(),
        )
        self.assertEqual(
            vocabulary.getTerm(self.item2.UID()).title,
            self.item2.Title(),
        )


class VcardKindIntegrationTest(unittest.TestCase):
    """Validate the `dct_location` CT."""

    layer = testing.INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

    def test_schema(self):
        fti = queryUtility(
            IDexterityFTI,
            name=constants.CT_VCARD_KIND,
        )
        schema = fti.lookupSchema()
        self.assertEqual(IVCARDKind, schema)

    def test_fti(self):
        fti = queryUtility(
            IDexterityFTI,
            name=constants.CT_VCARD_KIND,
        )
        self.assertTrue(fti)

    def test_factory(self):
        fti = queryUtility(
            IDexterityFTI,
            name=constants.CT_VCARD_KIND,
        )
        factory = fti.factory
        obj = createObject(factory)
        self.assertTrue(IVCARDKind.providedBy(obj))

    def test_adding(self):
        setRoles(self.portal, TEST_USER_ID, ['Contributor'])
        obj = api.content.create(
            container=self.portal.get(constants.FOLDER_VCARD_KIND),
            type=constants.CT_VCARD_KIND,
            id='sample-location',
        )
        self.assertTrue(IVCARDKind.providedBy(obj))