# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging
import datetime
import ast
import base64, os, json
from email.mime.text import MIMEText
import smtplib
# encoding
#import sys
#reload(sys)
#sys.setdefaultencoding('utf-8')

_logger = logging.getLogger(__name__)

class settings(models.Model):
    _name = 'storehouse.settings'

    id = fields.Char()
    status = fields.Boolean(default=False)
    products_virtual = fields.Boolean(default=False)
    products_inventory = fields.Boolean(default=False)
    #box_virtual = fields.Boolean(default=False)
    box_inventory = fields.Boolean(default=False)

    @api.multi
    def recompute_products_quantity(self):
        products = self.env['storehouse.product'].search([])

        if len(products) > 0:
            count = 0
            for product in products:
                product.compute_product_values()
                count += 1
            
            msg = '%s recomputed products' % (count)
        else:
            msg = 'No products records!'

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
    def get_sys_config(self):
        config = self.env['storehouse.settings'].search([('status', '=', True)])
        if len(config) == 1:

            if config.products_virtual == True:
                return 'products_virtual'
                #without boxes at all
            if config.products_inventory == True:
                return 'products_inventory'
                #it has only product barcode
            if config.box_inventory == True:
                return 'box_inventory' #it has box_barcode
        else:
            return False

class barcode(models.Model):
    _name = 'storehouse.barcode'

    _sql_constraints = [
                      #('product_id_unique', 
                      #'unique(product_id)',
                      #'"Product" Choose another value - it must be unique!'),
                      #('box_id_unique', 
                      #'unique(box_id)',
                      #'"Box" Choose another value - it must be unique!'),
                      ('barcode_unique', 
                      'unique(barcode)',
                      '"Barcode" Choose another value - it must be unique!'),
                      ]

    id = fields.Char()
    product_id = fields.Many2one('storehouse.product')
    box_id = fields.Many2one('storehouse.box')
    barcode = fields.Char()

class set(models.Model):
    _name = 'storehouse.set'
    _rec_name = 'name'
    _order = 'model'

    id = fields.Char()
    name = fields.Char()
    model = fields.Char()
    model_additional = fields.One2many('storehouse.set_model_additional', 'set_id')
    set_equipment = fields.One2many("storehouse.set_equipment", "set_id", help="Set Equipment")
    is_discontinued = fields.Boolean(default=False)
    status = fields.Boolean(default=True)

    @api.multi
    def compute_quantity(self):
        for record in self:
            #record.quantity = 3
            quantity_list = []
            if record.set_equipment:
                for set_equipment in record.set_equipment:
                    #_logger.debug('-------------')
                    product_quantity = set_equipment.product_id.quantity
                    quantity_in_set = set_equipment.set_product_quantity
                    if quantity_in_set != 0:
                        min_quantity = product_quantity // quantity_in_set
                    else:
                        min_quantity = 0
                    quantity_list.append(min_quantity)
                    #_logger.debug(product_quantity) # product quantity
                    #_logger.debug(quantity_in_set) # quantity in set
                    #_logger.debug('min quantity %s' % (min_quantity))

                record.quantity = min(quantity_list)
                
    quantity = fields.Integer(compute='compute_quantity')

    def get_set_model_quantity(self, customer_id=False):
        # return models list, quantity for set by customer id
        #customer_id = 79
        if customer_id:
            _logger.debug('============= get_set_model_quantity ==============')

            #if self.is_discontinued:
            #    is_discontinued = 1
            #else:
            #    is_discontinued = 0

            quantity_list = []
            models_list = []

            for model_additional in self.model_additional:
                if customer_id == model_additional.customer_id.id:
                    #_logger.debug(model_additional.model)
                    #_logger.debug(model_additional.customer_id.id)
                    models_list.append(model_additional.model)
                

            for set_equipment in self.set_equipment:
                product_quantity = set_equipment.product_id.quantity
                quantity_in_set = set_equipment.set_product_quantity
                min_quantity = product_quantity // quantity_in_set
                quantity_list.append(min_quantity)


            if len(models_list) > 0:
                #_logger.debug(models_list)
                #_logger.debug(min(quantity_list))
                if self.is_discontinued and min(quantity_list) == 0:
                    is_discontinued = 1
                else:
                    is_discontinued = 0

                return models_list, min(quantity_list), is_discontinued
            else:
                return False

class set_equipment(models.Model):
    _name = 'storehouse.set_equipment'
    _rec_name = 'id'

    id = fields.Char()
    set_id = fields.Many2one('storehouse.set')
    product_id = fields.Many2one('storehouse.product')
    set_product_quantity = fields.Integer()

    @api.multi
    def products_quantity(self):
        for record in self:
            #_logger.debug('----------------------------')
            #_logger.debug(self)
            record.total_products_quantity = record.product_id.quantity

    total_products_quantity = fields.Integer(compute='products_quantity')

class set_model_additional(models.Model):
    _name = 'storehouse.set_model_additional'
    _rec_name = 'id'

    id = fields.Char()
    model = fields.Char()
    set_id = fields.Many2one('storehouse.set')
    customer_id = fields.Many2one('storehouse.customer')

class product(models.Model):
    _name = 'storehouse.product'
    _rec_name = 'name'
    _order = 'model'

    _sql_constraints = [
                     ('field_unique', 
                      'unique(model)',
                      '"Product Model" Choose another value - it must be unique!')]

    id = fields.Char()
    name = fields.Char(help="Product name", required=True )

    name_additional = fields.One2many('storehouse.product_names', 'product_id')
    """
    @api.multi
    @api.constrains('name_additional')
    def make_name_uniq(self):
        if len(self.name_additional) == 0:
            msg = "Name must be filled!"
            raise ValidationError(msg)

        customers = []
        names = []
        for record in self.name_additional:
            if record.name not in names:
                names.append(record.name)
            else:
                msg = "Name \"%s\" added earlier!" % (record.name)
                raise ValidationError(msg)

            for customer in record.customer:
                if customer not in customers:
                    customers.append(customer)
                else:
                    for rec in self.name_additional:
                        for old_customer in rec.customer:
                            if old_customer == customer:
                                error_msg = "Name \"%s\" error! Customer \"%s\" added earlier to name \"%s\""\
                                 % (record.name, customer.name, rec.name)
                                raise ValidationError(error_msg)
    """

    model = fields.Char(help="Model name", required=True)

    @api.multi
    @api.onchange('model')
    def make_model_uppercase(self):
        for record in self:
            if record.model:
                model_upper = record.model.upper()
                record.model = model_upper

    # for xml-rpc
    def make_model_uppercase_xml(self):
        for record in self:
            model_upper = record.model.upper()
            try:
                record.write({
                    'model': model_upper,
                    })
            except Exception:
                #return "check product model: %s" % (record.model)
                return False, 'check product model: %s' % (model_upper)

        return True

    model_additional = fields.One2many('storehouse.product_models', 'product_id')

    #@api.multi
    #@api.constrains('model_additional')
    #def make_customer_uniq(self):
    #    if  len(self.model_additional) == 0:
    #        msg = "Model must be filled!"
    #        raise ValidationError(msg)

    image_url = fields.Char(help="Image url")
    description = fields.Text(help="Product description")
    #price = fields.Many2one("storehouse.price", help = "Product price")
    price = fields.One2many("storehouse.price", 'product_id', help = "Product price")

    @api.multi
    @api.constrains('price')
    def make_price_uniq(self):
        customers = []
        for record in self.price:

            if record.customer not in customers:
                customers.append(record.customer)
            else:
                msg = "Product Price Error! Customer \"%s\" added earlier!" % (record.customer.name)
                raise ValidationError(msg)

    @api.multi
    @api.constrains('product_equipment')
    def make_equipment_filled(self):
        #_logger.debug('==========')
        #_logger.debug(self.product_equipment)

        sys_config = self.env['storehouse.settings'].get_sys_config()

        if sys_config == 'products_virtual':
            pass
        if sys_config == 'box_inventory':
            if len(self.product_equipment) == 0 and not self.is_product_of_partner:
                msg = "Product Equipment Error! Please fill the \"Product Equipment!\""
                raise ValidationError(msg)

    sku_upc = fields.Char(help="Stock keeping unit / Universal product code")
    ean = fields.Char(help="European article number")
    jan = fields.Char(help="Japanese article number")
    isbn = fields.Char(help="International standard book number")
    mpn = fields.Char(help="Manufacturer part number")
    units_wid_sel = [('pound', 'pound'), ('kg', 'kg')]
    units_wid = fields.Selection(units_wid_sel, default='pound', required=True, help="Unit of measurement")
    depth = fields.Float(help="Product depth")
    width = fields.Float(help="Product width")
    height = fields.Float(help="Product height")
    weight = fields.Float(help="Product weight")

    size_unit_sel = [('inch', 'inch'), ('mm', 'mm')]
    size_unit_id = fields.Selection(size_unit_sel, default='inch', required=True, help="Unit of measurement")

    is_option = fields.Boolean(help="Is Option?",default=False)

    is_product_of_partner = fields.Boolean(default=False)

    is_discontinued = fields.Boolean(default=False)

    owner = fields.Many2one('storehouse.customer')

    product_equipment = fields.One2many(
        "storehouse.product_equipment",
        "product_id",
        help="Product Equipment"
        )

    @api.multi
    @api.constrains('product_equipment')
    def make_equipment_box_uniq(self):
        boxes = []
        for record in self.product_equipment:
            #_logger.debug('==============================================')
            #_logger.debug(record.box_id)

            if record.box_id not in boxes:
                boxes.append(record.box_id)
            else:
                msg = "Product Equipment Error! Box \"%s\" added earlier!" % (record.box_id.name)
                raise ValidationError(msg)

    status = fields.Boolean(help="Active/inactive", default=True)
    manufacturer = fields.Many2one("storehouse.manufacturer", help="Manufacturer from Storehouse Manufacturers")
    meta_tag_title = fields.Char(help="Meta Tag Title")
    quantity = fields.Integer(help="Product quantity") # for 'box_inventory', 'products_virtual'
    quantity_4_compare = fields.Integer() # field for compare with quantity
    quantity_on_stock = fields.Integer()               # unused
    #    quantity_need_2_order = fields.Integer()           # for 'products_virtual'
    @api.multi
    @api.onchange('quantity')
    def update_if_change_quantity(self):

        sys_config = self.env['storehouse.settings'].get_sys_config()

        if sys_config == 'products_virtual':# or sys_config == 'box_inventory':
            self._origin.prod_2_update()

    transport_weight = fields.Float()
    transport_volume = fields.Float()

    @api.multi
    def compute_product_quantity(self):
        _logger.debug('---- compute_product_quantity ----')
        #self.compute_product_volume_weight_by_boxes()


        if not self.is_option and not self.is_product_of_partner:
            #_logger.debug(self.product_equipment)

            quantity_stock = [] # quantity always > 0 or == 0, for update
            #quantity_need_2_order = []

            if len(self.product_equipment) > 0:

                #merge_boxes(self.product_equipment)

                for box in self.product_equipment:
                    if box.box_id.quantity > 0:
                        quantity = box.box_id.quantity // box.quantity
                        quantity_stock.append(quantity)
                        #quantity_need_2_order.append(0)

                    elif box.box_id.quantity <= 0:
                        quantity_stock.append(0)

                stock = min(quantity_stock)
                #need_2_order = max(quantity_need_2_order)
                
                if self.quantity != stock: # or self.quantity_need_2_order != need_2_order: # if quantity changed - write new value and update

                    self.write({
                        'quantity': stock,
                        #'quantity_need_2_order': need_2_order,
                        })

                    self.prod_2_update()

            else:
                self.write({
                    'quantity': 0,
                    #'quantity_need_2_order': 0,
                    })

        elif self.is_option or self.is_product_of_partner:
            #self.prod_2_update()
            #_logger.debug('----- elif self.is_option or self.is_product_of_partner: ------')
            if self.quantity != self.quantity_4_compare:

                self.write({
                    'quantity_4_compare': self.quantity,
                    })

                self.prod_2_update()

    @api.multi
    def compute_product_values(self):
        sys_config = self.get_sys_config()

        if sys_config == 'box_inventory':
            #self.compute_product_volume_weight_by_boxes()
            self.compute_product_quantity()
        if sys_config == 'products_virtual':
            #self.prod_2_update()
            pass

    action_compute = fields.Boolean(compute='compute_product_values')

    @api.multi
    def change_product_quantity_by_boxes(self, quantity, raise_exception=True):
        _logger.debug('-------- change_product_quantity_by_boxes --------')
        # used from add orders, or rollback order
        # if quantity negative - boxes, if positive + boxes
        # for 'box_inventory' config
        quantity = int(quantity)

        if self.quantity < -(quantity) and quantity < 0 and len(self.product_equipment) > 0:

            return False
        else:

            def boxes_change(equipment, quantity):
                for box in equipment:
                    _logger.debug('----------- %r', box.quantity) #box quantity in product 
                    _logger.debug('----------- %r', box.box_id.quantity) # all boxes quantity
                    _logger.debug('----------- %r', box.box_id.name) # box name
                    total_quantity = box.quantity * quantity + box.box_id.quantity
                    #write quantity in table storehouse.box
                    box.box_id.write({
                        'quantity': total_quantity
                        })
                    box.box_id.recompute_depend_products()          
            _logger.debug('--------------- %r', quantity)
            if not self.id:
                return 'Error'
            if len(self.product_equipment) > 0:
                for record in self:
                    boxes_change(record.product_equipment, quantity)
                return True
            else:
                return False

    @api.multi
    def change_products_virtual_quantity(self, quantity, raise_exception=True):
        # used from add orders, or rollback order
        # if quantity negative - product quantity, if positive + product quantity
        # for 'products_virtual' config
        quantity = int(quantity)

        #_logger.debug('=======================================================')
        #_logger.debug(quantity)

        old_quantity = self.quantity
        #old_quantity = self.quantity_on_stock
        # old_quantity_need_2_order = self.quantity_need_2_order

        # + quantity
        if quantity > 0:

            self.write({
                'quantity': old_quantity + quantity
                })

            self.prod_2_update()
        # - quantity
        elif quantity < 0:

            if self.quantity >= -(quantity):
            
                self.write({
                    'quantity': old_quantity + quantity
                    })

                self.prod_2_update()
            else:
                # order quantity more than stock!!!

                #self.write({
                #    'quantity_on_stock': 0,
                #    })
                #
                #self.prod_2_update()

                return False

        return True




        #if self.quantity_on_stock < -(quantity) and quantity < 0:
            
    #primary_image = 
    #image_list =
    
    brand = fields.Many2one("storehouse.brand", help="Brand from Storehouse Brand")
    category = fields.Many2one("storehouse.category_product", help="Product category")
    barcode = fields.One2many('storehouse.barcode', 'product_id')


    @api.multi
    #@api.onchange('quantity')
    def prod_2_update(self):

        if self.status:
            self.env['storehouse.products_2_update'].create_update_record(self)
            return True
        else:
            return False

    @api.multi
    def get_sys_config(self):
        sys_config = self.env['storehouse.settings'].get_sys_config()
        #_logger.debug('=======================================================')
        #_logger.debug(sys_config)
        for record in self:
            record.sys_config = sys_config
        return sys_config


    sys_config = fields.Char(compute=get_sys_config)

