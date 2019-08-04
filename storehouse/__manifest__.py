# -*- coding: utf-8 -*-
{
    'name': "storehouse",

    'summary': """###""",

    'description': """
        Long description of module's purpose
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
    'depends': ['base','report','web'],

    # always loaded
    'data': [
        'security/storehouse_groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/box_inventory.xml',
        #'views/products_virtual.xml',
        'views/templates.xml',
    ],
    'qweb': ['static/src/xml/create_local_order_button.xml'],
    # only loaded in demonstration mode
    #'demo': [
    #    'demo/demo.xml',
    #],
}