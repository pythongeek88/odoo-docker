 odoo.define('upload_products_csv.upload_products_csv', function (require){
"use strict";
 
/* 
var core = require('web.core');
var ListView = require('web.ListView');
var QWeb = core.qweb;
 
 
ListView.include({       
     
        render_buttons: function($node) {
                var self = this;
                this._super($node);
                    this.$buttons.find('.o_list_button_import_csv').click(this.proxy('tree_view_action'));
        },
 
        tree_view_action: function () {           
                 
        this.do_action({               
                type: "ir.actions.act_window",               
                name: "product",               
                res_model: "product.template",               
                views: [[false,'form']],               
                target: 'current',               
                view_type : 'form',               
                view_mode : 'form',               
                flags: {'form': {'action_buttons': true, 'options': {'mode': 'edit'}}}
        });
        return { 'type': 'ir.actions.client','tag': 'reload', } }

 
});
*/

    var session = require('web.session');
    var ListView = require('web.ListView');

     ListView.include({
        render_buttons: function() {
            var self = this;
            this._super.apply(this, arguments);
            //if (session.uid != 1)
            if (session.uid)
                //self.$buttons.find('.o_button_import').hide();
                console.log('test js new button')

            return this.$buttons;
        },
    });

});