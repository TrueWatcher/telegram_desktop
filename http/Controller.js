"use strict";

tgc.Controller=function() {
  var _this=this,
      connector = {},
      view = {},
      buddyList = [],
      wsKey = '';
  
  this.setup = function() {
    view = new tgc.View();
    view.setHandlers(arbitraryCommand, sendMessage, sendFile, selectDialog, forwardMessage, deleteMessage, reloadDialog, closeDialog, downloadMedia, reloadBuddies);
    view.showAlertB("Connecting...");
    connector = new tgc.Connector(tgc.serverParams, tgc.userParams);
    connector.pull.registerPullCallback(_this.takeResponse);
    connector.push.registerPushCallback(_this.takeResponse);
    view.showAlertB("Requesting data...");
    connector.push.sendGetBuddies();
  };
  
  function arbitraryCommand(cmdArr, dn) { connector.push.sendCommandWGet(cmdArr, dn); }
  function sendMessage(dn, text, replyTo) { connector.push.sendMessage(dn, text, replyTo); }
  function sendFile(dn, text, file, replyTo) { connector.push.sendFile(dn, text, file, replyTo); }
  function selectDialog(targetDn, dn) { connector.push.sendSelectDialog(targetDn, dn); }
  function forwardMessage(dn, msgId, toName) { connector.push.sendForwardMessage(dn, msgId, toName); }
  function deleteMessage(dn, id, forAll) { 
    //alert(`dn:${dn}, id:${id}, forAll:${forAll}`);
    connector.push.sendDeleteMessage(dn, id, forAll);
  }
  function reloadDialog(dn) { connector.push.sendReloadDialog(dn); }
  function closeDialog(dn) { 
    view.clearDn();
    connector.push.sendListDialogs(dn);
  }
  function downloadMedia(dn, id) { connector.push.sendDownloadMedia(dn, id); }
  function reloadBuddies(dn) { 
    connector.push.sendReloadAll();
    if (dn) connector.push.sendGetDialog(dn);
  }
  function sendSave(dn) { connector.push.sendSave(dn); }
  
  this.takeResponse=function(resp) {
    var mode = '';
    if (resp.mode) {
      mode = resp.mode;
    }
    if (resp.alert) {
      if (mode == "dialog") view.showAlertD(resp.alert);
      else view.showAlertB(resp.alert);
    }
    if (resp.buddies) {
      if ( ! resp.buddies[0]) {
        view.showAlertB("Got invalid buddy list");
      }
      else {
        setBuddies(resp.buddies)
        view.showBuddies(resp.buddies);
      }
    }
    if (resp.dialog) {
      var rd = resp.dialog;
      var current = view.getDn();
      if ( current && (rd.name != current) ) {
        //view.showAlertD("Changing dialog:"+ current+" > "+rd.name );
        view.clearMsgIds();
      }
      if ( buddyList.indexOf(rd.name) < 0 ) {
        view.showAlertB("Got unknown dialog:"+rd.name);
        throw new Error("Got unknown dialog:"+rd.name);
      }
      view.showDialogPanel()
      view.showDialog(rd);
      view.setDn(rd.name);
      view.setCounts("", rd.name, rd.count, rd.unreadCount);
      if (rd.hasOwnProperty('hasUndelivered')) view.setDialogUndelivered( rd.name, rd.hasUndelivered );
    }
    if (resp.replacedDialog) {
      var rd = resp.replacedDialog;
      console.log("replacedDialog: "+tgc.utils.dumpArray(rd));
      view.setCounts("", rd.name, rd.count, rd.unreadCount);
      if (rd.hasOwnProperty('hasUndelivered')) view.setDialogUndelivered( rd.name, rd.hasUndelivered );
    }
    if (resp.messages) {
      if ( ! resp.dialog || (resp.dialog.name != view.getDn()) ) {
        view.showAlertD("Got messages witnout dialog, current:"+view.getDn());
      }
      else if ( ! resp.messages instanceof Array) {
        view.showAlertD("Got non-array messages:"+typeof(resp.messages));
      }
      else {
        view.showMessages(resp.messages);
      }
    }
    if (resp.newMessage) {
      console.log(tgc.utils.dumpArray(resp.newMessage));
      takeNewMessage(resp.newMessage);
    }
    if (resp.messageRead) {
      console.log(tgc.utils.dumpArray(resp.messageRead));
      var by = resp.messageRead.from;
      if ( buddyList.indexOf(by) < 0 ) {
        view.showAlertD("Got messageRead from unknown "+by);
      }
      view.takeMessageRead(resp.messageRead);
    }
    if (resp.data) {
      view.showData(resp.data);
    }
    if (resp.mediaLink) {
      console.log(tgc.utils.dumpArray(resp.mediaLink));
      view.takeMediaLink(resp.mediaLink)
    }
    if (resp.wsKey) {
      wsKey = resp.wsKey;
      console.log("ws client id="+wsKey);
    }
  }
  
  function setBuddies(budArr) {
    buddyList = []
    budArr.forEach(function(b) { buddyList.push(b.name); });
    console.log("buddies reloaded:"+buddyList.length);
  }
  
  function takeNewMessage(msg) {
    var by = msg.from;
    if ( buddyList.indexOf(by) < 0 ) { view.showUnknownMsg(msg) }
    else { view.showNewMsg(msg) }
    if (by == view.getDn()) { connector.push.sendAck(by, msg.id); }
  }
  
};