class product_names(models.Model):
    _name = 'storehouse.product_names'
    _rec_name = 'name'

    id = fields.Char()
    product_id = fields.Many2one("storehouse.product")
    name = fields.Char(required=True)
    customer = fields.Many2many('storehouse.customer', required=True)

class product_models(models.Model):
    _name = 'storehouse.product_models'
    _rec_name = 'model'

    _sql_constraints = [(
        'additional_model_unique',
        'unique(model)',
        '"Additional Model" Choose another value - it must be unique!')]

    id = fields.Char()
    product_id = fields.Many2one("storehouse.product")
    model = fields.Char(required=True)  
    customer = fields.Many2many('storehouse.customer', required=True)

#class product_options(models.Model):
#   _name = 'storehouse.product_options'
#   _rec_name = 'options_model'
#
#   id = fields.Char()
#   product_id = fields.Many2one("storehouse.product")
#   #product_id = fields.Many2many(
#   #   comodel_name = 'storehouse.product',
#   #   relation = 'storehouse_product_product_options_rel',
#   #   column1 = 'product_options',
#   #   column2 = 'product'
#   #   )
#   box_id = fields.Many2one("storehouse.box")
#   options_model = fields.Char()
#   quantity = fields.Integer()

class product_equipment(models.Model):
    _name = 'storehouse.product_equipment'
    _rec_name = 'box_id'

    id = fields.Char()
    product_id = fields.Many2one("storehouse.product")
    box_id = fields.Many2one("storehouse.box")
    quantity = fields.Integer(default=None)
    is_option = fields.Boolean(default=False, help="Is this box are option?")
    box_option = fields.Many2one("storehouse.box_options")
    @api.multi
    @api.depends('box_id')
    def compute_total_box_quantity(self):
        for record in self:
            record.total_quantity = record.box_id.quantity

    total_quantity = fields.Integer(compute=compute_total_box_quantity)

    #   @api.multi
    #   @api.onchange('quantity')
    #   def show_warn_msg(self):
    #       if self.quantity == 0:
    #           return {'warning':{
    #           'message': 'Choose another value > 0',
    #           'title': 'Error!',
    #           }}
    @api.multi
    @api.constrains('quantity')
    def check_quantity(self):
        if self.quantity == 0:
            error_msg = "Product Equipment error! Box \"%s\" quantity error! Choose another value > 0" % (self.box_id.name)
            raise ValidationError(error_msg)

class box_options(models.Model):
    _name = 'storehouse.box_options'
    _rec_name = 'option'

    id = fields.Char()
    #product_equipment_id = fields.Many2one('storehouse.product_equipment')
    option = fields.Char(required=True)

class box(models.Model):
    _name = 'storehouse.box'
    _rec_name = 'name'
    _sql_constraints = [
                     ('field_unique', 
                      'unique(barcode)',
                      'Choose another value for barcode - it has to be unique!')]

    id = fields.Char()
    name = fields.Char(help="Accessories name")
    #barcode = fields.Char(help="Accessories barcodeID")
    barcode = fields.One2many('storehouse.barcode', 'box_id')
    depth = fields.Float(help="Product depth")
    width = fields.Float(help="Product width")
    height = fields.Float(help="Product height")
    weight = fields.Float(help="Product weight")
    description = fields.Text(help="Box description")
    quantity = fields.Integer(help="Box quantity")
    
    @api.depends('depth', 'width', 'height')
    def compute_box_volume(self):
        for record in self:
            vol = float((self.depth * self.width * self.height) / 1728)
            self.volume = round(vol, 2)

    volume = fields.Float(compute='compute_box_volume', store=True)

    @api.multi
    @api.depends('quantity')
    def recompute_depend_products(self):
        sys_config = self.env['storehouse.settings'].get_sys_config()

        if sys_config == 'box_inventory':
            _logger.debug('++++++++++ boxes onchange ++++++++')

            for record in self:
                product_equipment_ids = self.env['storehouse.product_equipment'].search([
                    ('box_id.id', '=', record.id)
                    ])
                _logger.debug('++++++ product eq ids: %r', product_equipment_ids)
                for equipment in product_equipment_ids:
                    _logger.debug('+++++++++ product id: %r', equipment.product_id.id)
                    product = self.env['storehouse.product'].search([
                        ('id', '=', equipment.product_id.id)
                        ])
                    product.compute_product_quantity()
                    #product.compute_product_volume_weight_by_boxes()

        return False

    action_compute = fields.Boolean(compute='recompute_depend_products')

    @api.multi
    def update_all_products_rel_box(self):
        sys_config = self.env['storehouse.settings'].get_sys_config()

        if sys_config == 'box_inventory':

            for record in self:
                product_equipment_ids = self.env['storehouse.product_equipment'].search([
                    ('box_id.id', '=', record.id)
                    ])
                for equipment in product_equipment_ids:
                    product = self.env['storehouse.product'].search([
                        ('id', '=', equipment.product_id.id)
                        ])
                    product.prod_2_update()
                    
        return False


class manufacturer(models.Model):
    _name = 'storehouse.manufacturer'
    _rec_name = 'name'
    _sql_constraints = [
                     ('field_unique', 
                      'unique(name)',
                      '"Manufacturer Name" Choose another value - it must be unique!')]

    id = fields.Char()
    name = fields.Char(help="Manufacturer name")
    web_site = fields.Char(help="Manufacturer website")
    email = fields.Char(help="Manufacturer email")
    telephone = fields.Char(help="Manufacturer telephone")
    fax = fields.Char(help="Manufacturer fax")
    status = fields.Boolean(help="Active/inactive")
    address = fields.Char(help="Manufacturer address")
    city = fields.Char(help="Manufacturer city")
    postcode = fields.Integer(help="Manufacturer postcode")
    country = fields.Char(help="Manufacturer country")
    state_region = fields.Char(help="Manufacturer state region")

class brand(models.Model):
    _name = 'storehouse.brand'
    _rec_name = 'name'
    _sql_constraints = [
                     ('field_unique', 
                      'unique(name)',
                      '"Brand Name" Choose another value - it must be unique!')]

    id = fields.Char()
    name = fields.Char(help="Brand name")

class inventory(models.Model):
    _name = 'storehouse.inventory'
    _rec_name = 'cell'

    _sql_constraints = [
                         ('field_unique', 
                          'unique(cell)',
                          'Choose another cell - it has to be unique!')]

    id = fields.Char()
    cell = fields.Many2one("storehouse.cell", help="ID from Cell")
    box = fields.Many2one("storehouse.box", help="Box name from Boxes")
    amount = fields.Integer(help="Boxes amount")

class cell(models.Model):
    _name = 'storehouse.cell'
    _rec_name = 'id'

    id = fields.Char()
    line = fields.Integer(help="Cell line coordinate")
    level = fields.Integer(help="Cell level coordinate")
    place = fields.Integer(help="Cell place coordinate")
    height = fields.Integer(help="Cell max height")
    width = fields.Integer(help="Cell max width")
    depth = fields.Integer(help="Cell max depth")
    weight = fields.Integer(help="Cell max weight")

class suppliers(models.Model):
    _name = 'storehouse.suppliers'
    _rec_name = 'name'

    id = fields.Char()
    name = fields.Char(help="Supplier name")
    website = fields.Char(help="Supplier website")
    email = fields.Char(help="Supplier email")
    telephone = fields.Char(help="Supplier telephone")
    fax = fields.Char(help="Supplier fax")
    status = fields.Boolean(help="Status active/inactive")
    address = fields.Char(help="Supplier address")
    city = fields.Char(help="Supplier city")
    postcode = fields.Char(help="Supplier postcode")
    country = fields.Char(help="Supplier country")
    state_region = fields.Char(help="Supplier state region")

