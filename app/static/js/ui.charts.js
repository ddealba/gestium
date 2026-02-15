(function(){
  if(!window.ApexCharts) return;
  const css=(v)=>window.ff && window.ff.cssVar ? window.ff.cssVar(v) : '';
  const primary=css('--ff-primary')||'#5b52b6';
  const grid='rgba(25,33,61,.10)';

  const el=document.querySelector('[data-ff-chart="sales"]');
  if(!el) return;

  new ApexCharts(el,{
    chart:{type:'line',height:280,toolbar:{show:false},fontFamily:'Poppins, system-ui'},
    stroke:{width:[0,3],curve:'smooth'},
    plotOptions:{bar:{columnWidth:'24%',borderRadius:6}},
    fill:{type:['solid','gradient'],gradient:{opacityFrom:.18,opacityTo:0,stops:[0,100]}},
    colors:[primary,'#8b8f9b'],
    series:[
      {name:'Sales',type:'column',data:[12,42,18,40,22,48,28,14,36,44,52,32]},
      {name:'Revenue',type:'area',data:[8,14,12,16,15,22,18,16,19,21,27,24]}
    ],
    xaxis:{categories:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],axisBorder:{show:false},axisTicks:{show:false}},
    grid:{borderColor:grid,strokeDashArray:6,padding:{left:8,right:8}},
    dataLabels:{enabled:false},
    legend:{position:'bottom',markers:{radius:12}}
  }).render();
})();