odoo.define('max_web_hide_list_view_import.max_web_hide_list_view_import', function (require) {
'use strict';
    var session = require('web.session');
    var ListView = require('web.ListView');

     ListView.include({
        render_buttons: function() {
            var self = this;
            this._super.apply(this, arguments);
            if (session.uid)
                self.$buttons.find('.o_button_import').hide();
            return this.$buttons;
        },
    });
});
