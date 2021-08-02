function show_processing()
{
    $("#form-submit")[0].innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="visually-hidden">Loading...</span>';
}
$('form[name=setup-form]').submit(function(e) {
    show_processing();
});