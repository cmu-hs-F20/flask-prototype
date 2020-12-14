
$(document).ready(function () {
    $.fn.selectpicker.Constructor.DEFAULTS.whiteList.a.push('data-toggle');
    $("body").tooltip({ selector: '[data-toggle=tooltip]' });
});