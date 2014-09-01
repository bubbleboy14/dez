// utility function lifted from cantools
var inputEnterCallback = function(n, cb, fid) {
    n.onkeyup = function(e) {
        e = e || window.event;
        var code = e.keyCode || e.which;
        if (code == 13 || code == 3) {
            // can prevent annoying repeating alert on enter scenarios
            if (fid)
                document.getElementById(fid).focus();
            cb(n.value);
        }
    };
};

onload = function () {
    var inNode = document.getElementById("in");
    var outNode = document.getElementById("out");
    var log = function(msg) {
	var msgnode = document.createElement("div");
        msgnode.innerHTML = msg;
        outNode.appendChild(msgnode);
    };

    var ws = new WebSocket("ws://localhost:8888");
    ws.onopen = function(val) {
        log("OPEN: " + JSON.stringify(val));
    };
    ws.onclose = function(val) {
        log("CLOSE: " + JSON.stringify(val));
    };
    ws.onmessage = function(val) {
        log("RECV: " + JSON.stringify(val));
    };
    ws.onerror = function(val) {
        log("ERROR: " + JSON.stringify(val));
    };
    inputEnterCallback(inNode, function(val) {
    	log("SEND: " + val);
    	inNode.value = "";
    	ws.send(val);
    });
};