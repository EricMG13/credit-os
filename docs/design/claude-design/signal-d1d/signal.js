/* Signal mocks: shell, settings navigation and placeholder icons, so each screen's markup holds only its own content. */
(function(){
  var m=/f=(\d+)/.exec(location.hash);
  if(m){var s=document.createElement('style');s.textContent='.page>header{display:none}.page>section{display:none}.page>section:nth-of-type('+m[1]+'){display:block}.page{padding:8px 0!important}';document.head.appendChild(s);}
  var P={
    search:'<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    star:'<path d="M12 3l2.7 5.6 6.1.8-4.5 4.2 1.1 6.1L12 16.8 6.6 19.7l1.1-6.1L3.2 9.4l6.1-.8z"/>',
    bookmark:'<path d="M6 4h12v16l-6-4-6 4z"/>',
    msg:'<path d="M4 5h16v11H9l-5 4z"/>',
    share:'<path d="M12 15V4M8 8l4-4 4 4M5 13v6h14v-6"/>',
    ext:'<path d="M8 16l8-8M9 8h7v7"/>',
    down:'<path d="M6 9l6 6 6-6"/>',
    x:'<path d="M6 6l12 12M18 6L6 18"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
    users:'<circle cx="9" cy="9" r="3.5"/><path d="M3 19c1-3.5 3.3-5 6-5s5 1.5 6 5"/><circle cx="17" cy="8" r="2.5"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4.5 4.5-6 8-6s6.5 1.5 8 6"/>',
    sliders:'<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    lib:'<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    model:'<path d="M5 20V10M12 20V4M19 20v-7"/>',
    run:'<path d="M7 4l12 8-12 8z"/>',
    signal:'<circle cx="12" cy="12" r="2"/><circle cx="12" cy="12" r="8"/>',
    lines:'<path d="M4 6h16M4 12h16M4 18h10"/>',
    clock:'<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
    hash:'<path d="M9 4L7 20M17 4l-2 16M4 9h16M3 15h16"/>',
    doc:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    link:'<path d="M9 15l6-6M10 6l1-1a4 4 0 016 6l-1 1M14 18l-1 1a4 4 0 01-6-6l1-1"/>'
  };
  function ic(n,a){return '<sg-i n="'+n+'"'+(a||'')+'></sg-i>';}
  class SgI extends HTMLElement{connectedCallback(){if(this._d)return;this._d=1;var f=this.hasAttribute('f');this.innerHTML='<svg viewBox="0 0 24 24" fill="'+(f?'currentColor':'none')+'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(P[this.getAttribute('n')]||'')+'</svg>';}}
  function item(id,icon,label,extra,on){return '<li class="ni'+(on===id?' on':'')+'">'+ic(icon)+'<span class="l">'+label+'</span>'+(extra||'')+'</li>';}
  class SgShell extends HTMLElement{connectedCallback(){
    if(this._d)return;this._d=1;
    var g=function(k){return this.getAttribute(k);}.bind(this);
    var on=g('view')||'',role=g('role')||'Writer',name=g('name'),nf=g('follow')==='none';
    var c=function(n){return '<span class="cnt">'+n+'</span>';};
    var st=function(f){return '<sg-i n="star" s="16" class="fs" title="'+(f?'Following':'Follow')+'"'+(f&&!nf?' f':'')+'></sg-i>';};
    var rail=document.createElement('aside');rail.className='rail';
    rail.innerHTML='<div class="railc"><div class="logo" title="Logo symbol (placeholder)"><i></i></div><div class="rl">'+
      [['lib','Library'],['model','Model'],['run','Run'],['signal','Signal']].map(function(a){return '<span class="rb'+(a[0]==='signal'?' on':'')+'" title="'+a[1]+'">'+ic(a[0])+'</span>';}).join('')+'</div></div>';
    var sub=document.createElement('nav');sub.className='sub';
    var dg=g('digests'),pz='<span class="bd sm neu"><i class="s pb"></i>Paused</span>';
    sub.innerHTML='<h3>Signal</h3><ul>'+
      item('foryou','lines','For you','',on)+item('latest','clock','Latest','',on)+item('saved','bookmark','Saved',g('saved')==='0'?'':c(6),on)+'</ul>'+
      '<h6>Topics</h6><ul>'+
      item('shipping','hash','Shipping',c(12)+st(1),on)+item('packaging','hash','Packaging',c(8)+st(1),on)+item('telecoms','hash','Telecoms',c(5)+st(0),on)+item('ratings','hash','Rating actions',c(9)+st(1),on)+'</ul>'+
      '<h6>Groups</h6><ul>'+item('lev','users','Leveraged credit',c(3),on)+item('desk','users','Shipping desk','',on)+'</ul>'+
      '<h6>Digests</h6><ul>'+
      item('weekly','doc','Weekly brief',dg==='paused'?pz:(dg==='read'?'':'<i class="dot" title="Unread"></i>'),on)+item('daily','doc','Daily ratings',dg==='paused'?pz:'',on)+'</ul>'+
      '<ul style="margin-top:8px">'+item('settings','sliders','Settings','',on)+'</ul>'+
      '<div class="me"><div class="alg">'+(name?'<span class="av me1">'+name.split(' ').map(function(w){return w[0];}).join('')+'</span><div><b>'+name+'</b><small>'+role+'</small></div>':'<span class="av" style="display:inline-grid;place-items:center">'+ic('user',' s="16"')+'</span><div><b><a href="#">Set your name</a></b><small>'+role+'</small></div>')+'</div></div>';
    this.prepend(rail,sub);
  }}
  class SgSet extends HTMLElement{connectedCallback(){
    if(this._d)return;this._d=1;var on=this.getAttribute('sec');
    var h=document.createElement('h2');h.textContent='Settings';
    var v=document.createElement('div');v.className='vt';
    v.innerHTML=['Groups','Thread rules','Sources','Topics','Digests','Notifications','AI and cost'].map(function(n){return '<span'+(n===on?' class="on"':'')+'>'+n+'</span>';}).join('');
    this.prepend(h,v);
  }}
  [['sg-i',SgI],['sg-shell',SgShell],['sg-set',SgSet]].forEach(function(d){if(!customElements.get(d[0]))customElements.define(d[0],d[1]);});
})();
