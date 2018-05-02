# -*- coding: utf-8 -*-
"""VCARDKind Content Type."""
from pkan.dcatapde import _
from pkan.dcatapde import constants
from pkan.dcatapde import i18n
from pkan.dcatapde.content.base import DCATMixin
from pkan.dcatapde.content.base import IDCAT
from plone.dexterity.content import Container
from plone.schema import Email
from plone.supermodel import model
from ps.zope.i18nfield.field import I18NText
from ps.zope.i18nfield.field import I18NTextLine
from ps.zope.i18nfield.fieldproperty import I18NTextProperty
from zope.interface import implementer

import zope.schema as schema


class IVCARDKind(model.Schema, IDCAT):
    """Marker interface and Dexterity Python Schema for VCARDKind."""

    # Fieldsets
    # -------------------------------------------------------------------------

    # Mandatory
    # -------------------------------------------------------------------------
    vcard_fn = I18NTextLine(
        required=True,
        title=i18n.LABEL_DCT_TITLE,
    )

    dct_description = I18NText(
        required=True,
        title=i18n.LABEL_DCT_DESCRIPTION,
    )

    vcard_hasEmail = schema.List(
        required=False,
        title=_(u'Emails'),
        value_type=Email(
            title=_(u'Email'),
        ),
    )
    vcard_hasTelephone = schema.List(
        required=False,
        title=_(u'Phone Numbers'),
        description=_(u'Add one number per Line'),
        value_type=schema.TextLine(
            title=_(u'Phone Number'),
        ),
    )

    vcard_hasURL = schema.URI(
        required=False,
        title=_(u'Contact Formular'),
    )

    vcard_Fax = schema.List(
        required=False,
        description=_(u'Add one number per Line'),
        title=_(u'Fax Numbers'),
        value_type=schema.TextLine(
            title=_(u'Fax Number'),
        ),
    )


@implementer(IVCARDKind)
class VCARDKind(Container, DCATMixin):
    """VCARDKind Content Type."""

    portal_type = constants.CT_VCARD_KIND
    content_schema = IVCARDKind
    _namespace = 'vcard'
    _ns_class = 'kind'

    vcard_fn = I18NTextProperty(IVCARDKind['vcard_fn'])
    dct_description = I18NTextProperty(IVCARDKind['dct_description'])

    def Title(self):
        return self.title_from_title_field()

    def Description(self):
        return self.desc_from_desc_field()
