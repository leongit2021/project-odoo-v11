# -*- coding: utf-8 -*-
{
    'name': "Report Sales: Quotation, Order",

    'summary': """
        1. Report Sales: QU vs SO at PTI.  
        2. Report Div-21 Sparepart.
        3. Report Due Delivery Div-21 Sparepart.
        4. Dashboard Detail Spare Part Div 21.
        5. SKEP/PIB
    """,

    'description': """
        Long description of module's purpose
    """,

    'author': "ati",
    'website': "http://www.ati.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','sale','portal','product','ati_product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sqo_state.xml',
        'wizard/show_list_item_so_view.xml',
        'wizard/show_skep_pib_wizard_view.xml',
        'views/skep_pib_view.xml',
        'views/sale_view.xml',
        'wizard/sales_quotation_order_view.xml',
        'wizard/sales_sparepart_view.xml',
        'wizard/sales_delivery_order_view.xml',
        'wizard/dashboard_detail_sparepart_div21_view.xml',
        'views/product_template_view.xml',
        'wizard/export_import_product_wizard.xml',
        'wizard/management_report_view.xml',
        'reports/reports.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}