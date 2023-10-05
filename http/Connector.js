"use strict";
//
// adapted from https://github.com/TrueWatcher/mozchat/blob/master/assets/Connector_3_6_2.js
//
tgc.Connector=function(serverParams, userParams) {
  var _this=this,
      pullCallbacks=[],
      pushCallbacks=[];
  
  var viewC={
    showMessageP: function(m) { $("alertBlP").innerHTML=m; },
    showMessageR: function(m) { $("alertBlP").innerHTML=m; },
    uploadIndicatorR: new tgc.utils.Indicator("uploadIndBtn", [["","auto"], ["","ye"]] ),
    onHangR: function() { $("alertBlP").innerHTML="Request timed out"; },
    onPollhangsP: function() { $("alertBlP").innerHTML="The poll request has timed out"; }    
  };
  
  this.echo="echo";
      
  this.push=new tgc.Connector.PushLink(serverParams.pathBias+"a", pushCallAllBack, viewC.onHang,  serverParams, userParams, viewC.uploadIndicatorR);

  this.push.registerPushCallback=function(cb) {
    if ( ! cb instanceof Function) throw new Error("Wrong CB type="+(typeof cb));
    pushCallbacks.push(cb);
  };
  
  function pushCallAllBack(respObj) {
    var i=0, l=pushCallbacks.length;
    //if (l == 0) throw new Error("No callbacks found");
    for (; i < l; i+=1) { pushCallbacks[i](respObj); }    
  }  
  
  this.pull=getPullLink(tgc.serverParams.wsOn);
  
  this.pull.registerPullCallback=function(cb) {
    if ( ! cb instanceof Function) throw new Error("Wrong CB type="+(typeof cb));
    pullCallbacks.push(cb);
  };
  
  function getPullLink(websocketsOn) {
    if (websocketsOn) {
      return new tgc.utils.WsClient(onWsconnected, callAllBack, viewC.onPollhangsP, userParams, serverParams, _this.push);
    }
    else {
      return new tgc.utils.Poller(serverParams.pathBias+"poll", callAllBack,  viewC.onPollhangsP, userParams, serverParams);
    }    
  }
  
  function onWsconnected() {
    //console.log("requesting the catalog from uplink");
    //_this.push.sendGetCatalog();
  }
  
  function callAllBack(respObj) {
    var i=0, l=pullCallbacks.length;
    //if (l == 0) throw new Error("No callbacks found");
    for (; i < l; i+=1) { pullCallbacks[i](respObj); }    
  }
  
  this.pullReinit=function() {
    _this.pull.stop();
    _this.pull=getPullLink(tgc.serverParams.wsOn); 
  };
  
};

