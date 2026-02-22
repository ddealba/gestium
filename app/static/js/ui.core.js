(function(){
  const qs=(s,el=document)=>el.querySelector(s);
  const qsa=(s,el=document)=>[...el.querySelectorAll(s)];

  // Theme
  const key='ff_theme';
  const setTheme=(t)=>{document.documentElement.setAttribute('data-theme',t);try{localStorage.setItem(key,t)}catch{}};
  const saved=(()=>{try{return localStorage.getItem(key)}catch{return null}})();
  if(saved) setTheme(saved);

  qsa('[data-ff="theme-toggle"]').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const cur=document.documentElement.getAttribute('data-theme')||'light';
      setTheme(cur==='dark'?'light':'dark');
    });
  });

  // Active nav by data-page
  const page=document.body.getAttribute('data-page');
  if(page) qsa(`[data-nav="${page}"]`).forEach(a=>a.classList.add('is-active'));

  // Sidebar permission-aware nav visibility
  const applyPermissionsToSidebar=(permissions)=>{
    const set=new Set(permissions||[]);
    qsa('[data-required-permissions]').forEach(el=>{
      const raw=el.getAttribute('data-required-permissions')||'';
      const required=raw.split(',').map(v=>v.trim()).filter(Boolean);
      if(!required.length) return;
      const allowed=required.some(code=>set.has(code));
      if(!allowed) el.remove();
    });
    qsa('.ff-nav__group').forEach(group=>{
      if(!qs('.ff-nav__subitem',group)) group.remove();
    });
  };

  if(window.apiFetch){
    window.apiFetch('/rbac/me/permissions')
      .then(data=>applyPermissionsToSidebar(data?.permissions||[]))
      .catch(()=>{});
  }

  // Modal
  qsa('[data-ff="modal-open"]').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const id=btn.getAttribute('data-target');
      const modal=id?qs(id):null;
      if(modal){modal.classList.add('is-open');document.body.style.overflow='hidden';}
    });
  });
  qsa('[data-ff="modal-close"]').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const modal=btn.closest('.ff-modal');
      if(modal){modal.classList.remove('is-open');document.body.style.overflow='';}
    });
  });

  // Drawer
  const openDrawer=(id)=>{const d=id?qs(id):null;if(d){d.classList.add('is-open');document.body.style.overflow='hidden';}};
  const closeDrawer=(d)=>{if(d){d.classList.remove('is-open');document.body.style.overflow='';}};
  qsa('[data-ff="drawer-open"]').forEach(btn=>btn.addEventListener('click',()=>openDrawer(btn.getAttribute('data-target'))));
  qsa('[data-ff="drawer-close"]').forEach(btn=>btn.addEventListener('click',()=>closeDrawer(btn.closest('.ff-drawer'))));
  qsa('.ff-drawer__backdrop').forEach(b=>b.addEventListener('click',()=>closeDrawer(b.closest('.ff-drawer'))));

  // View toggle
  qsa('[data-ff="view-toggle"]').forEach(root=>{
    const targetSel=root.getAttribute('data-target');
    const target=targetSel?qs(targetSel):null;
    if(!target) return;
    const setView=(v)=>{
      target.setAttribute('data-view',v);
      qsa('[data-view-btn]',root).forEach(b=>{
        const on=b.getAttribute('data-view-btn')===v;
        b.classList.toggle('ff-btn--primary',on);
        b.classList.toggle('ff-btn--ghost',!on);
      });
    };
    setView(target.getAttribute('data-view')||'grid');
    qsa('[data-view-btn]',root).forEach(b=>b.addEventListener('click',()=>setView(b.getAttribute('data-view-btn'))));
  });

  // Kanban drag & drop
  qsa('[data-ff-kanban]').forEach(board=>{
    let dragged=null;
    qsa('[draggable="true"]',board).forEach(card=>{
      card.addEventListener('dragstart',(e)=>{dragged=card;e.dataTransfer.effectAllowed='move';card.style.opacity='0.85';});
      card.addEventListener('dragend',()=>{card.style.opacity='';dragged=null;});
    });
    qsa('[data-dropzone]',board).forEach(zone=>{
      zone.classList.add('ff-dropzone');
      zone.addEventListener('dragover',(e)=>{e.preventDefault();zone.classList.add('is-over');});
      zone.addEventListener('dragleave',()=>zone.classList.remove('is-over'));
      zone.addEventListener('drop',(e)=>{e.preventDefault();zone.classList.remove('is-over');if(dragged) zone.appendChild(dragged);});
    });
  });

  // ESC
  document.addEventListener('keydown',(e)=>{
    if(e.key==='Escape'){
      qsa('.ff-modal.is-open').forEach(m=>m.classList.remove('is-open'));
      qsa('.ff-drawer.is-open').forEach(d=>d.classList.remove('is-open'));
      document.body.style.overflow='';
    }
  });

  window.ff=window.ff||{};
  window.ff.cssVar=(v)=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
})();
