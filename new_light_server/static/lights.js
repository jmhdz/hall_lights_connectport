function updateColor(name,button) 
{
    var cb = document.getElementById(name+"_check");
    if (!cb || !cb.checked) {
        return;
    }
    var in1=document.getElementById(name+"_color");
    if (button.valueElement && button.valueElement.id == name+"_color2") {
        in1.color.fromString(button.toString());
    } else {
        var in2=document.getElementById(name+"_color2");
        in2.color.fromString(in1.value);
    }
    if (button == cb) {
        hidden_submit(button.form, null);
    }
}

function hidden_submit(form,control)
{
    if (control && control.color) {
        control.color.hidePicker();
    }
    var action = form.action;
    if (action.length == 0) {
        action = window.location.href;
    }
    var inputs = form.getElementsByTagName("INPUT");
    var conjunct="?";
    for (var i=0; i < inputs.length; ++i) {
        var input = inputs.item(i);
        if (input.name) {
            action = action + conjunct;
            conjunct='&';
            action = action+input.name + "=" + input.value;
        }
    }
    xmlhttp = new XMLHttpRequest();
    xmlhttp.open(form.method, action, false);
    xmlhttp.send();
    return false;
}

function handleUpdates()
{
    var xmlhttp = new XMLHttpRequest();
    var loc = window.location;
    loc.path="/query";
    loc.search="";
    
    xmlhttp.open(loc, "GET", false);
    xmlhttp.send();
    var result = eval(xmlhttp.responseText);
    if (!result) {
        return;
    }
	for (var node in result["nodes"]) {
        if (!node["name"]) {
            continue;
        }
        var name = encodeURI(node["name"]);
        if (node["color"]) {
            var obj = document.getElementsById(name+"_color");
            if (obj && jscolor.picker.owner != obj.color) {
                obj.color.fromString(node["color"]);
            }
        }
        if (node["color2"]) {
            var obj = document.getElementsById(name+"_color2");
            if (obj && jscolor.picker.owner != obj.color) {
                obj.color.fromString(node["color2"]);
            }
        }
    }
}

function startUpdates()
{
    window.setInterval("handleUpdates()", 10000);
}

function setAllLights(color,form)
{
    var inputs = form.getElementsByTagName("INPUT");
    for (var i=0; i < inputs.length; ++i) {
        var input = inputs.item(i);
        if (input.color) {
            input.color.fromString(color);
        }
    }
    hidden_submit(form, null);
}

function stopSequence(name)
{
    var action = "/stopsequence?name="+name;
    xmlhttp = new XMLHttpRequest();
    xmlhttp.open("PUT", action, false);
    xmlhttp.send();
}

function playSequence(name)
{
    var action = "/playsequence?name="+name;
    xmlhttp = new XMLHttpRequest();
    xmlhttp.open("PUT", action, false);
    xmlhttp.send();
}

function recordSequence(name)
{
    var action = "/sequence/"+name;
    window.location=action;
}

