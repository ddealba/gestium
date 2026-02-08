(function(){
  const c = document.getElementById("chart");
  if(!c || !window.GestiumCharts) return;

  const sets = {
    "6":  { labels:["Sep","Oct","Nov","Dic","Ene","Feb"], a:[8.4,9.1,10.2,11.0,10.6,12.48], b:[6.9,7.4,8.8,9.7,9.2,9.36] },
    "12": { labels:["Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic","Ene","Feb"], a:[6.8,7.1,7.5,8.2,8.0,8.6,8.4,9.1,10.2,11.0,10.6,12.48], b:[5.8,6.2,6.6,7.1,7.0,7.4,6.9,7.4,8.8,9.7,9.2,9.36] },
    "24": { labels:[...Array(24)].map((_,i)=>`M${i+1}`), a:Array(24).fill(0).map((_,i)=>6.2+Math.sin(i/2.3)*0.6+i*0.08), b:Array(24).fill(0).map((_,i)=>5.4+Math.sin(i/2.6)*0.55+i*0.07) }
  };

  function render(key){
    const s = sets[key];
    window.GestiumCharts.drawLineAreaChart(c, s.a, s.b, s.labels, { a:"#4f46e5", b:"#10b981" });
  }

  render("6");

  document.querySelectorAll('.tab[data-tab-group="range"]').forEach(btn=>{
    btn.addEventListener("click", ()=>{
      document.querySelectorAll('.tab[data-tab-group="range"]').forEach(b=>b.classList.remove("is-active"));
      btn.classList.add("is-active");
      render(btn.getAttribute("data-tab"));
    });
  });
})();