class price(models.Model):
    _name = 'storehouse.price'
    _rec_name = 'msrp'
    _order = 'msrp'
    product_id = fields.Many2one("storehouse.product")
    msrp = fields.Float(help="Max price selling", required=True)
    ship_price = fields.Float(help="Shipping cost")
    m_a_p = fields.Float(help="minimum advertised price")
    cost_additional = fields.Float(help="Cost additional")
    cost = fields.Float()
    customer = fields.Many2one("storehouse.customer", help="Customer name from Storehouse Customers", required=True)

class customer(models.Model):
    _name = 'storehouse.customer'
    _rec_name = 'name'

    id = fields.Char()
    name = fields.Char(help="Customer name")
    website = fields.Char(help="Customer website")
    email = fields.Char(help="Customer email")
    telephone = fields.Char(help="Customer telephone")
    fax = fields.Char(help="Customer fax")
    status = fields.Boolean(help="Status Active/inactive", default=False)
    is_partner = fields.Boolean(default=False)
    address = fields.Char(help="Customer address")
    city = fields.Char(help="Customer city")
    postcode = fields.Integer(help="Customer postcode")
    country = fields.Char(help="Customer country")
    state_region = fields.Char(help="Customer state region")
    commission = fields.Float(help="Commission %")

    type_sel = [
        ('amazon.settings_seller', 'AMZN Seller'),
        ('amazon.settings_vendor', 'AMZN Vendor'),
        ('houzz.settings', 'Houzz'),
        ('wayfair.settings', 'Wayfair'),
        ('hayneedle.settings', 'Hayneedle'),
        ('opencart.settings', 'OpenCart'),
        ('local.settings', 'Local')
        ]

    market_channel_type = fields.Selection(type_sel, help='')

    @api.multi
    @api.constrains('commission')
    def check_input_value(self):
        #raise ValidationError(error_msg)
        if self.commission:
            if self.commission < 0 or self.commission > 100:
                raise ValidationError('\"Commission\" wrong value! \"%s\"' % (self.commission))

class clients(models.Model):
    _name = 'storehouse.clients'
    _rec_name = 'name'

    id = fields.Char()
    name = fields.Char(help="Client name")
    email = fields.Char(help="Client email")
    telephone = fields.Char(help="Client telephone")
    fax = fields.Char(help="Client fax")
    address = fields.Char(help="Client address")
    city = fields.Char(help="Client city")
    postcode = fields.Char(help="Client postcode")
    country = fields.Char(help="Client country")
    state_region = fields.Char(help="Client state region")

    @api.multi
    def add_client_info(self,info=False):
        if info:

            client_id = self.env['storehouse.clients'].search([
                ('name', '=', info['client_name']),
                #('email', '=', info['client_email']),
                ('telephone', '=', info['client_tel']),
                #('fax', '=', info['client_fax']),
                ('address', '=', info['client_address']),
                ('city', '=', info['client_city']),
                ('postcode', '=', info['client_postcode']),
                ('country', '=', info['client_country']),
                ('state_region', '=', info['client_state_region']),
                ])

            if client_id:
                return client_id.id
            else:
                client_id = self.env['storehouse.clients'].create({
                    'name': info['client_name'],
                    'email': info['client_email'],
                    'telephone': info['client_tel'],
                    #'fax': info['client_fax'],
                    'address': info['client_address'],
                    'city': info['client_city'],
                    'postcode': info['client_postcode'],
                    'country': info['client_country'],
                    'state_region': info['client_state_region'],
                    })
                return client_id.id

        return False

#class units_weight(models.Model):
#   _name = 'storehouse.units_weight'
#   _rec_name = 'unitwname'
#
#   id = fields.Char()
#   unitwname = fields.Char()
#   conversionindexw = fields.Char()
#
#class size_units(models.Model):
#   _name = 'storehouse.size_units'
#
#   id = fields.Char()
#   sizeunitname = fields.Char()
#   conversionindexs = fields.Char()

class category_product(models.Model):
    _name = 'storehouse.category_product'
    _rec_name = 'category'

    id = fields.Char()
    category = fields.Char()

class clients_order(models.Model):
    _name = 'storehouse.clients_order'
    _rec_name = 'id'

    id = fields.Char()
    create_date = fields.Datetime(readonly=True)
    order_name = fields.Char() #???
    #total = fields.Float(help='Total Price')
    extra_cost = fields.Float(help='Extra Cost')
    status_id = fields.Char()
    status_order_odoo = fields.Many2one('storehouse.status')

    edi_850 = fields.Many2one('storehouse.edi_850')
    edi_856 = fields.Many2one('storehouse.edi_856')
    edi_855 = fields.Many2one('storehouse.edi_855')
    edi_810 = fields.Many2one('storehouse.edi_810')

    @api.multi
    @api.constrains('status_order_odoo')
    def set_comments_to_log(self):
        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        if not self.log:
            log = ''
        else:
            log = self.log

        if self.status_order_odoo:
            log += "<p>[%s \"UTC\"] User \"%s\" set order status to \"%s\"</p>" % (time, self.env.user.name, self.status_order_odoo.status)
        else:
            log += "<p>[%s \"UTC\"] User \"%s\" unlink order status</p>" % (time, self.env.user.name)

        self.write({
            'log': log
            })

    customer_id = fields.Many2one('storehouse.customer')
    invoce_prefix = fields.Char()

    clients_order_set = fields.One2many(
        'storehouse.clients_order_set',
        'clients_order_id'
        )

    clients_order_product = fields.One2many(
        'storehouse.clients_order_product',
        'clients_order_id'
        )

    order_equipment = fields.One2many(
        'storehouse.clients_order_equipment',
        'order_id'
        )

    items_need_2_order = fields.One2many(
        'storehouse.items_need_2_order',
        'clients_order_id'
        )

    clients_id = fields.Many2one('storehouse.clients', help="Client name")

    @api.multi
    def get_client_tel(self):
        for record in self:
            record.client_tel = record.clients_id.telephone

    client_tel = fields.Char(compute='get_client_tel')

    order_id_customer = fields.Char(help='Customer Order ID')

    shipping_firstname = fields.Char()
    shipping_company = fields.Char()
    shipping_address_1 = fields.Char()
    shipping_address_2 = fields.Char()
    shipping_city = fields.Char()
    shipping_postcode = fields.Char()
    shipping_country = fields.Char()

    order_info = fields.Text()

    @api.multi
    def compute_order_vol_weight(self):

        #sys_config = self.get_sys_config()
        sys_config = self.env['storehouse.settings'].get_sys_config()
        _logger.debug('************** compute_order_vol_weight ***************')

        

        if sys_config == 'box_inventory' or True:
            _logger.debug('************** box_inventory ***************')
            for order in self:
                #_logger.debug('*************** %r', self.clients_order_product)
                vol_by_boxes = 0
                weight_by_boxes = 0
                for record in order.items_need_2_order:
                    if record.processed:
                        #_logger.debug(record.product_id.product_equipment)
                        #_logger.debug(record.ordered_quantity)
                        for box in record.product_id.product_equipment:
                            #_logger.debug(box.quantity)
                            #_logger.debug(box.box_id.name)

                            vol_by_boxes += record.ordered_quantity * (box.quantity * (box.box_id.depth * box.box_id.width * box.box_id.height / 1728))
                            weight_by_boxes += record.ordered_quantity * (box.quantity * box.box_id.weight)

                order.volume_comp_box_inv = '%s %s' % (vol_by_boxes, '(Boxes ft3)')
                order.gross_weight_comp_box_inv = '%s %s' % (weight_by_boxes, '(Boxes lb)')

        #return False

        if sys_config == 'products_virtual' or True:
            _logger.debug('************** products_virtual ***************')
            for order in self:
                vol_by_products = 0
                weight_by_products = 0

                for record in order.items_need_2_order:

                    if record.processed:

                        vol_by_products += record.ordered_quantity * record.product_id.transport_volume
                        weight_by_products += record.ordered_quantity * record.product_id.transport_weight

                order.volume_comp_prod_vir = '%s %s' % (vol_by_products, 'Products inch')
                order.gross_weight_comp_prod_vir = '%s %s' % (weight_by_products, 'Products pound')
                    

    volume_comp_box_inv = fields.Char(compute='compute_order_vol_weight')
    gross_weight_comp_box_inv = fields.Char(compute='compute_order_vol_weight')
    volume_comp_prod_vir = fields.Char(compute='compute_order_vol_weight')
    gross_weight_comp_prod_vir = fields.Char(compute='compute_order_vol_weight')

    @api.multi
    def compute_order_total_price(self):
        for order in self:
            total = 0

            for record in order.items_need_2_order:
                if record.processed:
                    total += record.ordered_quantity * record.price_per_product

            order.total = total

    total = fields.Float(compute='compute_order_total_price', help='Total Price')
    
    error = fields.Boolean(default=False)
    warning = fields.Html()
    log = fields.Text()

    cancel_info = fields.Text() # visible in order
    cancel_data = fields.Char() # for 3rd party stores logic
    need_cancel = fields.Boolean(default=False)
    cancel_in_progress = fields.Boolean(default=False)
    canceled = fields.Boolean(default=False)

    @api.model
    def create(self, values):
        record = super(clients_order, self).create(values)

        #_logger.debug('--------- custom create order function ------------')
        # add custom python code here
        # press "save" button to run the code

        return record

    def set_canceled_odoo_status(self):
        #_logger.debug('---------------------------------------------------------------------------')
        if self.canceled == True:

            canceled_status = self.env['storehouse.status'].search([('status','=','Canceled')])

            if len(canceled_status) == 0:
                canceled_status = self.env['storehouse.status'].create({
                    'status': 'Canceled',
                    })

            if self.status_order_odoo.id != canceled_status.id:

                self.write({
                    'status_order_odoo': canceled_status.id,
                    })

    @api.multi
    def get_orders_2_cancel(self, customer=False):
        # for market channels
        if customer:
            orders_need_cancel = self.env['storehouse.clients_order'].search([
                ('need_cancel', '=', True),
                ('canceled', '=', False),
                ('cancel_in_progress', '=', False),
                ])

            orders = orders_need_cancel.filtered(lambda order: order.customer_id.id == customer.id)

            if len(orders) > 0:
                return orders
            else:
                return False
        else:
            return False



    @api.multi
    def write_msg_to_log(self, user_action_message=False,message=False):
        time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        if not self.log:
            log = ''
        else:
            log = self.log

        if user_action_message:
            log += "<p>[%s \"UTC\"] User \"%s\": %s</p>" % (time, self.env.user.name, user_action_message)
        if message:
            log += "<p>[%s \"UTC\"] %s</p>" % (time, message)

        if user_action_message or message:

            self.write({
                'log': log
                })

    @api.multi
    def rollback_order(self):
        #for cancel order if order canceled on marketchannels(api)

        sys_config = self.env['storehouse.settings'].get_sys_config()

        _logger.debug('/////////////////// rollback order ///////////')     
        _logger.debug('// order id: %r   //', self.id)

        #ordred_products = self.clients_order_product
        #if len(ordred_products) > 0:
        processed_products = self.items_need_2_order
        if len(processed_products) > 0:
            for product in processed_products:

                if product.processed:

                    storehouse_product = self.env['storehouse.product'].search([
                        ('id', '=', product.product_id.id)
                        ])

                    if sys_config == 'products_virtual':
                        storehouse_product.change_products_virtual_quantity(product.ordered_quantity)

                    if sys_config == 'box_inventory': 
                        storehouse_product.change_product_quantity_by_boxes(product.ordered_quantity)

            self.write({
                'status_id': 'Canceled',
                'canceled': True,
                })

            self.set_canceled_odoo_status()

        elif len(processed_products) == 0:
            self.write({
                'status_id': 'Canceled',
                'canceled': True,
                })

            self.set_canceled_odoo_status()

    @api.multi
    def rollback_order_button(self):
        # for test
        _logger.debug('======== rollback order button =======')
        #_logger.debug(self.id)
        #if False:
        if self.customer_id.market_channel_type:
            # for houzz
