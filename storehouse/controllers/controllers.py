# -*- coding: utf-8 -*-
from odoo import http

# class Storehouse(http.Controller):
#     @http.route('/storehouse/storehouse/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/storehouse/storehouse/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('storehouse.listing', {
#             'root': '/storehouse/storehouse',
#             'objects': http.request.env['storehouse.storehouse'].search([]),
#         })

#     @http.route('/storehouse/storehouse/objects/<model("storehouse.storehouse"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('storehouse.object', {
#             'object': obj
#         })

class Storehouse(http.Controller):
	@http.route('/storehouse/storehouse/objects/<model("storehouse.product"):obj>/', auth='public')
	def object(self, obj, **kw):
		return http.request.render('storehouse.object', {
			'object': obj
			})
