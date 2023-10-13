"use strict";

tgc.View = function() {
  var _this = this,
      argMax = 3,
      dn = false,
      buddyIdPrefix = "bd_",
      messageIdPrefix = "msg_",
      mediaHrefPrefix = "media_",
      hideable=document.getElementsByClassName("hideable"),
      showMore=0;
      
  function getShowMore() { return showMore; }
  function setShowMore(s) { showMore=s; }
  
  this.setDn = function(s) {
    if ( ! s) {
      throw new Error("trying to set empty dialog name");
    }
    dn = s;
  };
  this.clearDn = function(s) { dn = false; };
  this.getDn = function(s) { return dn; };
  
  this.showDialogPanel = function() { $("dialogFs").style.display = ''; };
  this.hideDialogPanel = function() { $("dialogFs").style.display = 'none'; };
  
  this.showAlertB = function(msg) { $("alertBlP").innerHTML = msg; };
  this.showAlertD = function(msg) { $("alertDiaP").innerHTML = msg; };
  
  this.showBuddies = function(buddyList) {
    //$("buddyListD").innerHTML = "List of "+buddyList.length+" buddies";
    var i=0, ih='', options=[], bn;
    for (i; i < buddyList.length; i+=1) {
      ih += buddy2str( buddyList[i] );
      bn = buddyList[i].name;
      options.push([bn, bn]);
    }
    $("buddyListD").innerHTML = ih;
    setBuddyHandlers($("buddyListD"), this.selectDialog);
    tgc.utils.clearSelect('fwdToSel');
    options.unshift(['-none-','-none-']);
    //console.log(tgc.utils.dumpArray(options));
    tgc.utils.fillSelect('fwdToSel',options,0);
  };
  
  this.selectDialog = function() { alert("redefine this"); };
  
  function setBuddyHandlers(listElement, selectDialogCmd) {
    listElement.onclick = function(event) {
      //console.log("c");
      var target = getClickedItem(event);
      //console.log("clicked:"+target);
      var targetDn = getChildDataByClass(target, "buddyName");
      if (targetDn) {
        console.log("clicked name:"+targetDn);
        selectDialogCmd(targetDn, dn);
      }
      return false;
    };// end onclick
  }
  
  function getClickedItem(event) {
    event = event || window.event;
    var target = event.target || event.srcElement;
    while(target.nodeName != 'DIV') {
      if (target.nodeName == 'SPAN' && target.id) {
        return target;
      }
      target = target.parentNode;
    }
    return false;
  }
  
  function getChildDataByClass(el, cn) {
    var i=0, ci={};
    for (; i < el.children.length; i+=1) {
      ci = el.children[i];
      if ( ci.classList.contains(cn) ) { return ci.innerText; }
    }
    return false;
  }
  
  function clickedHref(event) {
    event = event || window.event;
    var target = event.target || event.srcElement;
    while(target.nodeName != 'DIV') {
      if (target.nodeName == 'A' && target.id) {
        return target;
      }
      target = target.parentNode;
    }
    return false; // missed
  }
  
  function buddy2str(b) {
    var postfix = '';
    if (b.hasUndelivered) postfix = '<span class="undelivered">&nbsp;&nbsp;</span>'; 
    var s = `<span class="buddy" id="${buddyIdPrefix+b.i}">\
      <span class="buddyName">${b.name}</span> / ${b.username} / ${b.phone}\
       &nbsp; <span class="buddyTotal">${b.count}</span> / <span class="buddyUnread">${b.unreadCount}</span> ${postfix}\
       <br />\n</span>`;
    return s;
  }
  
  this.showDialog = function(dialog) {
    //$("dialogD").innerHTML = dialog.name;
    $("dialogD").innerHTML = buddy2str(dialog);
  };
  
  this.showData = function(str) {
    //$("dialogD").innerHTML = dialog.name;
    $("dataD").innerHTML = str;
  };
  
  this.showMessages = function(msgList) {
    //$("msgListD").innerHTML = "List of "+msgList.length+" messages";
    var i=0, ih='', el = $("msgListD");
    for (i; i < msgList.length; i+=1) {
      ih += msg2str( msgList[i] );
    }
    el.innerHTML = ih;
    setupDragging(el);
  };
      
  function setupDragging(el) {
    var i=0, c={}; 
    for (var i=0; i < el.children.length; i += 1) {
      c = el.children[i];
      if (c.nodeName == 'SPAN' && c.id) { makeDraggable(c); } 
    }
  }
  
  function makeDraggable(el) {
    el.draggable = true;
    el.addEventListener("dragstart", function onDragstart(event) {
      event.dataTransfer.setData("text/plain", event.target.id);
    } );
  }
  
  function msg2base(m) {
    var prefix, re='', media='', mediaLink = '', cn = '', postfix = '';
    ['action', 'media', 'text', 'date', 'prefix', 'fwdFrom'].forEach(function(s) {
      if (! m[s]) m[s] = '';
      else {
        m[s] = tgc.utils.escapeHtml(m[s]);
        //m[s]=m[s].replace('&','&amp;');
        //m[s]=m[s].replace('<','&lt;');
        //m[s]=m[s].replace('>','&gt;');
      }
    });
    prefix = m.prefix || '_';
    if (m.unread) { prefix = `<span class="unread">${prefix}</span>`; }
    if (m.fwdFrom) { prefix += m.fwdFrom + prefix; }
    if (m.replyToId) { re = `Re:${m.replyToId} `; }
    if (m.media) {
      cn = 'raw';
      if (m.mediaLink) {
        mediaLink = m.mediaLink;
        cn = 'ripe';
      }
      media = `<a href="${mediaLink}" target="_blank" draggable="false" class="${cn}" id="${mediaHrefPrefix+m.id}">${m.media}</a>`;
    }
    if (m.undelivered) postfix = '<span class="undelivered">&nbsp;&nbsp;</span>'; 
    return `${prefix} ${re}${media}${m.action}${m.text} [${m.date}] ${postfix}<br />\n`;
  }
  
  function msg2str(m) {
    var s = `<span class="messageDraggable" id="${messageIdPrefix+m.id}" title="${m.id}">\
    ${msg2base(m)}\
    </span>`;
    return s;
  }
  
  function msg2span(m) {
    var span = document.createElement('SPAN');
    span.className = "messageDraggable";
    span.id = messageIdPrefix+m.id;
    span.title = m.id;
    span.innerHTML = msg2base(m);
    return span;
  }
  
  this.showUnknownMsg = function(msg) { this.showAlertB("Message from "+msg.from+" (unknown) :"+msg.text); };
  
  this.showNewMsg = function(msg) {
    if (msg.from == dn) { 
      //this.showAlertD(msg.from+":"+msg.text); 
      addMsgToCurrentDialog(msg);
      incCounts("buddyListD", msg.from, false );
      incCounts("dialogD", msg.from, false );
    }
    else {
      //this.showAlertB(msg.from+":"+msg.text)
      incCounts("buddyListD", msg.from, msg.unread);
    } 
  };
  
  function addMsgToCurrentDialog(msg) {
    var ns ='', el = $("msgListD");
    ns = msg2span(msg);
    el.appendChild(ns);
    makeDraggable(ns);
  }
  
  
  function incCounts(containerId, targetDn, isUnread = true, inc = +1) {
    var elTotal = false, elBuddy = false, elUnread = false, c, t, u;
    elBuddy = findDialogInContainer($(containerId), targetDn);
    if (! elBuddy) throw new Error("Wrong TARGETDN:"+targetDn+"!");
    elTotal = elBuddy.getElementsByClassName('buddyTotal')[0];
    if (! elTotal) throw new Error(targetDn+": missing buddyTotal");
    t = parseInt(elTotal.innerText);
    elTotal.innerText = t + inc;
    if (! isUnread) return;
    elUnread = elBuddy.getElementsByClassName('buddyUnread')[0];
    if (! elUnread) throw new Error(targetDn+": missing buddyUnread");
    u = parseInt(elUnread.innerText);
    elUnread.innerText = u + inc;
  }
  
  this.setCounts=function(containerId, targetDn, total, unread) {
    var elTotal = false, elBuddy = false, elUnread = false;
    if (! containerId) containerId = "buddyListD";
    elBuddy = findDialogInContainer($(containerId), targetDn);
    if (! elBuddy) throw new Error("Wrong TARGETDN:"+targetDn+"!");
    elTotal = elBuddy.getElementsByClassName('buddyTotal')[0];
    if (! elTotal) throw new Error(targetDn+": missing buddyTotal");
    elTotal.innerText = total;
    elUnread = elBuddy.getElementsByClassName('buddyUnread')[0];
    if (! elUnread) throw new Error(targetDn+": missing buddyUnread");
    elUnread.innerText = unread;
  };
  
  function findDialogInContainer(container, targetDn) {
    var i=0, c, n;
    for (; i < container.children.length; i+=1) {
      c = container.children[i];
      n = getChildDataByClass(c, "buddyName");
      if (n == targetDn) return c;
    }
    return false;
  }
  
  this.clearMsg = function() {
    $("textInp").value = $("fileInp").value = $("replyToInp").value = '';
  };
  
  this.takeMediaLink = function(arr) {
    var aId, el, href;
    if (! arr.length == 3) throw new Error("Wrong data");
    if (arr[0] != dn) return false;
    aId = mediaHrefPrefix + arr[1];
    el = false;
    try { el = $(aId); }
    catch(e) {}
    if (! el) return;
    href = arr[2] || '';
    el.href = href;
    el.className = href ? 'ripe' : 'raw';
  };
  
  this.takeMessageRead = function(cmdo) {
    var dialog, count = 0, mel=false;
    if ( ! cmdo.id) {
      console.log("Missing id");
      return;
    }
    try { mel = $("msg_"+cmdo.id); }
    catch(e) {}
    if ( ! mel) {
      console.log("Unknown id:"+cmdo.id);
      return;
    }
    if ( dn && cmdo.from == dn) { 
      count = clearUndeliveredMarks($('msgListD'));
      console.log('cleared '+count+' undelivered');
      clearUndeliveredMarks($("dialogD"));
    }
    // fall through
    dialog = findDialogInContainer($("buddyListD"), cmdo.from);
    if ( ! dialog) {
      console.log('MessageRead miss (no dialog):'+cmdo.from);
      return;
    }
    count = clearUndeliveredMarks(dialog);
  };
  
  function clearUndeliveredMarks(container) {
    var spansUndelivered, count, s, i=0;
    spansUndelivered = container.querySelectorAll('span.undelivered');
    count = spansUndelivered.length;
    for (; i < count; i += 1) {
      s = spansUndelivered[i];
      s.parentElement.removeChild(s);
    }
    return count;
  }
  
  function addUndeliveredMark(container) {
    clearUndeliveredMarks(container);
    var span = document.createElement('SPAN');
    span.className = 'undelivered';
    span.innerHTML = '&nbsp;&nbsp;';
    container.insertBefore(span, container.lastElementChild);
  }
  
  this.setDialogUndelivered = function(aDn, isUndlv) {
    if (dn && aDn == dn) {
      isUndlv ? addUndeliveredMark($("dialogD").firstElementChild) : clearUndeliveredMarks($("dialogD"));
    }
    var dialog = findDialogInContainer($("buddyListD"), aDn);
    if ( ! dialog) { throw new Error("Not in dialog list:"+aDn); }
    isUndlv ? addUndeliveredMark(dialog) : clearUndeliveredMarks(dialog);
  };
  
  function assembleCommand() {
    var i,v
    var res = [];
    var act = $("actInp").value;
    if ( ! act) {
      this.showAlertB("Empty ACTION")
      return false;
    }
    res.push(act);
    for (i=0; i <= argMax; i += 1) {
      v = $("arg"+i+"Inp").value;
      //console.log(i+":"+v);
      res.push(v);
    }
    return res;  
  }
  
  this.setHandlers = function(arbitraryCommand, sendMessage, sendFile, selectDialog, forwardMessage, deleteMessage, reloadDialog, closeDialog, downloadMedia, reloadBuddies) {
    $("sendCmdBtn").onclick = function() {
      var cmdArr = assembleCommand();
      var aDn = dn || '';
      if (cmdArr) arbitraryCommand(cmdArr, aDn);
      return false;
    };
    $("clearCmdBtn").onclick = function() {
      $("actInp").value = ""
      for (var i=0; i <= argMax; i += 1) { $("arg"+i+"Inp").value = ""; }
      return false;
    };
    $("sendMsgBtn").onclick = function() {
      if ( ! dn) {
        _this.showAlertD("No dialog selected");
        return false;
      }
      var t = $("textInp").value;
      var f = $("fileInp").files[0];
      if ( ! t && ! f) {
        _this.showAlertD("Provide message or file");
        return false;
      }
      var re = $("replyToInp").value || '';
      if ( ! f) sendMessage(dn, t, re);
      else sendFile(dn, t, f, re);
      $("replyToInp").value = '';
      return false;
    };
    $("clearMsgBtn").onclick = function() {
      _this.clearMsg();
    };
    this.selectDialog = selectDialog;
    this.deleteMessage = deleteMessage;
    setupDrop($("deleteMsg1Btn"), '', this.deleteMessage);
    setupDrop($("deleteMsg2Btn"), 'true', this.deleteMessage);
    setupDrop($("fwdIdInp"), '', function(dn, eid) { _this.setFwdId(dn, eid); _this.handleForward(); } );
    $('fwdToSel').onchange = function() { _this.handleForward(); }; //this.handleForward; fails
    this.handleForward = function() {
    // send the command as soon as both id and name are set
      var fwdId = + ($("fwdIdInp").value);
      //alert(fwdId);
      if (! fwdId || fwdId != fwdId) return false; // empty or NaN
      var fwdToName = tgc.utils.getSelect('fwdToSel');
      //alert(fwdToName);
      if ( ! fwdToName || fwdToName == '-none-') return false; // no target name set
      console.log("About to forward #"+fwdId+" to "+fwdToName);
      forwardMessage(dn, fwdId, fwdToName);
      incCounts("buddyListD", fwdToName, true );
      if (fwdToName != dn) { this.setDialogUndelivered(fwdToName, true); }
      else { incCounts("dialogD", fwdToName, true ); }
      return false;
    };
    setupDrop($("replyToInp"), '', this.setReplyTo);
    $("reloadDialogBtn").onclick = function() {
      reloadDialog(dn);
      return false;
    };
    $("closeDialogBtn").onclick = function() {
      closeDialog(dn);
      _this.hideDialogPanel();
      return false;
    };
    $("msgListD").onclick = function(event) {
      var clicked = clickedHref(event);
      //alert(clicked);
      //alert(typeof clicked);
      //return false;
      if (typeof clicked == 'object') {
        console.log("Clicked id:"+clicked.id+'/'+stripPrefix(clicked.id)+'/'+clicked.href);
        if (clicked.href)  {
          if (window.location.href == clicked.href) { downloadMedia(dn, stripPrefix(clicked.id)) } 
          else { return true; }
        }
        return false;
      }
      return false;
    };
    $("toggleHideableBtn").onclick = toggleHideable;
    $("reloadBuddiesBtn").onclick = function() { reloadBuddies(dn); };
    //window.onunload = function() { if (dn) sendSave(dn); }; does not work
    $("deleteMsg1Btn").onclick = $("deleteMsg2Btn").onclick = dragHere;
  };
  
  function stripPrefix(aId) { return aId.split('_')[1]; }
  
  this.deleteMessage = function() { alert("redefine this"); };
  
  function setupDrop(el, arg, cmd) {
    el.addEventListener('dragover', function(event) {
      event.preventDefault();
    });
    el.addEventListener('drop', function(event) {
      event.preventDefault();
      var eid = event.dataTransfer.getData("text/plain");
      if ( ! dn) {
        _this.showAlertB("No current dialog");
        return false;
      }
      if ( ! eid.startsWith(messageIdPrefix) ) { return false; }
      eid = eid.split('_')[1];
      cmd(dn, eid, arg);
      return false;
    });
  }
  
  this.setReplyTo = function(dn, eid) {
    $("replyToInp").value = eid;
  };
  
  this.setFwdId = function(dn, eid) {
    $("fwdIdInp").value = eid;
  };
  
  this.clearMsgIds = function() {
    $("replyToInp").value = '';
    $("fwdIdInp").value = '';
  };
  
  function toggleHideable() {
    tgc.utils.toggleHideable(hideable,getShowMore,setShowMore);
  }
  toggleHideable();
  
  function dragHere() { alert("To delete a message, drag it to this button"); }
  
  this.hideDialogPanel();
};