#            if self.customer_id.market_channel_type == 'houzz.settings':
#                
#                return {
#                    'name': 'Cancel Info',
#                    'type': 'ir.actions.act_window', 
#                    'view_type': 'form', 
#                    'view_mode': 'form',
#                    'res_model': 'storehouse.cancel_order_info_houzz', 
#                    'target': 'new',
#                    'context': {
#                        'default_order_id': self.id,
#                        } 
#                    }
#
#            elif self.customer_id.market_channel_type == 'amazon.settings_seller':
#                
#                return {
#                    'name': 'Cancel Info',
#                    'type': 'ir.actions.act_window', 
#                    'view_type': 'form', 
#                    'view_mode': 'form',
#                    'res_model': 'storehouse.cancel_order_info_amzn_seller', 
#                    'target': 'new',
#                    'context': {
#                        'default_order_id': self.id,
#                        } 
#                    }
#
#            elif self.customer_id.market_channel_type == 'wayfair.settings':
#                
#                return {
#                    'name': 'Cancel Info',
#                    'type': 'ir.actions.act_window', 
#                    'view_type': 'form', 
#                    'view_mode': 'form',
#                    'res_model': 'storehouse.cancel_order_info_wayfair', 
#                    'target': 'new',
#                    'context': {
#                        'default_order_id': self.id,
#                        } 
#                    }
#
#            elif self.customer_id.market_channel_type == 'amazon.settings_vendor':
#                
#                return {
#                    'name': 'Cancel Info',
#                    'type': 'ir.actions.act_window', 
#                    'view_type': 'form', 
#                    'view_mode': 'form',
#                    'res_model': 'storehouse.cancel_order_info_amazon_vendor', 
#                    'target': 'new',
#                    'context': {
#                        'default_order_id': self.id,
#                        } 
#                    }

            if self.customer_id.market_channel_type == 'local.settings':
                
                return {
                    'name': 'Cancel Info',
                    'type': 'ir.actions.act_window', 
                    'view_type': 'form', 
                    'view_mode': 'form',
                    'res_model': 'storehouse.cancel_order_info_local', 
                    'target': 'new',
                    'context': {
                        'default_order_id': self.id,
                        } 
                    }

            else:
                msg = 'Market Channel Type "%s" cancellation "code" in development' % (self.customer_id.market_channel_type)
                return {
                    'name': 'INFO',
                    'type': 'ir.actions.act_window', 
                    'view_type': 'form', 
                    'view_mode': 'form',
                    'res_model': 'storehouse.info_message', 
                    'target': 'new',
                    'context': {
                        'default_html': msg,
                        } 
                    }


        else:
            msg = "Check \"Market Channel Type\" of Market Channel \"%s\"!" % (self.customer_id.name)
            header = "Market Channel \"%s\" ERROR!" % (self.customer_id.name)


            return {
                'name': header,
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
    def add_comment(self):
        
        return {
            'name': 'Comment',
            'type': 'ir.actions.act_window', 
            'view_type': 'form', 
            'view_mode': 'form',
            'res_model': 'storehouse.order_comment', 
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                } 
            }


    @api.multi
    def add_client_order(self, data_parsed, store_name, customer_id):
        # order data from 3-rd party stores
        order = data_parsed[0]

        existing_order_record = self.search([
            ('order_id_customer', '=', order['order_id']),
            ('customer_id.id', '=', customer_id),
            ])

        ### add new order record #####
        if not existing_order_record:
            html_missing_product_begin = """
                <p> missing products<br></p>
                <table class="table table-bordered">
                <tbody>
                <thead>
                <th>product name</th>
                <th>product sku</th>
                <th>ordered quantity</th>
                <th>price</th>
                <th>total price</th>
                </thead>"""
            html_missing_product_data = ''
            html_missing_product_end = """</tbody></table>"""

            # create client record
            client_id = self.env['storehouse.clients'].add_client_info(order)
            #_logger.debug(order)
            #return False

            # create new record
            clients_order = self.create({
                'clients_id': client_id,
                'customer_id': customer_id,
                'order_id_customer': order['order_id'],
                })

            msg_2_email_notification = '<p>marketchannel: %s</p>' % (clients_order.customer_id.name)
            msg_2_email_notification += '<p>order id: %s</p>' % (order['order_id'])
            msg_2_email_notification += '<p>total price (original data): %s</p>' % (order['total_price'])
            total_price_marketchannel_computed = 0

            # create ordered items records
            for product_info in order['products']:

                #_logger.debug('////////////////////////////')
                #_logger.debug(product_info)
                msg_2_email_notification += '<ul>'
                if 'sku' in product_info:
                    msg_2_email_notification += '<li>product sku: %s</li>'  % (product_info['sku'])
                if 'odoo_set_id' in product_info:
                    msg_2_email_notification += '<li>local order, odoo set id: %s</li>'  % (product_info['odoo_set_id'])
                if 'odoo_product_id' in product_info:
                    msg_2_email_notification += '<li>local order, odoo product id: %s</li>'  % (product_info['odoo_product_id'])

                msg_2_email_notification += '<li>product name: %s</li>'  % (product_info['product_name'])
                msg_2_email_notification += '<li>product price: %s</li>'  % (product_info['price'])
                msg_2_email_notification += '<li>ordered quantity: %s</li>'  % (product_info['quantity'])
                msg_2_email_notification += '</ul>'

                total_price_marketchannel_computed += float(product_info['price']) * int(product_info['quantity'])

                set_id = self.env['storehouse.clients_order_set'].add_clients_order_set_info(product_info,clients_order.id,customer_id)

                if not set_id:

                    product_id = self.env['storehouse.clients_order_product'].add_clients_order_product_info(product_info,clients_order.id,customer_id)

                    if not product_id:

                        html_missing_product_data += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" \
                        % (product_info['product_name'], product_info['sku'], product_info['quantity'], \
                        product_info['price'], int(product_info['quantity']) * float(product_info['price']))

                        if clients_order.error == False:
                            clients_order.write({'error': True})

            warn = html_missing_product_begin + html_missing_product_data.encode('ascii','replace') + html_missing_product_end

            # emails
            msg_2_email_notification += '<p>total price (computed): %s</p>' % (total_price_marketchannel_computed)
            out_emails = self.env['storehouse.mail_server_users'].send_mail_2_all(msg_2_email_notification, 'order from: %s' % (clients_order.customer_id.name))
            
            # write missing products info
            if clients_order.error == True:
                clients_order.write({'warning': warn})

            #
            if 'status_id' in order:
                status = order['status_id']
            else:
                status = ''

            if 'info' in order:
                if type(order['info']) is str:
                    order_info = order['info']
                elif type(order['info']) is list:
                    order_info = ''
                    for item in order['info']:
                        order_info += '<p>%s</p>' % (item)
                else:
                    order_info = False
            else:
                order_info = False

            # fill order record
            clients_order.write({
                    'shipping_firstname': order['shipping_name'],
                    'shipping_company': order['shipping_company'],
                    'shipping_address_1': order['shipping_address'],
                    #'shipping_address_2': order['shipping_'],
                    'shipping_city': order['shipping_city'],
                    'shipping_postcode': order['shipping_postcode'],
                    'shipping_country': order['shipping_country'],
                    'status_id': status,
                    'order_info': order_info,
                    })

            # compute section if no errors in order
            eq_status = clients_order.create_order_equipment(clients_order.id)

            if eq_status:

                is_ordered_items_exist = True

                for equipment in clients_order.order_equipment:

                    if equipment.ordered_quantity > int(equipment.current_quantity):
                        is_ordered_items_exist = False

                #_logger.debug('==================================================================')
                #_logger.debug(is_ordered_items_exist)

                if is_ordered_items_exist:
                
                    for equipment in clients_order.order_equipment:

                        for i in range(equipment.ordered_quantity):
                            equipment.change_ordered_item_location('order')


            return True, clients_order.id, clients_order

        ### add new order record  end #####

        else:
            _logger.debug("************* order added earlier by id: %s", existing_order_record.id)
            return False, existing_order_record.id, existing_order_record

        return False

    @api.multi
    def all_order_equipment_to_order_button(self):
        if not self.error and self.order_equipment:
            for record in self.order_equipment:
                for i in range(record.ordered_quantity):
                    record.change_ordered_item_location('order')
            return True
        else:
            return False

    @api.multi
    def all_order_equipment_to_warehouse_button(self):
        if not self.error and self.order_equipment:
            for record in self.order_equipment:
                for i in range(record.reserved_quantity):
                    record.change_ordered_item_location('warehouse')
            return True
        else:
            return False

    @api.multi
    def create_order_equipment(self, order_id):
        client_order = self.search([
            ('id', '=', order_id),
            ])


        if client_order and not client_order.error:
        #if client_order:

            #ordered_products = {'product_id': 'ordered quantity'}
            ordered_products = {}

            #ordered_partnes_products
            ordered_partners_products = {}

            #ordered_boxes = {'box_id': 'ordered quantity'}
            ordered_boxes = {}

            # ordered_products from clients_order_set
            for _set in client_order.clients_order_set:
                #_logger.debug('ordered set id: %s' % (_set.set_id.id))
                #_logger.debug('ordered set quantity: %s' % (_set.quantity))
                #_logger.debug('ordered set status: %s' % (_set.status))

                for set_eq in _set.set_id.set_equipment:
                    #_logger.debug('product_id in set: %s' % (set_eq.product_id.id))
                    ##_logger.debug('quantity in set: %s' % (set_eq.set_product_quantity))
                    #_logger.debug('ordered quantity: %s' % (set_eq.set_product_quantity * _set.quantity))
                    if set_eq.product_id not in ordered_products:
                        ordered_products[set_eq.product_id] = set_eq.set_product_quantity * _set.quantity
                    else:
                        old_quantity = ordered_products[set_eq.product_id]
                        ordered_products[set_eq.product_id] = set_eq.set_product_quantity * _set.quantity + old_quantity

            # ordered_products from clients_order_product
            for _product in client_order.clients_order_product:
                #_logger.debug('ordered product id: %s' % (_product.product_id.id))
                #_logger.debug('ordered product quantity: %s' % (_product.quantity))
                ##_logger.debug('ordered product status: %s' % (_product.status))

                if _product.product_id not in ordered_products:
                    ordered_products[_product.product_id] = _product.quantity
                else:
                    old_quantity = ordered_products[_product.product_id]
                    ordered_products[_product.product_id] = _product.quantity + old_quantity

            #_logger.debug('==============================')
            #_logger.debug(ordered_products)

            for product in ordered_products:
                #_logger.debug(product.name)
                #_logger.debug('ordered quantity %s' % (ordered_products[product]))

                if not product.is_product_of_partner:
                
                    for equipment in product.product_equipment:
                        #_logger.debug('ordered box id: %s' % (equipment.box_id.id))
                        #_logger.debug('ordered box quantity: %s' % (equipment.quantity * ordered_products[product]))

                        if equipment.box_id not in ordered_boxes:
                            ordered_boxes[equipment.box_id] = equipment.quantity * ordered_products[product]
                        else:
                            old_quantity = ordered_boxes[equipment.box_id]
                            ordered_boxes[equipment.box_id] = equipment.quantity * ordered_products[product] + old_quantity

                else:
                    ordered_partners_products[product] = ordered_products[product]

            _logger.debug(ordered_partners_products)
            _logger.debug(ordered_boxes)


            for product in ordered_partners_products:
                order_eq_product = self.env['storehouse.clients_order_equipment'].create({
                    'order_id': client_order.id,
                    'product': product.id,
                    'ordered_quantity': ordered_partners_products[product],
                    })

            for box in ordered_boxes:
                order_eq_box = self.env['storehouse.clients_order_equipment'].create({
                    'order_id': client_order.id,
                    'box': box.id,
                    'ordered_quantity': ordered_boxes[box],
                    })

            return True
        else:
            return False

