const editorArea = document.getElementById("editor-area");
const outputArea = document.getElementById("output-area");
const actionBar = $("#action-bar");
const textboxContainer = $("#textbox-container");

var editor = CodeMirror.fromTextArea(editorArea, {
    lineNumbers: true,
    mode: "python",
    pythonVersion: 3,
    theme: "darcula",
    indentWithTabs: true,
    autofocus: true,
    lineWrapping: false
});
var output = CodeMirror.fromTextArea(outputArea, {
    readOnly: true,
    theme: "darcula",
    lineWrapping: true
});

function set_textbox_heights(v)
{
    /* todo: constrain width as well */
    editor.setSize(null, v);
    output.setSize(null, v);
}

function calc_texteditor_size() {
    const rawHeight = $(document).height() - actionBar.height();
    const height = rawHeight - (rawHeight * 0.01) - 50;
    set_textbox_heights(height);
}

calc_texteditor_size();
$(window).resize(calc_texteditor_size);
