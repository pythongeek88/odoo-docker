# -*- coding: utf-8 -*-
from odoo import http

class HouzzConnection(http.Controller):
    @http.route('/houzz_connection/houzz_connection/', auth='public')
    def index(self, **kw):
        return "Hello, world"

#     @http.route('/houzz_connection/houzz_connection/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('houzz_connection.listing', {
#             'root': '/houzz_connection/houzz_connection',
#             'objects': http.request.env['houzz_connection.houzz_connection'].search([]),
#         })

#     @http.route('/houzz_connection/houzz_connection/objects/<model("houzz_connection.houzz_connection"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('houzz_connection.object', {
#             'object': obj
#         })