class clients_order_2_canel(models.Model):
    _name = 'storehouse.clients_order_2_canel'

    id = fields.Char()
    customer = fields.Many2one('storehouse.customer')
    order = fields.Many2one('storehouse.clients_order')
    cancel_data = fields.Text()

    in_work = fields.Boolean(default=False)
    done = fields.Boolean(default=False)



class local_clients_order(models.TransientModel):
    _name = 'storehouse.local_clients_order'
    #_inherit = 'storehouse.clients_order'

    id = fields.Char()
    customer = fields.Many2one('storehouse.customer', required=True)
    order_name = fields.Char(default='Local Order')
    order_id = fields.Char()

    shipping_postcode = fields.Char()
    shipping_name = fields.Char()
    shipping_city = fields.Char()
    shipping_state = fields.Char()
    shipping_address = fields.Char()
    shipping_company = fields.Char()
    shipping_country = fields.Char()

    client_name = fields.Char(required=True)
    client_tel = fields.Char(required=True)
    client_state_region = fields.Char()
    client_postcode = fields.Char()
    client_email = fields.Char()
    client_country = fields.Char()
    client_city = fields.Char()
    client_address = fields.Char()
    client_fax = fields.Char()

    clients_order_set = fields.One2many(
        'storehouse.local_clients_order_set',
        'local_clients_order_id'
        )

    clients_order_product = fields.One2many(
        'storehouse.local_clients_order_product',
        'local_clients_order_id'
        )


    @api.multi
    def ok_action(self):
        for record in self:

            data_parsed = []
            order = {}
            order['products'] = []
            order['info'] = []

            final_odoo_id = False

            _logger.debug('==========================================')
            #_logger.debug(record.id)

            curr_date = datetime.datetime.now().strftime('%Y%m%d')
            curr_time_utc = datetime.datetime.utcnow().strftime('%H%M')

            if not record.order_id:
                record.write({
                    'order_id': 'local_' + curr_date + '_utc_' + curr_time_utc,
                    })
            order['order_id'] = record.order_id

            if not record.shipping_postcode:
                record.write({
                    'shipping_postcode': ' ',
                    })
            order['shipping_postcode'] = record.shipping_postcode

            if not record.shipping_name:
                record.write({
                    'shipping_name': ' ',
                    })
            order['shipping_name'] = record.shipping_name

            if not record.shipping_city:
                record.write({
                    'shipping_city': ' ',
                    })
            order['shipping_city'] = record.shipping_city

            if not record.shipping_state:
                record.write({
                    'shipping_state': ' ',
                    })
            order['shipping_state'] = record.shipping_state

            if not record.shipping_address:
                record.write({
                    'shipping_address': ' ',
                    })
            order['shipping_address'] = record.shipping_address

            if not record.shipping_company:
                record.write({
                    'shipping_company': ' ',
                    })
            order['shipping_company'] = record.shipping_company

            if not record.shipping_country:
                record.write({
                    'shipping_country': ' ',
                    })
            order['shipping_country'] = record.shipping_country

            if not record.client_state_region:
                record.write({
                    'client_state_region': ' ',
                    })
            order['client_state_region'] = record.client_state_region

            if not record.client_postcode:
                record.write({
                    'client_postcode': ' ',
                    })
            order['client_postcode'] = record.client_postcode

            if not record.client_email:
                record.write({
                    'client_email': ' ',
                    })
            order['client_email'] = record.client_email

            if not record.client_country:
                record.write({
                    'client_country': ' ',
                    })
            order['client_country'] = record.client_country

            if not record.client_city:
                record.write({
                    'client_city': ' ',
                    })
            order['client_city'] = record.client_city

            if not record.client_address:
                record.write({
                    'client_address': ' ',
                    })
            order['client_address'] = record.client_address

            if not record.client_fax:
                record.write({
                    'client_fax': ' ',
                    })
            order['client_fax'] = record.client_fax

            ordered_products_odoo_tmp = self.env['storehouse.local_clients_order_product'].search([
                ('local_clients_order_id', '=', record.id),
                ])

            ordered_sets_odoo_tmp = self.env['storehouse.local_clients_order_set'].search([
                ('local_clients_order_id', '=', record.id),
                ])

            total_price = 0

            if record.clients_order_set:
                for _set in ordered_sets_odoo_tmp:
                    #_logger.debug('set: %s' % (_set.set_id.name))
                    order['products'].append({
                            'product_name': _set.set_id.name,
                            'quantity': _set.quantity,
                            'price': _set.price,
                            'odoo_set_id': _set.set_id.id,
                        })

                    total_price += int(_set.quantity) * float(_set.price)

            if record.clients_order_product:
                for product in ordered_products_odoo_tmp:
                    #_logger.debug('product: %s' % (product.product_id.name))
                    order['products'].append({
                            'product_name': product.product_id.name,
                            'quantity': product.quantity,
                            'price': product.price,
                            'odoo_product_id': product.product_id.id,
                        })

                    total_price += int(product.quantity) * float(product.price)

            order['order_name'] = record.order_name
            order['order_id'] = record.order_id
            order['shipping_postcode'] = record.shipping_postcode
            order['shipping_name'] = record.shipping_name
            order['shipping_city'] = record.shipping_city
            order['shipping_state'] = record.shipping_state
            order['shipping_address'] = record.shipping_address
            order['shipping_company'] = record.shipping_company
            order['shipping_country'] = record.shipping_country
            order['client_name'] = record.client_name
            order['client_tel'] = record.client_tel
            order['client_state_region'] = record.client_state_region
            order['client_postcode'] = record.client_postcode
            order['client_email'] = record.client_email
            order['client_country'] = record.client_country
            order['client_city'] = record.client_city
            order['client_address'] = record.client_address
            order['client_fax'] = record.client_fax
            order['total_price'] = total_price

            if 'products' in order and len(order['products']) > 0:
                data_parsed.append(order)

                _logger.debug(order)

                odoo_order = self.env['storehouse.clients_order'].add_client_order(data_parsed, record.order_name, record.customer.id)

                #_logger.debug(order)
                if odoo_order[0] == True:
                    final_odoo_id = odoo_order[1]

            if final_odoo_id:
                res = {
                    'name': 'Confirmation',
                    'type': 'ir.actions.act_window', 
                    'view_type': 'form', 
                    'view_mode': 'form',
                    'res_model': 'storehouse.clients_order',
                    'res_id': final_odoo_id,
                    'target': 'self',
                    'context': {} 
                    }
            else:
                res = {
                    'name': 'Local Order',
                    'type': 'ir.actions.act_window', 
                    'view_type': 'form', 
                    'view_mode': 'form',
                    'res_model': 'storehouse.local_clients_order',
                    'res_id': record.id,
                    'target': 'new',
                    'context': {} 
                    }

            return res

        return True

class local_clients_order_set(models.TransientModel):
    _name = 'storehouse.local_clients_order_set'
    #_inherit = 'storehouse.clients_order_set'
    id = fields.Char()
    set_id = fields.Many2one('storehouse.set', required=True)
    quantity = fields.Integer(default=1)
    price = fields.Float(default=0)
    local_clients_order_id = fields.Many2one('storehouse.local_clients_order')
class local_clients_order_product(models.TransientModel):
    _name = 'storehouse.local_clients_order_product'
    #_inherit = 'storehouse.clients_order_product'
    id = fields.Char()
    product_id = fields.Many2one('storehouse.product', required=True)
    quantity = fields.Integer(default=1)
    price = fields.Float(default=0)
    local_clients_order_id = fields.Many2one('storehouse.local_clients_order')


class clients_order_equipment(models.Model):
    _name = 'storehouse.clients_order_equipment'

    id = fields.Char()
    order_id = fields.Many2one('storehouse.clients_order')
    box = fields.Many2one('storehouse.box')
    product = fields.Many2one('storehouse.product')
    ordered_quantity = fields.Integer()
    @api.multi
    def get_curr_item_quantity(self):
        for item in self:
            if item.box and not item.product:
                item.current_quantity = item.box.quantity
            elif not item.box and item.product:
                item.current_quantity = item.product.quantity
            else:
                item.current_quantity = 'err'
    current_quantity = fields.Char(compute='get_curr_item_quantity')
    reserved_quantity = fields.Integer()

    @api.multi
    def change_ordered_item_location(self, location):
        """ + item from warehouse to order or - from order to warehouse """

        if location == 'warehouse':
            quantity = 1
        elif location == 'order':
            quantity = -1

        for record in self:

            if record.reserved_quantity >= 0:# and record.reserved_quantity < record.ordered_quantity:

                if quantity > 0 and record.reserved_quantity > 0:

                    _logger.debug('item from order to warehouse')

                    if record.box and not record.product:
                        new_quantity = record.box.quantity + quantity
                    elif record.product and not record.box:
                        new_quantity = record.product.quantity + quantity

                    if record.box and not record.product:
                        record.box.write({
                            'quantity': new_quantity,
                            })
                        # create update record
                        record.box.update_all_products_rel_box()

                    elif record.product and not record.box:
                        record.product.write({
                            'quantity': new_quantity,
                            })

                        # create update record
                        record.product.prod_2_update()

                    new_reserved_quantity = record.reserved_quantity - quantity
                    record.write({
                        'reserved_quantity': new_reserved_quantity
                        })

                    return True

                if quantity < 0 and record.reserved_quantity < record.ordered_quantity:

                    _logger.debug('item from warehouse to order')

                    if record.box and not record.product:
                        new_quantity = record.box.quantity + quantity
                    elif record.product and not record.box:
                        new_quantity = record.product.quantity + quantity

                    if new_quantity >= 0:

                        if record.box and not record.product:
                            record.box.write({
                                'quantity': new_quantity,
                                })
                            # create update record
                            record.box.update_all_products_rel_box()

                        elif record.product and not record.box:
                            record.product.write({
                                'quantity': new_quantity,
                                })
                            # update record
                            record.product.prod_2_update()

                        new_reserved_quantity = record.reserved_quantity + -(quantity)
                        record.write({
                            'reserved_quantity': new_reserved_quantity
                            })

                    return True

                return False


    @api.multi
    def change_reserved_quantity_plus(self, context=False):
        _logger.debug('++++++++++++++++++++++++++++++++')
        status = self.change_ordered_item_location('order')

    @api.multi
    def change_reserved_quantity_minus(self, context=False):
        _logger.debug('--------------------------------')
        status = self.change_ordered_item_location('warehouse')

class write_order_comment(models.TransientModel):
    _name = 'storehouse.order_comment'

    comment = fields.Text(required=True)
    order_id = fields.Integer()

    @api.multi
    def write_comment(self):
        order = self.env['storehouse.clients_order'].search([('id','=', self.order_id)])
        order.write_msg_to_log(user_action_message=self.comment)

