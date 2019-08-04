odoo.define('no_open_tree_view.no_open_tree_view', function (require) {
'use strict';
    var session = require('web.session');
    var ListView = require('web.ListView');

     ListView.include({
        row_clicked: function (e, view) {
            if( this.view.is_action_enabled('open') )
                this._super.apply(this, arguments);
        },
    });
});
