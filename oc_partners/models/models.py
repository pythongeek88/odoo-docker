# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging, requests, json, ast
_logger = logging.getLogger(__name__)

class opencart(models.Model):
    _name = 'opencart.settings'

    id = fields.Char()
    name = fields.Char()
    customer = fields.Many2one("storehouse.customer")
    #app_id = fields.Char()
    user_name = fields.Char()
    key = fields.Text()
    url = fields.Char() # Here we have url for login!
    status = fields.Boolean(default=False)
    upload_status = fields.Boolean(default=False)

    @api.multi
    def check_connection(self):
        for opencart in self:
            
            try:

                s = requests.Session()
                r = s.post(opencart.url + '/index.php?route=api/login', data={'username':opencart.user_name, 'key':opencart.key})
                content = json.loads(r.content)
                s.close()
                msg = ''

                if 'success' in content:
                    msg += '<br>%s<br>' % (content['success'])
                if 'token' in content:
                    msg += '<br> token: %s<br>' % (content['token'][0:7] + '*' * (int(len(content['token'])) - 7) )

            except Exception:
                msg = '<br>%s<br>' % ('CONNECTION ERROR!')
                msg += '<br>%s<br>' % (content)

            return {
                'name': ' Info ',
                'type': 'ir.actions.act_window', 
                'view_type': 'form', 
                'view_mode': 'form',
                'res_model': 'storehouse.info_message',
                'target': 'new',
                'context': {
                    'default_html': msg,
                    }
            }



    @api.multi
    def get_products_info(self, data_token, url):

        s = requests.Session()


        if 'token' in data_token:
            #print(data['token'])
            token = data_token['token']
            url_to_get_products = str(url) +'/index.php?route=api/custom/products&token=' + str(token)
            products = s.post(url_to_get_products)
            url_to_get_products_with_options = str(url) +'/index.php?route=api/custom/productswithoptions&token=' + str(token)
            products_with_options = s.post(url_to_get_products_with_options)            
        else:
            return "You don't have a token!"

        return products.content, products_with_options.content

    # @api.multi
    # def get_product_options_info(self, data_token, url, product_id):

    #     s = requests.Session()


    #     if 'token' in data_token:
    #         #print(data['token'])
    #         token = data_token['token']
    #         url_to_get_product_options = str(url) +'/index.php?route=api/custom/productoptions&token=' + str(token) + '&product_id=' + str(product_id)
    #         product_options = s.post(url_to_get_product_options)         
    #     else:
    #         return "You don't have a token!"

    #     return product_options.content
    @api.multi
    def get_product_options_info(self, data_token, url, product_id):

        s = requests.Session()


        if 'token' in data_token:
            #print(data['token'])
            token = data_token['token']
            url_to_get_product_options = str(url) +'/index.php?route=api/custom/productoptionslist&token=' + str(token) + '&product_id=' + str(product_id)
            product_options = s.post(url_to_get_product_options)         
        else:
            return "You don't have a token!"

        return product_options.content

    @api.multi
    def main_opencart_job_products(self):
        _logger.debug('--------- main_opencart_job_products ----------')
        opencart_settings_ids = self.env['opencart.settings'].search([
            ('status', '=', True)
            ])

        for opencart in opencart_settings_ids:
            if opencart.status:

                key = opencart.key
                username = opencart.user_name
                url = str(opencart.url) + '/index.php?route=api/login'
                s = requests.Session()
                r = s.post(url, data={'username':username, 'key':key})
                data_token = json.loads(r.content)

                # check_statuses = ['Pending'] #'Processed', 'Processing', 'Expired', 
                # for status in check_statuses:
                #     _logger.debug('--------- opencart check_status %r   ----------', status)
                #     _logger.debug('--------- shop is %r   ----------', opencart.customer.name)
                #     opencart.check_orders_status(status, opencart.customer, data_token, opencart.url)

                _logger.debug('--------- opencart %r BEGIN ----------', opencart.customer.name)
                products_data_json = opencart.get_products_info(data_token, opencart.url)
                # _logger.debug(products_data_json[0])
                # _logger.debug(products_data_json[0])
                # _logger.debug('################################')
                # _logger.debug(products_data_json[1])
                #_logger.debug(products_data_json)

                #return False

                null_values_replaced = products_data_json[0].replace('null', '""')

                dict_from_str_0 = ast.literal_eval(null_values_replaced)

                clean_result_0 = dict_from_str_0['success']['products']
                # _logger.debug(type(clean_result_0))

                products_with_quantity_ids = []

                for item in clean_result_0:
                    id_model_quantity = {}
                    id_model_quantity['product_id'] = item
                    id_model_quantity['model'] = clean_result_0[item]['model']
                    if int(clean_result_0[item]['quantity']) < 0:
                        quantity_can_not_be_negative = '0'
                        id_model_quantity['quantity'] = quantity_can_not_be_negative
                    else:
                        id_model_quantity['quantity'] = clean_result_0[item]['quantity']

                    # _logger.debug(item)
                    # _logger.debug(clean_result_0[item]['model'])
                    # _logger.debug(clean_result_0[item]['quantity'])
                    # _logger.debug(item['product_id'])
                    # for key in item:
                    #     _logger.debug(key)
                    products_with_quantity_ids.append(id_model_quantity)
                # _logger.debug('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
                # _logger.debug(products_with_quantity_ids)

                dict_from_str_1 = ast.literal_eval(products_data_json[1].replace('null', '""'))
                # result={"success":{"products_with_options":[{"product_id":"140"},{"product_id":"141"},{"product_id":"143"},{"product_id":"143"},{"product_id":"144"},{"product_id":"145"},{"product_id":"147"},{"product_id":"148"},{"product_id":"150"},{"product_id":"151"},{"product_id":"152"},{"product_id":"154"},{"product_id":"155"},{"product_id":"157"},{"product_id":"177"},{"product_id":"186"},{"product_id":"199"},{"product_id":"203"},{"product_id":"206"},{"product_id":"207"},{"product_id":"220"},{"product_id":"221"},{"product_id":"227"},{"product_id":"228"},{"product_id":"231"},{"product_id":"232"},{"product_id":"233"},{"product_id":"236"},{"product_id":"237"},{"product_id":"237"},{"product_id":"238"},{"product_id":"242"},{"product_id":"244"},{"product_id":"245"},{"product_id":"246"},{"product_id":"248"},{"product_id":"249"},{"product_id":"250"},{"product_id":"251"},{"product_id":"254"},{"product_id":"255"},{"product_id":"256"},{"product_id":"258"},{"product_id":"258"},{"product_id":"258"},{"product_id":"258"},{"product_id":"258"},{"product_id":"258"},{"product_id":"259"},{"product_id":"261"},{"product_id":"262"},{"product_id":"263"},{"product_id":"264"},{"product_id":"265"},{"product_id":"266"},{"product_id":"279"},{"product_id":"280"},{"product_id":"281"},{"product_id":"282"},{"product_id":"284"},{"product_id":"318"},{"product_id":"319"},{"product_id":"320"},{"product_id":"321"},{"product_id":"322"},{"product_id":"322"},{"product_id":"323"},{"product_id":"323"},{"product_id":"324"},{"product_id":"324"},{"product_id":"325"},{"product_id":"325"},{"product_id":"326"},{"product_id":"326"},{"product_id":"327"},{"product_id":"327"},{"product_id":"328"},{"product_id":"328"},{"product_id":"329"},{"product_id":"329"},{"product_id":"330"},{"product_id":"330"},{"product_id":"331"},{"product_id":"331"},{"product_id":"332"},{"product_id":"332"},{"product_id":"333"},{"product_id":"333"},{"product_id":"334"},{"product_id":"334"},{"product_id":"335"},{"product_id":"335"},{"product_id":"336"},{"product_id":"337"},{"product_id":"338"},{"product_id":"339"},{"product_id":"340"},{"product_id":"341"},{"product_id":"342"},{"product_id":"343"},{"product_id":"344"}]}}



                clean_result_1 = dict_from_str_1['success']['products_with_options']

                products_with_options_ids = []

                for item in clean_result_1:
                    # _logger.debug(item['product_id'])
                    products_with_options_ids.append(item['product_id'])
                # _logger.debug('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
                # _logger.debug(products_with_options_ids)
                products_without_options = []
                products_with_options = []
                for item in products_with_quantity_ids:
                    if item['product_id'] in products_with_options_ids:
                        products_with_options.append(item)
                    else:
                        products_without_options.append(item)
                # _logger.debug(products_with_options)
                # _logger.debug('######################################')
                # _logger.debug(products_without_options)
                products_with_options_result = []

                # for item in [{'model': 'A210', 'product_id': '151', 'quantity': '60'}]:

                product_id = ''

                for item in products_with_options:
                    # _logger.debug(item['product_id'])
                    if len(product_id) == 0:
                        product_id += str(item['product_id'])
                    else:
                        product_id += ',' + str(item['product_id']) 

                # _logger.debug(product_id)
                product_options_data_json = opencart.get_product_options_info(data_token, opencart.url, product_id)
                # _logger.debug('#############################')
                # _logger.debug(product_options_data_json)
                # _logger.debug(type(product_options_data_json))
                null_values_replaced = product_options_data_json.replace('null', '""')
                # _logger.debug(null_values_replaced)
                dict_from_str_0 = ast.literal_eval(null_values_replaced)
                # _logger.debug(dict_from_str_0)

                clean_result_0 = dict_from_str_0['success']['options']
                # _logger.debug('#############################')
                # _logger.debug(clean_result_0)
                # _logger.debug(products_with_options)
                # _logger.debug("*********************")  

                ERRORS = []

                for item in clean_result_0:
                    product_id = item
                    result = clean_result_0[item][0]["product_option_value"]

                    # _logger.debug(result)
                    # _logger.debug('$$$$$$$$$$$$$$$$$$$$$$$$')

                    # for item in products_with_options:
                    #     _logger.debug(item)
                    #     _logger.debug('####################')
                        
                    # #     # _logger.debug(item['product_id'])

                    #     if product_id == item['product_id']:
                    #         model = item['model']

                    quantity = 0  

                    

                    
                   

                    for subitem in result:
                        # _logger.debug(subitem)
                        # _logger.debug("*************************")
                                         

                        
                        
                        try:
                            model_quantity_id = {}
                            model = subitem['model']
                            if model == '':
                                raise Exception('Empty option_model!')

                            quantity = int(subitem['quantity'])
                            if quantity < 0:
                                quantity = 0 # Quantity can not be negative!!!

                            model_quantity_id['model'] = model

                            model_quantity_id['product_id'] = product_id
                            
                            model_quantity_id['quantity'] = quantity

                            products_with_options_result.append(model_quantity_id)
                        except Exception as e:
                            ERROR = {}
                            ERROR['ERROR_NO_PRODUCT_OPTION_VALUE: no value or empty option_model'] = subitem
                            ERROR['ERROR_product_id'] = product_id
                            ERROR['ERROR_description'] = repr(e)
                            
                            ERRORS.append(ERROR)
                        # model_quantity_id['model'] = subitem["product_option_value"][0]['model']
                        # model_quantity_id['quantity'] = subitem["product_option_value"][0]['quantity']
                        # _logger.debug(subitem)
                        # _logger.debug(clean_result_0[subitem]['model'])
                        # _logger.debug(clean_result_0[subitem]['quantity'])
                        # _logger.debug(subitem['product_id'])
                        # for key in subitem:
                        #     _logger.debug(key)

                _logger.debug('$$$$$$$$$$$$$$   ERROR  $$$$$$$$$$$$$$$$')
                _logger.debug(ERRORS)
                # _logger.debug('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
                # _logger.debug(products_with_options_result)

                products_in_odoo = self.env['storehouse.product'].search([
                    
                    
                    ('model_additional.customer.id', '=', opencart.customer.id)

                    ])
                # ('is_product_of_partner', '=', True),

                for item in products_in_odoo:
                    
                    try:
                        #model = item.model_additional.model
                        quantity = int(item.quantity)

                        model = False

                        # models
                        for record in item.model_additional:
                            # m2m customers
                            for customer in record.customer:
                                #_logger.debug(customer)
                                if customer.id == opencart.customer.id:
                                    model = record.model
                                    

                        # _logger.debug('OLD QUANTITY ==========')
                        # _logger.debug(quantity)
                        # _logger.debug(type(quantity))
                        # # _logger.debug(item.name)
                        # # _logger.debug(item.model_additional.customer.name)
                        # _logger.debug(item.model_additional.model)
                        # # _logger.debug(opencart.customer.name)
                        # _logger.debug(item.quantity)
                        # _logger.debug(type(item.quantity))
                        # _logger.debug('==================')
                        #if False:

                        if model:
                            
                            for item2 in products_without_options:

                                #if item2['model'] == model and int(item2['quantity']) != quantity:
                                #    _logger.debug('================================================')
                                
                                #    _logger.debug('products_without_options model: %s, quantity: %s' % (item2['model'],item2['quantity']))

                                #    _logger.debug('================================================')

                                if item2['model'] == model and int(item2['quantity']) != quantity:
                                    

                                    item.update({
                                        'quantity': int(item2['quantity']),
                                        })

                                    item.prod_2_update()
                            

                                   
                                
                            for item3 in products_with_options_result:

                                

                                #if item3['model'] == model and int(item3['quantity']) != quantity:
                                #    _logger.debug('------------------------------------------------')

                                #    res = 'products_with_options_result model: %s, quantity: %s \n' % (item3['model'],item3['quantity'])
                                
                                #    _logger.debug(res)

                                #    _logger.debug('------------------------------------------------')


                                

                                if item3['model'] == model and int(item3['quantity']) != quantity:

                                    item.update({
                                        'quantity': int(item3['quantity']),
                                        })

                                    item.prod_2_update()

                    except Exception as e:
                        _logger.debug('################ ERROR IN ODOO!!!!!!!!!!!!!')
                        _logger.debug(repr(e))

                s.close()


                #_logger.debug('----======-----======-----=====')
                #_logger.debug(out_pr)


                # A LOT OF REQUESTS TO get_product_options_info


                # for item in products_with_options:
                #     # _logger.debug(item['product_id'])

                #     product_id = item['product_id']

                #     model = item['model']

                #     product_options_data_json = opencart.get_product_options_info(data_token, opencart.url, product_id)
                #     # _logger.debug(product_options_data_json)
                #     # _logger.debug(type(product_options_data_json))
                #     null_values_replaced = product_options_data_json.replace('null', '""')

                #     dict_from_str_0 = ast.literal_eval(null_values_replaced)
                #     # _logger.debug(dict_from_str_0)

                #     clean_result_0 = dict_from_str_0['success']['options'][0]["product_option_value"]



                #     quantity = 0  

                #     model_quantity_id = {}
                   

                #     for subitem in clean_result_0:
                #         # _logger.debug(subitem)
                #         # _logger.debug("*************************")
                                         

                        
                #         ERROR = {}
                #         try:
                #             quantity += int(subitem['quantity'])
                #         except Exception as e:
                #             ERROR['ERROR_NO_PRODUCT_OPTION_VALUE'] = subitem
                #             ERROR['ERROR_product_id'] = product_id
                #         # model_quantity_id['model'] = subitem["product_option_value"][0]['model']
                #         # model_quantity_id['quantity'] = subitem["product_option_value"][0]['quantity']
                #         # _logger.debug(subitem)
                #         # _logger.debug(clean_result_0[subitem]['model'])
                #         # _logger.debug(clean_result_0[subitem]['quantity'])
                #         # _logger.debug(subitem['product_id'])
                #         # for key in subitem:
                #         #     _logger.debug(key)
                #     model_quantity_id['product_id'] = product_id
                #     model_quantity_id['model'] = model
                #     model_quantity_id['quantity'] = quantity

                #     products_with_options_result.append(model_quantity_id)
                # # _logger.debug('$$$$$$$$$$$$$$   ERROR  $$$$$$$$$$$$$$$$')
                # # _logger.debug(ERROR)
                # # _logger.debug('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
                # # _logger.debug(products_with_options_result)



                # products_in_odoo = self.env['storehouse.product'].search([
                    
                #     ('is_product_of_partner', '=', True),
                #     ('model_additional.customer.name', '=', opencart.customer.name)

                #     ])

                # for item in products_in_odoo:
                #     model = item.model_additional.model
                #     quantity = int(item.quantity)
                #     _logger.debug('OLD QUANTITY ==========')
                #     _logger.debug(quantity)
                #     _logger.debug(type(quantity))
                #     # # _logger.debug(item.name)
                #     # # _logger.debug(item.model_additional.customer.name)
                #     _logger.debug(item.model_additional.model)
                #     # # _logger.debug(opencart.customer.name)
                #     _logger.debug(item.quantity)
                #     # _logger.debug(type(item.quantity))
                #     # _logger.debug('==================')

                #     for item2 in products_without_options:
                #       if item2['model'] == model and int(item2['quantity']) != quantity:
                #         item.update({
                #             'quantity': int(item2['quantity']),
                #             })
                #         sys_config = self.env['storehouse.settings'].get_sys_config()

                #         if sys_config == 'products_virtual':
                #             self.env['storehouse.products_2_update'].create_update_record(item)
                #         _logger.debug('NEW QUANTITY ==========')
                #         _logger.debug(item2['quantity'])
                #         _logger.debug('======== NEW QUANTITY, product without options ==========')       
                        
                #     for item3 in products_with_options_result:
                #       if item3['model'] == model and int(item3['quantity']) != quantity:
                #         item.update({
                #             'quantity': int(item3['quantity']),
                #             })
                #         sys_config = self.env['storehouse.settings'].get_sys_config()

                #         if sys_config == 'products_virtual':
                #             self.env['storehouse.products_2_update'].create_update_record(item)

                #         _logger.debug('NEW QUANTITY ==========')
                #         _logger.debug(item3['quantity'])
                #         _logger.debug('======== NEW QUANTITY, product with options ==========')       
                        
                  

                

                # s.close()