class cancel_order_info_houzz(models.TransientModel):
    _name = 'storehouse.cancel_order_info_houzz'

    code_sel = [
        ('1', 'Item out of stock'),
        ('5', 'Other'),
        ]

    cancel_code = fields.Selection(code_sel, required=True, help='')
    cancel_comment = fields.Text(required=True)
    order_id = fields.Integer()

    @api.multi
    def write_cancel_info(self):

        #return False

        order_2_cancel = self.env['storehouse.clients_order'].search([('id','=', self.order_id)])
        cancellation_status = self.env['storehouse.status'].search([('status','=','Cancellation')])

        if len(cancellation_status) == 0:
            cancellation_status = self.env['storehouse.status'].create({
                'status': 'Cancellation',
                })

        if self.cancel_code == '1':
            cancel_code_msg = '<p>Cancel Code: "%s", "Item out of stock"</p>' % (self.cancel_code)
        elif self.cancel_code == '5':
            cancel_code_msg = '<p>Cancel Code: "%s", "Other"</p>' % (self.cancel_code)

        cancel_info_msg = cancel_code_msg + '<p>Cancel comment: "%s"</p>' % (self.cancel_comment)

        cancel_data = json.dumps({
            'cancel_code': self.cancel_code,
            'cancel_comment': self.cancel_comment,
            })

        order_2_cancel.write({
            'cancel_info': cancel_info_msg,
            'cancel_data': cancel_data,
            'need_cancel': True,
            'status_order_odoo': cancellation_status.id,
            })

        order_2_cancel.write_msg_to_log(user_action_message='sent cancel request to market channel')

        #msg = 'Information to cancel: %s, order id: %s' % (self.cancel_comment, self.order_id)
        msg = cancel_info_msg

        return {
            'name': 'Info Message',
            'type': 'ir.actions.act_window', 
            'view_type': 'form', 
            'view_mode': 'form',
            'res_model': 'storehouse.info_message', 
            'target': 'new',
            'context': {
                'default_html': msg,
                } 
            }

class cancel_order_info_amzn_seller(models.TransientModel):
    _name = 'storehouse.cancel_order_info_amzn_seller'

    code_sel = [
        ('NoInventory', 'No Inventory'),
        ('BuyerCanceled', 'Buyer Canceled'),
        ('GeneralAdjustment', 'General Adjustment'),
        ('PricingError', 'Pricing Error'),
        ('ShippingAddressUndeliverable', 'Shipping Address Undeliverable'),
        ('CustomerExchange', 'Customer Exchange'),
        ]


    cancel_code = fields.Selection(code_sel)
    cancel_comment = fields.Text(required=True)
    order_id = fields.Integer()

    @api.multi
    def write_cancel_info(self):

        order_2_cancel = self.env['storehouse.clients_order'].search([('id','=', self.order_id)])
        cancellation_status = self.env['storehouse.status'].search([('status','=','Cancellation')])

        if len(cancellation_status) == 0:
            cancellation_status = self.env['storehouse.status'].create({
                'status': 'Cancellation',
                })

        _logger.debug('------------------------')
        #_logger.debug(type(self.cancel_code))
        #_logger.debug(self.cancel_code)

        if self.cancel_code == False:
            _logger.debug(type(self.cancel_code))
            _logger.debug(self.cancel_code)

            cancel_info_msg = '<p>Cancel comment: "%s"</p>' % (self.cancel_comment)

            cancel_data = json.dumps({
            'cancel_code': self.cancel_code,
            'cancel_comment': self.cancel_comment,
            })

            order_2_cancel.write({
                'cancel_info': cancel_info_msg,
                'cancel_data': cancel_data,
                'need_cancel': True,
                'status_order_odoo': cancellation_status.id,
                })

            order_2_cancel.write_msg_to_log(user_action_message='sent cancel request to market channel')

        else:
            _logger.debug(type(self.cancel_code))
            _logger.debug(self.cancel_code)

class cancel_order_info_wayfair(models.TransientModel):
    _name = 'storehouse.cancel_order_info_wayfair'

    ack_sel = [
        ('ID', 'Item Deleted'),
        ('IR', 'Item Rejected'),
        ]

    cancel_comment = fields.Text(required=True)
    ack_code = fields.Selection(ack_sel, required=True)
    order_id = fields.Integer()

    @api.multi
    def write_cancel_info(self):
        _logger.debug('========= wayfair write_cancel_info ==========')

        order_2_cancel = self.env['storehouse.clients_order'].search([('id','=', self.order_id)])
        cancellation_status = self.env['storehouse.status'].search([('status','=','Cancellation')])

        if len(cancellation_status) == 0:
            cancellation_status = self.env['storehouse.status'].create({
                'status': 'Cancellation',
                })

        cancel_info_msg = '<p>Cancel comment: "%s"</p>' % (self.cancel_comment)

        cancel_data = json.dumps({
            'ack_code': self.ack_code,
            #'cancel_comment': self.cancel_comment,
            })

        order_2_cancel.write({
                'cancel_info': cancel_info_msg,
                'cancel_data': cancel_data,
                'need_cancel': True,
                'status_order_odoo': cancellation_status.id,
                })

        order_2_cancel.write_msg_to_log(user_action_message='sent cancel request to market channel')

class cancel_order_info_amazon_vendor(models.TransientModel):
    _name = 'storehouse.cancel_order_info_amazon_vendor'

    ack_sel = [
        ('ID', 'Item Deleted'),
        ('IR', 'Item Rejected'),
        ]

    cancel_comment = fields.Text(required=True)
    ack_code = fields.Selection(ack_sel, required=True)
    order_id = fields.Integer()

    @api.multi
    def write_cancel_info(self):
        _logger.debug('========= amazon vendor write_cancel_info ==========')

        order_2_cancel = self.env['storehouse.clients_order'].search([('id','=', self.order_id)])
        cancellation_status = self.env['storehouse.status'].search([('status','=','Cancellation')])

        if len(cancellation_status) == 0:
            cancellation_status = self.env['storehouse.status'].create({
                'status': 'Cancellation',
                })

        cancel_info_msg = '<p>Cancel comment: "%s"</p>' % (self.cancel_comment)

        cancel_data = json.dumps({
            'ack_code': self.ack_code,
            #'cancel_comment': self.cancel_comment,
            })

        order_2_cancel.write({
                'cancel_info': cancel_info_msg,
                'cancel_data': cancel_data,
                'need_cancel': True,
                'status_order_odoo': cancellation_status.id,
                })

        order_2_cancel.write_msg_to_log(user_action_message='sent cancel request to market channel')

class cancel_order_info_local(models.TransientModel):
    _name = 'storehouse.cancel_order_info_local'

    id = fields.Char()
    cancel_comment = fields.Text(required=True)
    #ack_code = fields.Selection(ack_sel, required=True)
    order_id = fields.Integer()

    @api.multi
    def write_cancel_info(self):
        _logger.debug('========= storehouse.cancel_order_info_local write_cancel_info ==========')
        order_2_cancel = self.env['storehouse.clients_order'].search([('id','=', self.order_id)])
        #_logger.debug(order_2_cancel)
        #_logger.debug(type(order_2_cancel))
        cancellation_status = self.env['storehouse.status'].search([('status','=','Cancellation')])
        canceled_status = self.env['storehouse.status'].search([('status','=','Canceled')])

        if len(cancellation_status) == 0:
            cancellation_status = self.env['storehouse.status'].create({
                'status': 'Cancellation',
                })
        if len(canceled_status) == 0:
            canceled_status = self.env['storehouse.status'].create({
                'status': 'Canceled',
                })

        if order_2_cancel.status_order_odoo.id != canceled_status.id:

            order_2_cancel.write({
                    'cancel_info': self.cancel_comment,
                    'status_order_odoo': cancellation_status.id,
                    })

            # some logic ...
            if order_2_cancel.customer_id.market_channel_type == 'local.settings':

                eq_2_warehouse_status = order_2_cancel.all_order_equipment_to_warehouse_button()

                if eq_2_warehouse_status:
                    order_2_cancel.write_msg_to_log(user_action_message='cancel this local order')
                    order_2_cancel.write({
                            'status_order_odoo': canceled_status.id,
                            'need_cancel': True,
                            })

                    self.env['storehouse.clients_order_2_canel'].create({
                        'customer': order_2_cancel.customer_id.id,
                        'order': order_2_cancel.id,
                        'cancel_data': self.cancel_comment,
                        'done': True,
                        })

                    return True
                else:
                    return False

            else:
                return False

        else:
            return False


class clients_order_set(models.Model):
    _name = 'storehouse.clients_order_set'
    _rec_name = 'set_id'

    id = fields.Char()
    set_id = fields.Many2one('storehouse.set')
    ordered_model = fields.Char()
    clients_order_id = fields.Many2one('storehouse.clients_order')
    quantity = fields.Integer() # ordered quantity
    total = fields.Float() #total price
    price = fields.Float()
    quantity_packed = fields.Integer()
    status = fields.Boolean(default=False)

    @api.multi
    def add_clients_order_set_info(self, info=False, order_id=False, customer_id=False):
        # info = {}
        if info and order_id and customer_id:

            #_logger.debug('--------------------------------------------------------')
            #_logger.debug(info)

            if 'odoo_set_id' in info:

                client_order_set = self.env['storehouse.clients_order_set'].create({
                            'set_id': int(info['odoo_set_id']),
                            'ordered_model': 'local_order',
                            'clients_order_id': int(order_id),
                            'quantity': int(info['quantity']),
                            'price': float(info['price']),
                            'total': int(info['quantity']) * float(info['price'])
                            })

                return client_order_set.id

            elif 'sku' in info:

                set_model = self.env['storehouse.set_model_additional'].search([
                    ('model', '=', info['sku']),
                    ('customer_id.id', '=', customer_id),
                    ])
                # uniq model_additional record in product record
                if len(set_model) == 1:
                    set_id = set_model.set_id
                    client_order_set = self.env['storehouse.clients_order_set'].create({
                                'set_id': set_id.id,
                                'ordered_model': info['sku'],
                                'clients_order_id': int(order_id),
                                'quantity': int(info['quantity']),
                                'price': float(info['price']),
                                'total': int(info['quantity']) * float(info['price'])
                                })
                    return client_order_set.id
                else:
                    return False

            else:
                return False

        return False

class clients_order_product(models.Model):
    _name = 'storehouse.clients_order_product'
    _rec_name = 'product_id'

    id = fields.Char()
    product_id = fields.Many2one('storehouse.product')
    ordered_model = fields.Char()
    clients_order_id = fields.Many2one('storehouse.clients_order')
    quantity = fields.Integer() # ordered quantity
    total = fields.Float() #total price
    price = fields.Float()
    quantity_packed = fields.Integer()
    status = fields.Boolean(default=False)
    #out_of_stock = fields.Boolean(default=False)

    @api.multi
    def add_clients_order_product_info(self, info=False, order_id=False, customer_id=False):
        # info = {}
        if info and order_id and customer_id:

            if 'odoo_product_id' in info:
                
                client_order_product = self.env['storehouse.clients_order_product'].create({
                                'product_id': int(info['odoo_product_id']),
                                'ordered_model': 'local_order',
                                'clients_order_id': int(order_id),
                                'quantity': int(info['quantity']),
                                'price': float(info['price']),
                                'total': int(info['quantity']) * float(info['price'])
                                })

                return client_order_product.id

            elif 'sku' in info:

                product_model = self.env['storehouse.product_models'].search([
                    ('model', '=', info['sku']),
                    ('customer.id', '=', customer_id),
                    ])
                # uniq model_additional record in product record
                if len(product_model) == 1:
                    product_id = product_model.product_id
                    client_order_product = self.env['storehouse.clients_order_product'].create({
                                'product_id': product_id.id,
                                'ordered_model': info['sku'],
                                'clients_order_id': int(order_id),
                                'quantity': int(info['quantity']),
                                'price': float(info['price']),
                                'total': int(info['quantity']) * float(info['price'])
                                })
                    return client_order_product.id
                else:
                    return False

            else:
                return False

        return False