tgc.utils.Ajaxer=function (responderUrl,onDataReceived,indicator,onTimeout) { //NEW
  if (typeof onDataReceived != "function") throw new Error("Non-function callback argument");
  if ( ! indicator.on) indicator={on:function(){}, off:function(){}}; 
  var urlOffset="";
  if (typeof URLOFFSET != "undefined") urlOffset=URLOFFSET;
  var lag=0, timer=false, busy=false, watch=false;
  var transports=["post", "posturle" ,"postmulti", "postfd", "get", "jsonp"];
  var queue=[], queueMax=15;
  
  var _this=this, req;
  
  this.transport=null;
  
  // query string or Form
  this.postRequest=function(stuff, timeoutMs, method) {
    if (typeof method == "undefined") method=_this.transport; 
    if ( ! stuff) throw new Error ("no data");
    if ( enqueueMsg(stuff, method) ) return;
    // unconditional entry point for from-queue messages
    doPostRequest(stuff, timeoutMs, method);
  };
  
  function doPostRequest(stuff, timeoutMs, method) {
    if (typeof method == "undefined" || method.indexOf("post") < 0) throw new Error("Wrong METHOD="+metod+" -- cannot set encoding");
    timer=Date.now();
    req=new XMLHttpRequest();
    req.open("POST",urlOffset+responderUrl,true); // POST
    //console.log("ENCODING="+method);
    if (method == "postmulti") req.setRequestHeader("Content-Type","multipart/form-data");// for POST; should go _after_ req.open!
    else if (method == "posturle") req.setRequestHeader("Content-Type","application/x-www-form-urlencoded");
    req.onreadystatechange=receive;// both
    indicator.on();
    busy=true;
    if (timeoutMs && onTimeout) {
      watch=window.setTimeout(_this.timeoutInner, timeoutMs);
    }
    //console.log("posting "+stuff);
    var q=req.send(stuff); // POST
  }
  
  // queryString or urlencoded queryString
  this.getRequest=function(queryString,timeoutMs) {
    if (enqueueMsg(queryString, "get")) return;
    doGetRequest(queryString,timeoutMs);
  };
  
  function doGetRequest(queryString,timeoutMs) {
    timer=Date.now();
    req=new XMLHttpRequest();
    var uriForGet=urlOffset+responderUrl+"?"+queryString; // GET
    req.open("GET", uriForGet); // GET
    req.onreadystatechange=receive;// both
    indicator.on();
    busy=true;
    if (timeoutMs && onTimeout) {
      watch=window.setTimeout(_this.timeoutInner, timeoutMs);
      //console.log("watching for "+timeoutMs);
    } 
    var q=req.send(null); // GET
  }
  
  var globalJsonpReceiverName=false;
  
  this.initJsonp= function() {
    if ( ! acceptMessage instanceof Function) throw new Error("Missing global receiver function (expected acceptMessage)");
    acceptMessage=_this.receiveJsonp;
    globalJsonpReceiverName="acceptMessage";
  };
  
  this.jsonpRequest=function(queryString,timeoutMs) {
    if (enqueueMsg(queryString, "jsonp")) return;
    doJsonpRequest(queryString,timeoutMs);
  };
  
  function doJsonpRequest(queryString,timeoutMs) {
    if ( ! globalJsonpReceiverName) _this.initJsonp();
    timer=Date.now();
    req = document.createElement("script");
    var uriForGet=urlOffset+responderUrl+"?"+queryString;
    uriForGet += "&jsonpWrapper="+globalJsonpReceiverName;
    req.setAttribute("src", uriForGet);
    indicator.on();
    busy=true;
    if (timeoutMs && onTimeout) {
      watch=window.setTimeout(_this.timeoutInner, timeoutMs);
      //console.log("watching for "+timeoutMs);
    }
    document.head.appendChild(req);
    document.head.removeChild(req);
    req = null;
  }
  
  function enqueueMsg(stuff, method) {
    if ( queueMax <= 0 && busy) throw new Error("Ajaxer "+responderUrl+" is busy");
    if ( queue.length == 0 && ! busy) return false; // if there is queue, put it there
    if (queue.length+1 >= queueMax) throw new Error("Ajaxer "+responderUrl+" is overflown");
    queue.push({ msg: stuff, method : method });
    console.log("Ajaxer "+responderUrl+": queued "+queue.length+"th message");
    return true;
  }
  
  this.postAsFormData=function(msgObj, to, method) {
    if ( ! method) method="postfd";
    var fd=new FormData(), p;
    for (p in msgObj) {
      if (msgObj.hasOwnProperty(p)) fd.append(p, msgObj[p]);
    }
    this.postRequest(fd, to, method);
  };
  
  this.sendAsJson=function(msgObj, to) { alert("redefine me!"); };
  
  this.setTransport=function(t) {
    if (transports.indexOf(t) < 0) throw new Error("Unknown transport:"+t);
    this.transport=t;
    //alert(transport);
    if (t == "postfd") {
      _this.sendAsJson=function(msgObj, to) {
        var msgObj = { json : JSON.stringify(msgObj) };
        _this.postAsFormData(msgObj, to);
      };
    }
    else if (t.indexOf("post") === 0) {
      _this.sendAsJson=function(msgObj, to) {
        var msgPost = "json="+JSON.stringify(msgObj);
        _this.postRequest(msgPost, to, t);
      };
    }
    else if (t == "get") {
      _this.sendAsJson=function(msgObj, to) {
        var msgGet = "json="+encodeURIComponent(JSON.stringify(msgObj));
        _this.getRequest(msgGet, to);
      };
    }
    else if (t == "jsonp") {
      _this.sendAsJson=function(msgObj, to) {
        var msgGet = "json="+encodeURIComponent(JSON.stringify(msgObj));
        _this.jsonpRequest(msgGet, to);
      };
    }
  };  
  this.setTransport("posturle");
  
  this.setQueueMax=function(n) { queueMax=n; };
  
  this.timeoutInner=function() {
    _this.reset();
    onTimeout();
  }
  
  this.reset=function() {
    if (req) req.abort();
    busy=false;
    indicator.off();
  };
  
  function receive() {
    var rdata,rmime;
    var fromQueue;
    
    if (req.readyState != 4) return;
    if (watch) clearTimeout(watch);
    lag=Date.now()-timer;
    indicator.off();
    busy=false;
    if (req.status != 200 && req.status != 204 && req.status != 304) {
      console.log(responderUrl+" ajax returned error "+req.status);
      req=null;
      return;
    }
    if (req.status != 200  && req.status != 304) {
      console.log("ajax returned code "+req.status);
      //onDataReceived(req.status);
      req=null;
      return;
    }
    if (req.status == 304) {
      //console.log("304 "+lag);
      onDataReceived({ alert : "No changes", lag : lag });
      req=null;
      return;
    }
    rdata=req.responseText;
    rmime=req.responseType;
    req=null;
    //alert(rmime);
    if (rmime === "" || rmime == "json" || rmime == "text") rdata=tryJsonParse(rdata);
    tryTakeFromQueue();
    onDataReceived(rdata);
    //setTimeout(function() { onDataReceived(rdata) }, 0);
  }
  
  this.receiveJsonp=function(responseObj) {
    var rdata,rmime;
    var fromQueue;
    lag=Date.now()-timer;
    if (watch) clearTimeout(watch);
    indicator.off();
    busy=false;
    rdata=responseObj;
    //req=null; // not good -- req needed for removeChild;
    tryTakeFromQueue();
    rdata.lag=lag;
    onDataReceived(rdata);
  }
  
  function tryTakeFromQueue() {
    if ( queueMax <= 0 || queue.length == 0) { busy=false; return false; }
    var fromQueue=queue.shift();
    busy=true;
    setTimeout(function() {
      console.log("Ajaxer "+responderUrl+": unqueued a message, "+queue.length+" remain");
      if (fromQueue.method.indexOf("post") === 0) doPostRequest(fromQueue.msg, 0, fromQueue.method); 
      else if (fromQueue.method == "get") doGetRequest(fromQueue.msg);
      else if (fromQueue.method == "jsonp") doJsonpRequest(fromQueue.msg);
      else throw new Error("Unknown method: "+fromQueue.method);         
    }, 100);
    return true;
  }
  
  function tryJsonParse(responseText) {
    if ( ! responseText) return responseText;
    var responseObj={};
    try { 
      responseObj=JSON.parse(responseText); 
    }
    catch (err) {
      //alert ("Unparsable server response:"+responseText);
      console.log("Unparsable server response:"+responseText);
      return responseText;
    }
    if (typeof responseObj === 'string' || responseObj instanceof String) {
      responseObj={alert: responseObj};
    }
    responseObj.lag=lag;
    return responseObj;
  }
  
  this.getLag=function() { return lag; };
  
  this.isBusy=function() {
    if (queueMax <= 0) return busy;
    var remains=(queueMax-queue.length  < 1);
    return remains;
  };
  
};// end Ajaxer

