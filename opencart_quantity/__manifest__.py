# -*- coding: utf-8 -*-
{
    'name': "opencart_quantity",

    'summary': """Opencart Quantity""",

    'description': """
        Opencart Quantity
    """,

    'author': "###",
    'website': "###",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base','storehouse'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        #'views/cron.xml', ------------------ UNCOMMENT IT WHEN YOU'VE TESTED IT LOCALLY!
    ],
    # only loaded in demonstration mode
    #'demo': [
    #    'demo/demo.xml',
    #],
}