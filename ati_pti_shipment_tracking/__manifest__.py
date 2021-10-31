# -*- coding: utf-8 -*-
{
    'name': "Shipment ",

    'summary': """
        1. Sparepart , Logistics, Principal, Forwarder, Transporter
    
    """,

    'description': """
        Long description of module's purpose
    """,

    'author': "ATI",
    'website': "http://www.ati.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Shipment ',
    'version': '0.1',
	'sequence'  : 51,

    # any module necessary for this one to work correctly
    'depends': ['base','mail','product','purchase','stock','ati_product','delivery','ati_pti_sales','stock_dev','hr_holidays'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        # 'views/views.xml',
        # 'views/templates.xml',
        # 'data/packing_list_data.xml',
        # 'data/mode_transport_data.xml',
        'views/menu.xml',
        'views/packing_list_view.xml',
        'views/packing_list_type_view.xml',
        'views/mode_transport_view.xml',
        'views/departure_arrival_view.xml',
        'views/summary_nor_goods_view.xml',
        'data/nor_goods.xml',
        'wizard/nor_validate_wizard_view.xml',
        'views/nor_goods_view.xml',
        'views/purchase_view.xml',
        'wizard/list_pickup_goods_wizard_view.xml',
        'wizard/list_shipping_instruction_wizard_view.xml',
        # 'wizard/package_number_wizard_view.xml',
        'wizard/list_commercial_view.xml',
        'views/pickup_goods_view.xml',
        'views/awb_bl_view.xml',
        'wizard/list_bc_goods_view.xml',
        'data/bc_type.xml',
        'views/bc_type.xml',
        'views/custom_clearance_view.xml',
        'views/stock_view.xml',
        'views/auto_check_goods_readiness_view.xml',

        'views/views basic_module.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
	'application': True,
}