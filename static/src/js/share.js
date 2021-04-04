
openerp.portnet_newtarification = function(session) {
    var _t = session.web._t;
    var has_action_id = false;
    session.web.Sidebar = session.web.Sidebar.extend({
    	start: function() {
            var self = this;
            this._super(this);
            if ($('.oe_share')['length']){
                var str1 = self.items.other[1]["classname"];
                var str2 = " custom_class_display";
                var res = str1.concat(str2);
                self.items.other[1]["classname"] = res
            }
       },
    });
};
