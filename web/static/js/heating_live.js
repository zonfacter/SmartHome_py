'use strict';
window.HeatingLive=(()=>{
  // Keep live nodes, focus, text selection, disclosures and scroll positions.
  const key=node=>node.nodeType===1?(node.id||node.getAttribute('data-live-key')||node.getAttribute('data-pump-detail')||node.getAttribute('data-diagnostic')||''):'';
  const compatible=(a,b)=>a&&a.nodeType===b.nodeType&&(a.nodeType!==1||(a.localName===b.localName&&a.namespaceURI===b.namespaceURI&&key(a)===key(b)));
  function children(parent,source){
    let cursor=parent.firstChild;
    for(const wanted of source.childNodes){
      let node=compatible(cursor,wanted)?cursor:null;
      if(!node&&key(wanted))node=Array.from(parent.childNodes).find(n=>compatible(n,wanted))||null;
      if(!node){node=wanted.cloneNode(true);parent.insertBefore(node,cursor);}
      else{
        if(node!==cursor)parent.insertBefore(node,cursor);
        if(node.nodeType===1){
          for(const attr of Array.from(node.attributes))if(!wanted.hasAttribute(attr.name)&&!(node.localName==='details'&&attr.name==='open'))node.removeAttribute(attr.name);
          for(const attr of wanted.attributes)if(!(node.localName==='details'&&attr.name==='open')&&node.getAttribute(attr.name)!==attr.value)node.setAttribute(attr.name,attr.value);
          children(node,wanted);
        }else if(node.nodeValue!==wanted.nodeValue)node.nodeValue=wanted.nodeValue;
      }
      cursor=node.nextSibling;
    }
    while(cursor){const next=cursor.nextSibling;parent.removeChild(cursor);cursor=next;}
  }
  function update(target,html){
    const template=target.ownerDocument.createElement('template');template.innerHTML=html;
    children(target,template.content);
    // WeakMap avoids keeping a second HTML copy in the rendered DOM.
    rendered.set(target,html);
  }
  const rendered=new WeakMap();
  return {update(target,html){if(rendered.get(target)!==html)update(target,html);}};
})();