class items_need_2_order(models.Model):
    _name = 'storehouse.items_need_2_order'
    _rec_name = 'product_id'

    _inherit = ['ir.needaction_mixin']

    id = fields.Char()
    clients_order_id = fields.Many2one('storehouse.clients_order')
    product_id = fields.Many2one('storehouse.product')
    price_per_product = fields.Float()
    ordered_quantity = fields.Integer()
    missing_quantity = fields.Integer()
    processed = fields.Boolean(default=False)
    #status = fields.Boolean(default=False)
    sup_order_id = fields.Many2one('storehouse.sup_order')

    status_sel = [
    ('1', 'need processing'),
    ('2', 'cancel'),
    ('3', 'include in general delivery'),
    ('4', 'separate delivery'),
    ]

    status = fields.Selection(status_sel, help='')

    @api.multi
    def get_total_product_quantity(self):
        for record in self:
            sys_config = self.env['storehouse.settings'].get_sys_config()

            if sys_config == 'products_virtual' or sys_config == 'box_inventory':
                record.total_quantity = record.product_id.quantity

            #elif sys_config == 'box_inventory':
            #    record.total_quantity = record.product_id.quantity

    total_quantity = fields.Integer(compute='get_total_product_quantity')

    @api.multi
    def get_sup_order_arrival_date(self):
        for record in self:
            if record.sup_order_id:
                record.arrival_date = record.sup_order_id.arrival_date

    arrival_date = fields.Datetime(compute='get_sup_order_arrival_date')

    #@api.model
    #def _needaction_domain_get(self):
    #    return [('processed', '=', False)]

    #@api.multi
    def remove_from_sup_order_action(self):
        self.write({
                'sup_order_id': False
                })

        msg = 'Record has been unliked, please refresh page'

        return {
            'name': 'Info',
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
    def remove_from_sup_order(self):
        # button action
        if self.sup_order_id:

            msg = "Do you want to unlink this record?"

            confirm_popup = self.env['storehouse.info_message'].confirm_action(msg,self,'remove_from_sup_order_action')

            return confirm_popup


    @api.multi
    def manual_processing(self):
        # button
        _logger.debug('----------------- manual processing --------------------')
        #_logger.debug(self.clients_order_id.id)
        if not self.sup_order_id:

            res = {
                'name': 'Supplier Order',
                'type': 'ir.actions.act_window', 
                'view_type': 'form', 
                'view_mode': 'form',
                'res_model': 'storehouse.items_need_2_order_manual_processing', 
                'target': 'new',
                'context': {
                    'default_clients_order_id': self.clients_order_id.id,
                    'default_item_need_2_order_id': self.id
                    }
                }

            msg = 'Add product to supplier orders?'

        else:

            res = {
                'name': 'Supplier Order',
                'type': 'ir.actions.act_window', 
                'view_type': 'form', 
                'view_mode': 'tree',
                'res_model': 'storehouse.sup_order',
                'domain': [('id', '=', self.sup_order_id.id)],
                #'res_id': self.sup_order_id.id,
                'target': 'new',
                'context': {},
                }

            msg = 'Product added earlier to supplier orders. Show details?'

        return {
            'name': 'Processing',
            'type': 'ir.actions.act_window', 
            'view_type': 'form', 
            'view_mode': 'form',
            'res_model': 'storehouse.info_message', 
            'target': 'new',
            'context': {
                'default_html': msg,
                'default_return_value': res,
                } 
            }
           
class items_need_2_order_manual_processing(models.TransientModel):
    _name = 'storehouse.items_need_2_order_manual_processing'

    clients_order_id = fields.Many2one('storehouse.clients_order')
    sup_order_id = fields.Many2one('storehouse.sup_order')
    item_need_2_order_id = fields.Many2one('storehouse.items_need_2_order')

    @api.multi
    def run_action(self):

        _logger.debug('----------------- Run WIzard Action --------------------')

        if self.sup_order_id and self.item_need_2_order_id:
            

            if not self.item_need_2_order_id.sup_order_id:

                #_logger.debug('------------------------------------')
                #_logger.debug(self.item_need_2_order_id.id)
                #_logger.debug('------------------------------------')

                self.item_need_2_order_id.write({
                    'sup_order_id': self.sup_order_id.id
                    })

            

                return {
                    'name': 'Supplier Order',
                    'type': 'ir.actions.act_window', 
                    'view_type': 'form', 
                    'view_mode': 'tree',
                    'res_model': 'storehouse.sup_order',
                    'domain': [('id', '=', self.sup_order_id.id)],
                    'target': 'new',
                    'context': {},
                    }

class status(models.Model):
    _name = 'storehouse.status'
    _rec_name = 'status'

    _sql_constraints = [
                     ('field_unique', 
                      'unique(status)',
                      'Choose another value for status - it has to be unique!')]

    id = fields.Char()
    status = fields.Char()

class sup_order(models.Model):
    _name = 'storehouse.sup_order'
    _rec_name = 'order_name'

    id = fields.Char()
    order_name = fields.Char()
    ship_date = fields.Datetime()
    arrival_date = fields.Datetime()

    sup_order_product = fields.One2many(
        'storehouse.sup_order_product',
        'sup_order_id'
        )

    items_need_2_order = fields.One2many(
        'storehouse.items_need_2_order',
        'sup_order_id'
        )

    status_sel = [
    ('1', 'opened'),
    ('2', 'finished'),
    ('3', 'submitted'),
    ('4', 'shipped'),
    ('5', 'awaiting time'),
    ('6', 'received'),
    ('7', 'stocked')
    ]
    status = fields.Selection(status_sel, help='Supplier Order Status')

    #volume = fields.Char(compute='compute_sup_order_boxes')
    #gross_weight = fields.Char(compute='compute_sup_order_boxes')

    #info = fields.Text(compute='compute_sup_order_boxes')
    log = fields.Text()
    #finished = fields.Boolean(compute='finished_action', store=True)
    finished = fields.Boolean(default=False)
    is_ordered = fields.Boolean(default=False)

    @api.multi
    @api.constrains('status')
    def finished_action(self):
        status_list = ['1','2','3','4','5','6']
        _logger.debug('+++++++++++++++++++++++++++++')
        _logger.debug(self.env.user.name)
        #_logger.debug(self.status)

        if not self.log:
            log = ''
        else:
            log = self.log

        status_sel = {
                        '1':'opened',
                        '2':'finished',
                        '3':'submitted',
                        '4':'shipped',
                        '5':'awaiting time',
                        '6':'received',
                        '7':'stocked',
                                        }
        if self.status:
            time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            status_2_log = status_sel[self.status]
            #_logger.debug(status_2_log)
            log += "<p>[%s \"UTC\"] User \"%s\" set order status to \"%s\"</p>" % (time, self.env.user.name, status_2_log)
        else:
            time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            log += "<p>[%s \"UTC\"] User \"%s\" unlink order status</p>" % (time, self.env.user.name)

        self.write({
            'log': log
            })




        #if self.status in status_list and self.is_ordered == False:
        if self.status in status_list:
            #_logger.debug('+++++++++++++++++++++++++++++')
            #_logger.debug(self.env.user.name)
            #_logger.debug(self.status)

            self.write({
                'is_ordered': True,
                'finished': False
                })



        #elif self.status == '7' and self.finished == False:
        elif self.status == '7':

            self.write({
                'finished': True
                })

class sup_order_product(models.Model):
    _name = 'storehouse.sup_order_product'

    id = fields.Char()
    sup_order_id = fields.Many2one('storehouse.sup_order')
    product_id = fields.Many2one('storehouse.product')
    quantity = fields.Integer()

class sup_order_box_tmp(models.Model):
    _name = 'storehouse.sup_order_box_tmp'

    id = fields.Char()
    sup_order_id = fields.Many2one('storehouse.sup_order')
    box_id = fields.Many2one('storehouse.box')
    quantity = fields.Integer()

class sup_order_box(models.Model):
    _name = 'storehouse.sup_order_box'

    id = fields.Char()
    sup_order_id = fields.Many2one('storehouse.sup_order')
    box_id = fields.Many2one('storehouse.box')
    quantity = fields.Integer()

class inventory_action(models.Model):
    _name = 'storehouse.inventory_action'

    id = fields.Char()
    box_barcode = fields.Char()
    cell_id = fields.Char()
    status = fields.Boolean(default=False)
    action = fields.Integer()

    @api.multi
    def run_inventory_action(self):
        info = []
        for record in self:
            msg = '------- inventory action id: %s -------' % (record.id)
            _logger.debug(msg)
            #product = self.env['storehouse.product'].search([('model', '=', 'ledtest')])
            info.append(msg)
        return info

class info_message(models.TransientModel):
    _name = 'storehouse.info_message'

    html = fields.Text()
    return_value = fields.Text()
    model = fields.Char() # table name
    method = fields.Char() # method
    model_id = fields.Integer() # object id

    @api.multi
    def ok_action(self):
        #_logger.debug('--------------------- OK BUTTON -------------------')
        #_logger.debug(self.return_value)
        if self.return_value:
            # return value must be dictionary (open view)
            res = ast.literal_eval(self.return_value)
            #_logger.debug(type(res))
            return res

        else:
            #_logger.debug('--------------------- OK BUTTON -------------------')

            if self.model and self.method:
                rec = self.env[self.model].search([('id', '=', self.model_id)])
                method = getattr(rec, self.method)
                res = method()
                if res:
                    return res
                #_logger.debug(method)


    def confirm_action(self, msg, obj, method):
        # msg - confirmation message
        # obj - db record
        # method - objec method

        record = self.env['storehouse.info_message'].create({
            'html': msg,
            'model': obj._description,
            'method': method,
            'model_id': obj.id,
            })

        res = {
                'name': 'Confirmation',
                'type': 'ir.actions.act_window', 
                'view_type': 'form', 
                'view_mode': 'form',
                'res_model': 'storehouse.info_message',
                'res_id': record.id,
                'target': 'new',
                'context': {} 
                }
        return res

class products_2_update(models.Model):
    _name = 'storehouse.products_2_update'

    id = fields.Char()
    create_date = fields.Datetime(readonly=True)
    customer = fields.Many2one('storehouse.customer')
    products = fields.Many2many('storehouse.product')
    sets = fields.Many2many('storehouse.set')
    in_work = fields.Boolean(default=False)
    done = fields.Boolean(default=False)
    info = fields.Text()

    @api.multi
    def get_customer_type(self):
        for record in self:
            record.customer_type = record.customer.market_channel_type

    customer_type = fields.Char(compute='get_customer_type')

    @api.multi
    def create_update_record_by_customer_all_products(self,customer_id=False):
        #_logger.debug('===== create_update_record_by_customer_all_products ======')
        if customer_id:

            customer = self.env['storehouse.customer'].search([
                ('id', '=', customer_id),
                ('status', '=', True),
                ('is_partner', '=', False),
                ])

            existing_record = self.search([
                ('customer', '=', customer.id),
                ('in_work', '=', False),
                ('done', '=', False),
                ])

            if not existing_record and customer.status and not customer.is_partner:
                                
                existing_record = self.create({
                    'customer': customer.id,
                    })

            #_logger.debug(existing_record)

            products = self.env['storehouse.product'].search([
                ('model_additional.customer.id', '=', customer.id),
                ])

            sets = self.env['storehouse.set'].search([
                ('model_additional.customer_id.id', '=', customer.id),
                ])

            if len(products) > 0:
                for product in products:

                    if product.status:
                        existing_record.write({
                            'products': [(4,[product.id])],
                            })

            if len(sets) > 0:
                for _set in sets:

                    if _set.status:
                        existing_record.write({
                            'sets': [(4,[_set.id])],
                            })

            #_logger.debug(products)
            #_logger.debug(type(sets))

            return True

        return False

    @api.multi
    def create_update_record(self, product_ids):

        customers = self.env['storehouse.customer'].search([
            ('status', '=', True),
            ('is_partner', '=', False),
            ])

        if len(customers) > 0:

            for product in product_ids:

                # product record
                if product.model_additional and product.status:

                    for record in product.model_additional:

                        for customer in record.customer:
                        #for customer in customers: # all customers

                            existing_record = self.search([
                                ('customer', '=', customer.id),
                                ('in_work', '=', False),
                                ('done', '=', False),
                                ])
                            #_logger.debug(existing_record)

                            if not existing_record and customer.status and not customer.is_partner:
                                
                                self.create({
                                    'customer': customer.id,
                                    'products': [(4,[product.id])],
                                    })

                            elif existing_record and customer.status and not customer.is_partner:
                                existing_record.write({
                                    'products': [(4,[product.id])],
                                    })

                            else:
                                pass

                # search product in set_equipment table
                set_equipment = self.env['storehouse.set_equipment'].search([
                        ('product_id.id', '=', product.id),
                        ])

                # set record
                if len(set_equipment) > 0 and product.status:

                    for set_eq in set_equipment:

                        #_logger.debug('=============  set_eq  ================')
                        
                        # check model_additional record
                        if set_eq.set_id and set_eq.set_id.model_additional:
                            
                            # models iteration
                            for record in set_eq.set_id.model_additional:
                                #_logger.debug(record.model)
                                #_logger.debug(record.customer_id)
                                #_logger.debug(record.set_id)

                                existing_record = self.search([
                                    ('customer', '=', record.customer_id.id),
                                    ('in_work', '=', False),
                                    ('done', '=', False),
                                    ])

                                if not existing_record and record.customer_id.status and not record.customer_id.is_partner:
                                
                                    self.create({
                                        'customer': record.customer_id.id,
                                        'sets': [(4,[record.set_id.id])],
                                        })

                                elif existing_record and record.customer_id.status and not record.customer_id.is_partner:

                                    existing_record.write({
                                        'sets': [(4,[record.set_id.id])],
                                        })
                                else:
                                    pass


    @api.multi
    def get_products_2_update(self, customer_id, action):

        sys_config = self.env['storehouse.settings'].get_sys_config()
        #_logger.debug(sys_config)

        #return False

        # optimize the search algorithm in the future
        def search_record(customer_id, in_work, done):

            record = self.search([
                ('customer', '=', customer_id),
                ('in_work', '=', in_work),
                ('done', '=', done)
                ])

            return record

        def get_model(product, customer):
            """select products 2 update by customer,
            return model or False"""
            models = []

            if product.model_additional:
                for record in product.model_additional:
                    for rec_customer in record.customer:
                        if rec_customer == customer:
                            #return record.model
                            models.append(record.model)

                if len(models) > 0:
                    return models
                else:
                    return False

            else:
                return False

        customer = self.env['storehouse.customer'].search([('id', '=', customer_id)])

        # no update records for "partners"
        if not customer.status or customer.is_partner or not customer:

            return False, 'customer.staus = False or customer.is_parner = True or unknown "customer_id"'

        if action == 'get':
          
            record = search_record(customer.id,False,False)

            record_inwork = search_record(customer.id,True,False)

            if record and not record_inwork:

                record.write({
                    'in_work': True,
                    })

                data = {}

                # product info to marketchannels
                for product in record.products:

                    if sys_config == 'box_inventory' or sys_config == 'products_virtual':
                        quantity = product.quantity

                    if product.is_discontinued and quantity == 0:
                        is_discontinued = 1
                    else:
                        is_discontinued = 0

                    #elif sys_config == 'products_virtual':
                    #    quantity = product.quantity_on_stock

                    model = get_model(product,customer)

                    if model:

                        data[str(product.id)] = [model, quantity, record.id, is_discontinued] # model (list) on m_channel, product quantity, prod_2_upd record id

                # set info to marketchannels
                for set_record in record.sets:

                    set_data = set_record.get_set_model_quantity(customer.id)

                    if set_data:
                        set_models_list = set_data[0]
                        set_quantity = set_data[1]
                        set_is_discontinued = set_data[2]

                        data['set_id_' + str(set_record.id)] = [set_models_list, set_quantity, record.id, set_is_discontinued]

                if len(data) > 0:
                    return data, [record.id, 'products data to update']
                else:
                    return False, 'no data to update!'

            else:

                record = search_record(customer.id,True,False)

                if record:

                    data = {}

                    # product info to marketchannels
                    for product in record.products:

                        if sys_config == 'box_inventory' or sys_config == 'products_virtual':
                            quantity = product.quantity

                        if product.is_discontinued and quantity == 0:
                            is_discontinued = 1
                        else:
                            is_discontinued = 0

                        #elif sys_config == 'products_virtual':
                        #    quantity = product.quantity_on_stock                        

                        model = get_model(product,customer)

                        if model:

                            data[str(product.id)] = [model, quantity, record.id, is_discontinued]

                    # set info to marketchannels
                    for set_record in record.sets:

                        set_data = set_record.get_set_model_quantity(customer.id)

                        if set_data:
                            set_models_list = set_data[0]
                            set_quantity = set_data[1]
                            set_is_discontinued = set_data[2]

                            data['set_id_' + str(set_record.id)] = [set_models_list, set_quantity, record.id, set_is_discontinued]

                    if len(data) > 0:
                        return data , [record.id, 'try again send products data to update']
                    else:
                        return False, 'no data to update!'

                else:

                    return False, 'no data to update!'

        if action == 'done':
            
            record = search_record(customer.id,True,False)

            if record:

                record.write({
                    'done': True,
                    })

                return True, [record.id, 'update data processed!']

            else:

                return False, 'no data to done!'

class edi_data(models.Model):
    _name = 'storehouse.edi'

    id = fields.Char()
    customer = fields.Many2one('storehouse.customer')
    edi_data = fields.Binary()
    edi_file_name = fields.Char()
    incoming = fields.Boolean(default=False)
    outgoing = fields.Boolean(default=False)
    is_processed = fields.Boolean(default=False)

    def create_edi_record(self, edi_id=False, file=False, customer_id=False, incoming=False, outgoing=False):
        if file and customer_id and not edi_id:
            path, filename = os.path.split(file)

            existing_record = self.search([
                ('edi_file_name','=',filename),
                ('customer','=',customer_id),
                ])

            if len(existing_record) == 0:

                f = open(file, "rb")
                f_out = f.read()
                f.close()

                record = self.create({
                    'customer': customer_id,
                    'edi_data': base64.b64encode(f_out),
                    'edi_file_name': filename,
                    'incoming': incoming,
                    'outgoing': outgoing,
                    })

                return record

            elif len(existing_record) == 1:
                return existing_record
            else:
                return False

        elif file and customer_id and edi_id:
            path, filename = os.path.split(file)

            record = self.search([('id','=', edi_id),])

            f = open(file, "rb")
            f_out = f.read()
            f.close()
            
            record.write({
                'customer': customer_id,
                'edi_data': base64.b64encode(f_out),
                'edi_file_name': filename,
                'incoming': incoming,
                'outgoing': outgoing,
                })

            return record


                #pass
                #_logger.debug('---------=========')
                #_logger.debug(existing_record.edi_file_name)

    def get_unprocessed_records(self, customer_id=False):
        if customer_id:
            records = self.search([
                ('customer','=',customer_id),
                ('is_processed','=',False),
                ])
            if len(records) > 0:
                return records
            else:
                return False

class edi_997(models.Model):
    _name = 'storehouse.edi_997'
    _inherit = 'storehouse.edi'

class edi_846(models.Model):
    _name = 'storehouse.edi_846'
    _inherit = 'storehouse.edi'
    edi_997 = fields.Many2one('storehouse.edi_997')

class edi_850(models.Model):
    _name = 'storehouse.edi_850'
    _inherit = 'storehouse.edi'
    edi_997 = fields.Many2one('storehouse.edi_997')

class edi_856(models.Model):
    _name = 'storehouse.edi_856'
    _inherit = 'storehouse.edi'
    edi_997 = fields.Many2one('storehouse.edi_997')

class edi_855(models.Model):
    _name = 'storehouse.edi_855'
    _inherit = 'storehouse.edi'
    edi_997 = fields.Many2one('storehouse.edi_997')

class edi_810(models.Model):
    _name = 'storehouse.edi_810'
    _inherit = 'storehouse.edi'
    edi_997 = fields.Many2one('storehouse.edi_997')

class to_do(models.Model):
    _name = 'to_do.tasks'
    _inherit = ['ir.needaction_mixin']
    _rec_name = 'name'

    id = fields.Char()
    name = fields.Char()
    task = fields.Text()
    note = fields.Text()
    status = fields.Boolean()
    #priority = fields.Integer(default=0)
    priority = fields.Selection([
        ('1', 'Very Low'),
        ('2', 'Low'),
        ('3', 'Medium'),
        ('4', 'High'),
        ('5', 'Very High'),])

    @api.multi
    def priority_as_str(self):
        for rec in self:
            if rec.priority:
                if rec.priority:
                    rec._priority = int(rec.priority[0]) * '★'
                #if rec.priority and rec.status:
                #    rec._priority = int(rec.priority[0]) * '★'
                #else:
                #    rec._priority = int(rec.priority[0]) * '☆ ⚝ '
            else:
                rec._priority = '--'

    _priority = fields.Char(compute='priority_as_str')

    @api.model
    def _needaction_domain_get(self):
        return [('status', '=', False)]

class mail_server_users(models.Model):
    _name = 'storehouse.mail_server_users'
    
    id = fields.Char()
    odoo_user = fields.Many2one('res.users')
    email = fields.Char()
    status = fields.Boolean(default=True)

    def send_mail_2_all(self,message,subject):
        #_logger.debug('==++++++++++++++++++++++++++++++++++++++++++===')
        if message and subject:
            users = self.search([])
            for user in users:
                if user.email and user.odoo_user.active:
                    # all active users
                    if user.status:
                        status = user.send_mail_storehouse(message,subject,user.email)
                else:
                    pass

            return True
        else:
            return False

    def send_mail_storehouse(self,message,subject,client_email):
        #_logger.debug('------- mail server logger message ---------')

        ir_mail_server = self.env['ir.mail_server'].search([])

        #msg = MIMEText(message.encode('utf-8'), 'plain', 'UTF-8') # plain text
        msg = MIMEText(message.encode('utf-8'), 'html', 'UTF-8')
        
        for server_data in ir_mail_server:

            msg['Subject'] = subject
            msg['From'] = server_data.smtp_user
            msg['To'] = client_email
            #msg['Content-Type'] = "text/html; charset=us-ascii"

            smtp_host = server_data.smtp_host
            smtp_port = server_data.smtp_port
            smtp_user = server_data.smtp_user
            smtp_pass = server_data.smtp_pass

            server = smtplib.SMTP(smtp_host,smtp_port)
            server.ehlo()
            server.starttls()
            a = server.login(smtp_user, smtp_pass)
            _logger.debug(a)
            b = server.sendmail(server_data.name, [client_email,], msg.as_string())
            _logger.debug(b)
            server.close()

        return True



#class m2mreltest(models.Model):
#   _name = 'storehouse.m2mreltest'
#
#   table1 = fields.Many2one('storehouse.clients_order')
#   table2 = fields.Many2one('storehouse.product')if notor