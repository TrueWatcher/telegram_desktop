"use strict";

tgc.utils = {};

tgc.utils.dumpArray=function(x) {
  var res="",i,expanded;
  if (typeof x == "object") {
    res+="{ ";
    for (i in x) {
      if (x.hasOwnProperty(i)) {
        res+=" "+i+":"+tgc.utils.dumpArray(x[i]);
      }  
    }
    res+=" }";
  }
  else res+=""+x;
  return res;  
};

tgc.utils.Indicator=function(id,states,htmlOrValue,startState) {
  var el=document.getElementById(id);
  if ( ! el) throw new Error("Wrong Id");
  if ( ! htmlOrValue) htmlOrValue="h";
  if ( ! states instanceof Array || states.length < 2) throw new Error("Wrong STATES");
  var cl=states.length;
  var sc=allOrNone()
  if ( ! startState) startState=0;
  if (startState >= cl) throw new Error("Too big STARTSTATE");
  var state;
  adoptState(startState);
  
  this.getElement=function() { return el; };
  
  this.on=function() { adoptState(1); };
  this.off=function() { adoptState(0); };
  this.z=function() { adoptState(2); };
  this.toggle=function() {
    if (state == 0) adoptState(1);
    else if (state == 1) adoptState(0);
    else console.log("Cannot toggle z-state");
  }
    
  function adoptState(index) {
    if (sc.strings) {
      if (htmlOrValue == "h") el.innerHTML=states[index][0];
      else el.value=states[index][0];
    }
    if (sc.classes) {
      removeOtherClasses(index);
      el.classList.add(states[index][1]);      
    }
    state=index;
  }
  
  function allOrNone() {
    var withStringCount=0,
        withoutStringCount=0,
        withClassCount=0,
        withoutClassCount=0;
    for (var i=0; i < cl; i+=1) {
      if ( !! states[i][0]) withStringCount+=1;
      else withoutStringCount+=1;
      if ( !! states[i][1]) withClassCount+=1;
      else withoutClassCount+=1;
    }
    if (withStringCount != cl && withoutStringCount != cl) throw new Error("Element: "+id+" Strings must be given for all states or for no state");
    if (withClassCount != cl && withoutClassCount != cl) throw new Error("Element: "+id+" Classes must be given for all states or for no state");
    return { strings : withStringCount == cl, classes : withClassCount == cl};
  }
  
  function removeOtherClasses(stateIndex) {
    var c;
    for (var i=0; i < cl; i+=1) {
      if (i == stateIndex) continue;
      el.classList.remove(states[i][1]);
    }   
  }
  
  this.removeAllStateClasses=function() {
    var c;
    for (var i=0; i < cl; i+=1) {
      el.classList.remove(states[i][1]);
    }
  };
}// end Indicator

tgc.utils.setStyle=function(collection, attr, value) {
  for (var i=collection.length-1; i >= 0; i-=1) { collection[i].style[attr]=value; }    
};

tgc.utils.toggleHideable=function(hideable,getShowMore,setShowMore) {
  var showMore=getShowMore();
  if (showMore) { tgc.utils.setStyle(hideable,"display",""); }
  else { tgc.utils.setStyle(hideable,"display","none"); }
  showMore= ! showMore;
  setShowMore(showMore);  
};

tgc.utils.escapeHtml=function(text) {
  return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
};