tgc.utils.WsClient=function(onConnect, onData, onHang, userParams, serverParams, upConnection, connectAtOnce) {
  //console.log("serverParams.wsServerUri");
  var conn={onopen:notReady, onmessage:notReady, send:notReady},
      myHello=JSON.stringify({user:serverParams.user, realm:serverParams.realm, act:"userHello"}),
      pollFactor=15000;
  var response=[], intervalHandler=false;
  if (typeof connectAtOnce == "undefined") connectAtOnce=true;
  
  function notReady() { throw new Error("The object is not ready"); }
  
  this.connect=function() {    
    conn=new WebSocket(serverParams.wsServerUri);//'ws://localhost:8080'
    
    conn.onerror = function(e) {
      alert("Something is wrong with your Websockets connection. Reload the page");
      if (wss2https()) {
        $("accountTopAlertP").innerHTML='<a href="'+wss2https()+'" target="_blank">Please, check WS certificate</a>';
      }
    };
    
    conn.onopen = function(e) {
      console.log("Ws connection established!");
      setTimeout(function() {
        //console.log(myHello);
        conn.send(myHello); }
      ,200);
      setTimeout(onConnect,500);
    };

    conn.onmessage = function(e) {
      //console.log(e.data);
      response=JSON.parse(e.data);
      onData(response);
    };    
  };  
  if (connectAtOnce) this.connect();
  
  this.disconnect=function() {
    conn.close();
    conn={onopen:notReady, onmessage:notReady, send:notReady};   
  };
  
  this.sendData=function(data) { conn.send(data); }; 
  this.linkIsBusy=function() { return false; };  
  this.getResponse=function() { return response; };
  
  if (userParams.pb.pollFactor != "off") {
    intervalHandler=setInterval(function() {
      upConnection.sendGetCatalog(pollFactor);
    }, pollFactor);
  }
  
  function wss2https() {
    var uri=serverParams.wsServerUri;
    if (uri.indexOf("ws://") === 0) return false;
    if (uri.indexOf("wss://") === 0) return uri.replace("wss://", "https://");
    throw new Error("Wrong ws uri="+uri);
  }
  
  this.stop=function() {
    if (intervalHandler) clearInterval(intervalHandler);
  };
  
  this.sendRelay=function(msgObj) {
    msgObj.act="relay";
    msgObj.user=serverParams.user;
    msgObj.realm=serverParams.realm;
    this.sendData(JSON.stringify(msgObj));
  };
  
};

