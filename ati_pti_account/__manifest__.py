# -*- coding: utf-8 -*-
{
    'name': "Custom Account",

    'summary': """
    1. Search Move -> Search Transaksi
    2. Column Label -> Diisi dengan data Customer PO/SO
    3. Arrange Debit/Credit --> Di Journal disusun debit/credit.
    4. Gl By Range Account
    5. Margin Analysis
    6. Faktur Pajak Single Line - Report
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
    'depends': ['base','account','iwesabe_reports_journal_entry','account_finreport','ati_accounting','stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_search_view.xml',
        'views/account_move_view.xml',
        'views/account_invoice_view.xml',
        'views/report_faktur_pajak_single_line.xml',
        'reports/journal_entries_report.xml',
        'wizard/account_gl_by_range_view.xml',
        'wizard/account_margin_analysis_view.xml',
        'reports/reports.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}