####################################################################
####################################################################''' 

                # MAYBE IT IS FOR PRODUCTS WITH SETS OF OPTIONS:

                # for item in clean_result_0:
                #     product_id = item
                #     result = clean_result_0[item][0]["product_option_value"]
                #     # _logger.debug(result)
                #     # _logger.debug('$$$$$$$$$$$$$$$$$$$$$$$$')

                #     for item in products_with_options:
                        
                #     #     # _logger.debug(item['product_id'])

                #         if product_id == item['product_id']:
                #             model = item['model']

                #     quantity = 0  

                #     model_quantity_id = {}

                #     ERRORS = {}
                   

                #     for subitem in result:
                #         # _logger.debug(subitem)
                #         # _logger.debug("*************************")
                                         

                        
                        
                #         try:
                #             quantity += int(subitem['quantity'])
                #         except Exception as e:
                #             ERROR = {}
                #             ERROR['ERROR_NO_PRODUCT_OPTION_VALUE'] = subitem
                #             ERROR['ERROR_product_id'] = product_id
                #             ERRORS.append(ERROR)
                #         # model_quantity_id['model'] = subitem["product_option_value"][0]['model']
                #         # model_quantity_id['quantity'] = subitem["product_option_value"][0]['quantity']
                #         # _logger.debug(subitem)
                #         # _logger.debug(clean_result_0[subitem]['model'])
                #         # _logger.debug(clean_result_0[subitem]['quantity'])
                #         # _logger.debug(subitem['product_id'])
                #         # for key in subitem:
                #         #     _logger.debug(key)
                #     model_quantity_id['product_id'] = product_id
                #     model_quantity_id['model'] = model
                #     model_quantity_id['quantity'] = quantity

                #     products_with_options_result.append(model_quantity_id)

                
####################################################################
################################################################