tgc.Connector.PushLink=function(respondrUri, onData, onHang, serverParams, userParams, indicator) {
  var _this=this;
  var ajaxerR=new tgc.utils.Ajaxer(respondrUri, onData, indicator, onHang);
  
  this.linkIsBusy=function() { return ajaxerR.isBusy(); };
  this.setQueueMax=function(n) { ajaxerR.setQueueMax(n); };
  
  this.sendCommandWGet = function(cmdArr, dn) {
    if ( ! cmdArr[0]) throw new Error("Wrong ACT:"+cmdArr[0]);
    var cmdArrStr = JSON.stringify(cmdArr);
    var stuff = { command: cmdArrStr };
    var queryString = 'command='+cmdArrStr;
    if (dn) queryString += '&dialog='+dn;
    console.log(queryString);
    ajaxerR.getRequest(queryString);
  };
  
  this.sendGetBuddies = function() {
    this.sendCommandWGet(["getBuddies"]);
  };
  
  this.sendGetDialog = function(dn) {
    this.sendCommandWGet(["getDialog", dn], dn);
  };
  
  this.sendSelectDialog = function(target, current) {
    this.sendCommandWGet(["selectDialog", 'n', target], current);
  };
  
  this.sendReloadDialog = function(dn) {
    this.sendCommandWGet(["reloadDialog", dn], dn);
  };
  
  this.sendMessage = function(dn, text, replyTo='') {
    //this.sendCommandWGet(["sendMessage", dn, text], dn);
    var stuff = { command:'sendMessage', dialog: dn, text: text, replyTo: replyTo };
    ajaxerR.postAsFormData(stuff);
  };
  
  this.sendDeleteMessage = function(dn, id, forAll) {
    this.sendCommandWGet(["deleteMessage", dn, 'id', id, forAll], dn);
  };
  
  this.sendPing = function(dn) {
    this.sendCommandWGet(["echo"]);
  };
  
  this.sendFile = function(dn, caption, file, replyTo='') {
    if ( ! file instanceof File) throw new Error("Not a file:"+file+"!");
    var stuff = { command:'sendFile', dialog: dn, text: '', replyTo: replyTo, fileName: file.name, file: file };
    if (caption) stuff.text = caption;
    ajaxerR.postAsFormData(stuff);
  };
  
  this.sendDownloadMedia = function(dn, id) {
    this.sendCommandWGet(["downloadFile", dn, 'id', id], dn);
  };
  
  this.sendReloadAll = function() {
    this.sendCommandWGet(["reloadAll"], '');
  };
  
  this.sendListDialogs = function(dn) {
    this.sendCommandWGet(["listDialogs", dn], dn);
  };
  
  this.sendSave = function(dn) {
    this.sendCommandWGet(["exit", 'save', dn], dn);
  };
  
  this.sendAck = function(dn, msgId) {
    this.sendCommandWGet(["ackNewMessage", dn, msgId], dn);
  };
  
};
