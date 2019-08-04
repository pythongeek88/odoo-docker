# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging, requests, json, ast
import time
_logger = logging.getLogger(__name__)

class opencart_quantity(models.Model):
    _name = 'opencart.quantity'

    id = fields.Char()
    name = fields.Char()
    customer = fields.Many2one("storehouse.customer")
    #app_id = fields.Char()
    user_name = fields.Char()
    key = fields.Text()
    url = fields.Char() # Here we have url for login!
    status = fields.Boolean(default=False) # ORDERS
    upload_status = fields.Boolean(default=False) # PRODUCTS


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
    def get_one_product_options(self, data_token, url, product_id):

        s = requests.Session()


        if 'token' in data_token:
            #print(data['token'])
            token = data_token['token']
            url_to_get_product_options = str(url) +'/index.php?route=api/custom/productoptions&token=' + str(token) + '&product_id=' + str(product_id)
            product_options = s.post(url_to_get_product_options)         
        else:
            return "You don't have a token!"

        return product_options.content


    @api.multi
    def get_one_order_options(self, data_token, url, order_id, order_product_id):

        s = requests.Session()


        if 'token' in data_token:
            #print(data['token'])
            token = data_token['token']
            url_to_get_order_options = str(url) +'/index.php?route=api/customorder/orderoptions&token=' + str(token) + '&order_id=' + str(order_id) + '&order_product_id=' + str(order_product_id)
            order_options = s.post(url_to_get_order_options)         
        else:
            return "You don't have a token!"

        return order_options.content

    @api.multi
    def update_quantity_info(self, data_token, url, model, quantity):

        s = requests.Session()


        if 'token' in data_token:
            #print(data['token'])
            token = data_token['token']

            url_to_update_quantity = str(url) +'/index.php?route=api/product/edit&token=' + str(token) + '&model=' + str(model) + '&quantity=' + str(quantity)
            # _logger.debug('--------- %r ----------', str(modelmodel))

            new_quantity = s.post(url_to_update_quantity)
        else:
            return "You don't have a token!"

        return new_quantity.content

    @api.multi
    def update_option_quantity_info(self, data_token, url, model, quantity):

        s = requests.Session()


        if 'token' in data_token:
            #print(data['token'])
            token = data_token['token']

            url_to_update_quantity = str(url) +'/index.php?route=api/product/editoption&token=' + str(token) + '&model=' + str(model) + '&quantity=' + str(quantity)
            # _logger.debug('--------- %r ----------', str(modelmodel))

            new_quantity = s.post(url_to_update_quantity)
        else:
            return "You don't have a token!"

        return new_quantity.content

    @api.multi
    def main_opencart_job_quantity(self):
        _logger.debug('--------- main_opencart_job_quantity ----------')
        opencart_quantity_ids = self.env['opencart.quantity'].search([
            ('upload_status', '=', True)
            ])

        for opencart in opencart_quantity_ids:
            if opencart.upload_status:

                _logger.debug('--------- opencart %r BEGIN ----------', opencart.customer.name)

                key = opencart.key
                username = opencart.user_name
                url = str(opencart.url) + '/index.php?route=api/login'
                s = requests.Session()
                r = s.post(url, data={'username':username, 'key':key})
                data_token = json.loads(r.content)

                if 'token' in data_token:

                    data_2_update, info = self.env['storehouse.products_2_update'].get_products_2_update(opencart.customer.id, 'get')

                    # _logger.debug('---------  %r  ----------', data_2_update)
                    # _logger.debug('---------  %r  ----------', info)

                    if data_2_update:
                        error = 0
                        for product_id in data_2_update:
                            quantity = data_2_update[product_id][1]
                            
                            for model in data_2_update[product_id][0]:
                        # 'product_id': [['model1','model2','model3'], 'quantity', 'upd_id']
                                products_data_json_product_model = opencart.update_quantity_info(data_token, opencart.url, model, quantity)
                                # _logger.debug(products_data_json_product_model)
                               
                                if 'error' in products_data_json_product_model:

                                    products_data_json_option_model = opencart.update_option_quantity_info(data_token, opencart.url, model, quantity)
                                    # _logger.debug(products_data_json_option_model)

                                    if 'error' in products_data_json_option_model:
                                        error+=1
                                        _logger.debug('ERROR IN UPDATING MODEL:  %r ', model)
                        done, info = self.env['storehouse.products_2_update'].get_products_2_update(opencart.customer.id, 'done') # it has to be ONLY when there is not errors!
                        _logger.debug("--------- Products\' quantity are updated! ---------")
                        if not error:
                            _logger.debug("No error in updating!")
                            # done, info = self.env['storehouse.products_2_update'].get_products_2_update(opencart.customer.id, 'done')
                    else:
                        _logger.debug("--------- No products to update! ---------")

                    

                    s.close()

                else:
                    _logger.debug('We didn\'t get token!')

    # UPDATING ONCE A DAY QUANTITY OF ALL PRODUCTS

    # Here we start from products --> models_additional 
    # @api.multi
    # def get_products_2_update_all(self, customer_id):

    #     sys_config = self.env['storehouse.settings'].get_sys_config()

    #     all_products = self.env['storehouse.product'].search([])
    #     # _logger.debug(all_products)
    #     result = {}
    #     for item in all_products:
    #         product_info = []
    #         product_models = []
            
    #         list_of_models_additional = item.model_additional
    #         for record in list_of_models_additional:
    #             if record.customer.id==customer_id:
    #                 product_models.append(record.model)
    #         if len(product_models) != 0:
    #             if sys_config == 'box_inventory' or sys_config == 'products_virtual':
    #                 quantity = item.quantity
    #                 result[str(item.id)] = [product_models, quantity]
    #             # elif sys_config == 'products_inventory':
    #             #     quantity = item.quantity_on_stock
    #             #     result[str(item.id)] = [product_models, quantity]

    #     return result

    # Here we start from  models_additional --> products

    @api.multi
    def get_products_2_update_all(self, customer_id):

        sys_config = self.env['storehouse.settings'].get_sys_config()

        all_models = self.env['storehouse.product_models'].search([
            ('customer', '=', customer_id),

            ])
        # _logger.debug(all_models)
        result = {}
        for item in all_models:
            product_info = []
            product_models = []
            product_models.append(item.model)
            if len(item.product_id) == 1:
                if sys_config == 'box_inventory' or sys_config == 'products_virtual':
                    quantity = item.product_id.quantity
                    result[str(item.product_id.id)] = [product_models, quantity]
                # elif sys_config == 'products_inventory':
                #     quantity = item.quantity_on_stock
                #     result[str(item.id)] = [product_models, quantity]
        # _logger.debug(result)
        return result


    @api.multi
    def main_opencart_job_quantity_all_products(self):
        _logger.debug('--------- main_opencart_job_quantity_ALL_products ----------')
        t1 = time.clock()
        opencart_quantity_ids = self.env['opencart.quantity'].search([
            ('upload_status', '=', True)
            ])

        for opencart in opencart_quantity_ids:
            if opencart.upload_status:

                _logger.debug('--------- opencart %r BEGIN ----------', opencart.customer.name)

                key = opencart.key
                username = opencart.user_name
                url = str(opencart.url) + '/index.php?route=api/login'
                s = requests.Session()
                r = s.post(url, data={'username':username, 'key':key})
                data_token = json.loads(r.content)
                # _logger.debug(data_token['token'])
                if 'token' in data_token:
                    data_2_update = self.get_products_2_update_all(opencart.customer.id)

                    # _logger.debug('---------  %r  ----------', data_2_update)

                    if data_2_update:
                        error = 0
                        for product_id in data_2_update:
                            quantity = data_2_update[product_id][1]
                            
                            for model in data_2_update[product_id][0]:
                        # 'product_id': [['model1','model2','model3'], 'quantity', 'upd_id']
                                products_data_json_product_model = opencart.update_quantity_info(data_token, opencart.url, model, quantity)
                                # _logger.debug(products_data_json_product_model)
                               
                                if 'error' in products_data_json_product_model:

                                    products_data_json_option_model = opencart.update_option_quantity_info(data_token, opencart.url, model, quantity)
                                    # _logger.debug(products_data_json_option_model)

                                    if 'error' in products_data_json_option_model:
                                        error+=1
                                        _logger.debug('ERROR IN UPDATING MODEL:  %r ', model)
                        _logger.debug("--------- Products\' quantity are updated! ---------")
                        if not error:
                            _logger.debug("No error in updating!")
                            # done, info = self.env['storehouse.products_2_update'].get_products_2_update(opencart.customer.id, 'done')
                    else:
                        _logger.debug("No products to update! Check sys_config mode you use.")

                    s.close()   

                else:
                    _logger.debug('We didn\'t get token!')
                    
        t2 = time.clock()
        # _logger.debug('Took %r Seconds', (t2-t1))                      

                

                
                
               

                



    @api.multi
    def get_new_orders_info(self, data_token, url):

        s = requests.Session()



        if 'token' in data_token:
            #print(data['token'])
            token = data_token['token']
            url_to_get_orders = str(url) +'/index.php?route=api/customorders/orders&token=' + str(token)
            new_orders = s.post(url_to_get_orders)
        else:
            return "You don't have a token!"

        return new_orders.content

    @api.multi
    def parse_orders_info(self, data, order_name, data_token, opencart):
        #_logger.debug('--- parse orders info (opencart) ----')

        data_parsed = []
        #data = data.encode('UTF-8')
        data = json.loads(data)

        if 'orders' in data:
            for order in data['orders']:
                order_data = {}
                order_data['products'] = []

                order_data['order_id'] = order['order_id']


                order_data['order_date'] = order['date_added']
                order_data['order_name'] = order_name 
                order_data['client_name'] = order["CONCAT(o.firstname, ' ', o.lastname)"]
                order_data['client_tel'] = order['telephone']
                

                if order['payment_address_1'] and order['payment_address_2']:                

                    if order['payment_address_1'] == order['payment_address_2']: # Ask logic behind this...
                        order_data['client_address'] = order['payment_address_1']
                        order_data['shipping_address'] = order['payment_address_1']
                    else:
                        order_data['client_address'] = order['payment_address_1'] + ' / ' + order['payment_address_2']
                        order_data['shipping_address'] = order['payment_address_1']
                        order_data['shipping_address_2'] = order['payment_address_2']
                else:
                    order_data['client_address'] = order['payment_address_1']
                    order_data['shipping_address'] = order['payment_address_1']


                order_data['client_city'] = order['payment_city']
                order_data['client_postcode'] = order['payment_postcode']
                order_data['client_country'] = order['payment_country']
                order_data['client_state_region'] = order['payment_zone']


                for item in order['products']:

                    product_id =  item['product_id']
                    order_product_id = item['order_product_id']
                    order_id =  item['order_id']


                    product_options_data_json = opencart.get_one_product_options(data_token, opencart.url, product_id)
                    # _logger.debug('#############################')
                    # _logger.debug(product_options_data_json)

                    null_values_replaced = product_options_data_json.replace('null', '""')
                    dict_from_str_0 = ast.literal_eval(null_values_replaced)
                    clean_result_0 = dict_from_str_0['success']['options']
                    # _logger.debug('>>>>>>>>>>>>>>PRODUCT OPTIONS>>>>>>>>>>>>>>')
                    # _logger.debug(clean_result_0)
                    # _logger.debug(len(clean_result_0))
                    if len(clean_result_0) == 0:
                        order_data['products'].append({
                            'price': item['price'],
                            'product_name': item['name'],
                            'quantity': item['quantity'],
                            'sku': item['model']
                        })
                    else:
                        ERRORS = []
                        options_result = []

                        for item5 in clean_result_0:

                            result = clean_result_0[0]["product_option_value"]


                            # _logger.debug('product_option_value')
                            # _logger.debug(result)


                            quantity = 0  
                            
                           

                            for subitem in result:
                                
                                
                                try:
                                    model_quantity_id = {}
                                    model = subitem['model']
                                    if model == '':
                                        raise Exception('Empty option_model!')


                                    model_quantity_id['model'] = model

                                    name = subitem['name']

                                    model_quantity_id['name'] = name

                                    price = subitem['price']                                    

                                    model_quantity_id['price'] = price

                                    model_quantity_id['product_option_value_id'] = subitem['product_option_value_id'] 


                                    options_result.append(model_quantity_id)
                                except Exception as e:
                                    ERROR = {}
                                    ERROR['ERROR_NO_PRODUCT_OPTION_VALUE: no value or empty option_model'] = subitem

                                    ERROR['ERROR_description'] = repr(e)
                                    
                                    ERRORS.append(ERROR)


                        # _logger.debug('$$$$$$$$$$$$$$   ERROR  $$$$$$$$$$$$$$$$')
                        # _logger.debug(ERRORS)
                        # _logger.debug('$$$$$$$$$$$$$$   RESULT  $$$$$$$$$$$$$$$$')
                        # _logger.debug(options_result)

                        order_options_data_json = opencart.get_one_order_options(data_token, opencart.url, order_id, order_product_id)
                        # _logger.debug('#############################')
                        null_values_replaced = order_options_data_json.replace('null', '""')
                        dict_from_str_1 = ast.literal_eval(null_values_replaced)
                        clean_result_1 = dict_from_str_1['order']
                        # _logger.debug(clean_result_1)
                        # _logger.debug(len(clean_result_1))
                        if len(clean_result_1) == 0:
                            order_data['products'].append({
                                'price': item['price'],
                                'product_name': item['name'],
                                'quantity': item['quantity'],
                                'sku': item['model']
                            })
                        else:
                            product_option_value_id = clean_result_1[0]['product_option_value_id']
                            # _logger.debug(product_option_value_id)
                            for item6 in options_result:

                                # _logger.debug('item6')

                                # _logger.debug(item6)

                                # _logger.debug('''item6['product_option_value_id']''')


                                # _logger.debug(item6['product_option_value_id'])


                                # _logger.debug(item6['product_option_value_id'] == product_option_value_id)

                                if item6['product_option_value_id'] == product_option_value_id:
                                    # _logger.debug('********** result_1 price/product_name/quantity/sku: : %r/%r/%r/%r ---', item['price'], item6['name'], item['quantity'], item6['model'])
                                    result_1 = order_data['products'].append({
                                        'price': item['price'],
                                        'product_name': item6['name'],
                                        'quantity': item['quantity'],
                                        'sku': item6['model']
                                    })



                order_data['shipping_name'] = order["CONCAT(o.shipping_firstname, ' ', o.shipping_lastname)"]
                order_data['shipping_company'] = order['shipping_company']
                order_data['shipping_city'] = order['shipping_city']
                order_data['shipping_postcode'] = order['shipping_postcode']
                order_data['shipping_country'] = order['shipping_country']
                order_data['status_order'] = order['status'] # This is the word "Prosessed", not integer 10!!!!!!!!!!!

                data_parsed.append(order_data)

        return data_parsed

    @api.multi
    def check_orders_status(self, status, customer, data_token, url): # I added customer!
 
        s = requests.Session()


        if 'token' in data_token:

            token = data_token['token']
            
            
        else:
            return "You don't have a token!"

    

        orders_in_odoo = self.env['storehouse.clients_order'].search([
            ('customer_id', '=', customer.id), 
            ('status_id', '=', status)
            ])


        for order in orders_in_odoo:

            _logger.debug('======================Checking status of order with id:')
            _logger.debug(order.order_id_customer)
            order_id = order.order_id_customer
            url = str(url) +'/index.php?route=api/customorder/order&token=%s&order_id=%s' % (token, order_id) 
            r = s.post(url)


            data = json.loads(r.content)

            if 'order' not in data:

                _logger.debug('--- ERROR! : %r ---', data)

            else:

                opencart_status = data['order']['order_status']

                if opencart_status == 'Canceled':
                    order.rollback_order()

                else:

                    if opencart_status != order.status_id:

                        order.write({
                            'status_id': opencart_status
                            })

                        _logger.debug('----'+ str(order.id) +'new status: ' + opencart_status)

    @api.multi
    def delete_order(self, order_id, data_token, url): 
        if self.status:
            _logger.debug('===== test delete order =====')
            _logger.debug('===== %r =====', order_id)
            #_logger.debug('===== send cancel to opencart store: %r =====', self.name)
            
            
            s = requests.Session()
            if 'token' in data_token:
                #print(data['token'])
                token = data_token['token']
            
            
            else:
                return "You don't have a token!"

            #order_id = order.order_id_customer
            #order_id = 5
            url = str(url) +'/index.php?route=api/order/delete&token=%s&order_id=%s' % (token, order_id) 
            r = s.post(url)
           
            data = json.loads(r.content)

            s.close()

            _logger.debug('=== opencart_delete_response: %r ===',data)
            #data = {'Errors1':{}}

            if 'error' in data:
                _logger.debug('################# Errors during deletion! ############################')
                return False
            else:
                _logger.debug('!!!!!!!!!!!!!!!!!Deletion id = %r is completed!!!!!!!!!!!!!!!!!!!!!!!', order_id)
                return 'Deletion request is sent'
        else:
            return False
    @api.multi
    def cancel_order(self, order_id, order_status_id, data_token, url): 
        if self.status:
            _logger.debug('===== test cancel order =====')
            _logger.debug('===== order id %r =====', order_id)
            _logger.debug('===== order status id %r =====', order_status_id)
            #_logger.debug('===== send cancel to opencart store: %r =====', self.name)
            
            
            s = requests.Session()
            if 'token' in data_token:
                #print(data['token'])
                token = data_token['token']
            
            
            else:
                return "You don't have a token!"

            #order_id = order.order_id_customer
            #order_id = 5
            url = str(url) +'/index.php?route=api/order/edit&token=%s&order_id=%s&order_status_id=%s' % (token, order_id, order_status_id) 
            r = s.post(url)
           
            data = json.loads(r.content)

            s.close()

            _logger.debug('=== opencart_cancel_response: %r ===',data)
            #data = {'Errors1':{}}

            if 'error' in data:
                _logger.debug('################# Errors during cancelation! ############################')
                return False
            else:
                _logger.debug('!!!!!!!!!!!!!!!!!Cancelation id = %r is completed!!!!!!!!!!!!!!!!!!!!!!!', order_id)
                return 'Cancel request is sent'
        else:
            return False



    @api.multi
    def main_opencart_job_orders(self):
        _logger.debug('--------- main_opencart_job_orders ----------')
        opencart_quantity_ids = self.env['opencart.quantity'].search([
            ('status', '=', True)
            ])

        for opencart in opencart_quantity_ids:
            if opencart.status:

                key = opencart.key
                username = opencart.user_name
                url = str(opencart.url) + '/index.php?route=api/login'
                s = requests.Session()
                r = s.post(url, data={'username':username, 'key':key})
                data_token = json.loads(r.content)

                check_statuses = ['Pending'] #'Processed', 'Processing', 'Expired', 
                for status in check_statuses:
                    _logger.debug('--------- opencart check_status %r   ----------', status)
                    _logger.debug('--------- shop is %r   ----------', opencart.customer.name)
                    opencart.check_orders_status(status, opencart.customer, data_token, opencart.url)

                _logger.debug('--------- opencart %r BEGIN ----------', opencart.customer.name) 
                orders_data_json = opencart.get_new_orders_info(data_token, opencart.url)
                # _logger.debug("#############################")
                # _logger.debug(orders_data_json)
                orders_data_parsed = opencart.parse_orders_info(orders_data_json, opencart.name, data_token, opencart)
                # _logger.debug(orders_data_parsed)
                for every_order in orders_data_parsed:
                    list_item_to_transfer = [every_order]
                    self.env['storehouse.clients_order'].add_client_order(list_item_to_transfer, opencart.name, opencart.customer.id)
                _logger.debug("Orders for %r updated.", opencart.customer.name)
                
                # ------------------- HERE IS TEST OF DELETION:

                #test_of_deletion = self.delete_order(5, data_token, opencart.url)
                
                # ------------------- HERE IS TEST OF CANCELATION: cancel_order(self, order_id, order_status_id (3 - means canceled!), data_token)

                # test_of_cancelation = self.cancel_order(3, 3, data_token, opencart.url)
                s.close()





####################################################################
####################################################################''' 
