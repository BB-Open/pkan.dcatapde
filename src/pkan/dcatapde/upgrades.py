# -*- coding: utf-8 -*-
"""Upgrades."""

from plone.app.upgrade.utils import loadMigrationProfile


def reload_gs_profile(context):
    loadMigrationProfile(
        context,
        'profile-pkan.dcatapde:default',
    )
