# -*- coding: utf-8 -*-
{
    'name': "Document",

    'summary': """
        Store default file for:
        1. Import SKEP
        2. Import DO
        3. Import PLB
    """,

    'description': """
        Store template default. 
    """,

    'author': "ATI",
    'website': "http://www.ati.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','ati_product','ati_pti_sales'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        'views/document_view.xml',
        'wizard/document_wizard_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}