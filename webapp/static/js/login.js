const dom_modal = document.getElementById('password-modal');
const modal = new bootstrap.Modal(dom_modal, {
    'backdrop': 'static' /* prevents clicking outside of modal dismissing it */
});

/* workaround to ensure modal input gets focused */
dom_modal.addEventListener('shown.bs.modal', function () {
    const password_field = $("#modal-password-field")[0];
    const password_input = $("input[name=password]")[0];
    password_field.value = password_input.value; /* compatibility with password managers */
    password_field.focus();
})

function submit_from_modal()
{
    const password_field = $("#modal-password-field")[0];
    const password_input = $("input[name=password]")[0];
    password_input.value = password_field.value;
    $('form[name=login-form]')[0].submit();
}

/* workaround to ensure pressing enter in modal submits */
$('.modal-content').keypress(function(e){
    if(e.which == 13) {
      /* enter has been pressed */
      submit_from_modal();
    }
})

$('#modal-submit').click(submit_from_modal);

/* water-tight method to add url parameter without clobbering others - from stackoverflow */
function url_add_parameter(url, param, value){
    var hash       = {};
    var parser     = document.createElement("a");

    parser.href    = url;

    var parameters = parser.search.split(/\?|&/);

    for(var i=0; i < parameters.length; i++) {
        if(!parameters[i])
            continue;

        var ary      = parameters[i].split("=");
        hash[ary[0]] = ary[1];
    }

    hash[param] = value;

    var list = [];
    Object.keys(hash).forEach(function (key) {
        list.push(key + "=" + hash[key]);
    });

    parser.search = "?" + list.join("&");
    return parser.href;
}

function show_password_modal()
{
    modal.show();
}

function show_message(mid)
{
    window.location.href = url_add_parameter(window.location.href, "mid", mid);
}

function show_processing()
{
    $("#form-submit")[0].innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="visually-hidden">Loading...</span>';
}

function decide_submission(locked, requires_password)
{
    if (locked)
    {
        show_message(3);
    }
    else
    {
        show_processing();
        if (requires_password)
        {
            show_password_modal();
        }
        else
        {
            $('form[name=login-form]')[0].submit();
        }
    }
}

$('form[name=login-form]').submit(function(e) {
    e.preventDefault();
    const form_data = new FormData(e.target);
    const code = form_data.get("code");
    if (code.length == 8)
    {
        $.get("/api/auth/probe", { code: code })
         .done(function(result) {
            const locked = result["locked"];
            const requires_password = result["requires_password"];
            decide_submission(locked, requires_password);
         })
         .fail(function(jqXHR, textStatus, errorThrown) {
            const status_code = jqXHR.status;

            /* code not found */
            if (status_code == 404)
            {
                show_message(1);
            }
            /* rate limiter in effect found */
            else if (status_code == 429)
            {
                show_message(10);
            }
            /* unknown error occurred */
            else
            {
                show_message(9);
            }
         });
    }
    else
    {
        console.log("skipped probing as code was invalid");
    }
});