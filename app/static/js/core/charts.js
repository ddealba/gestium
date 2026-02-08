(function(){
  function drawLineAreaChart(canvas, seriesA, seriesB, labels, colors){
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;

    const pad = { l: 64, r: 24, t: 18, b: 54 };
    const x0 = pad.l, x1 = W - pad.r;
    const y0 = pad.t, y1 = H - pad.b;

    const all = seriesA.concat(seriesB || []);
    const min = Math.min(...all) * 0.92;
    const max = Math.max(...all) * 1.08;

    const toX = (i)=> x0 + (i*(x1-x0))/Math.max(1,labels.length-1);
    const toY = (v)=> y1 - ((v-min)*(y1-y0))/Math.max(0.0001,(max-min));

    ctx.clearRect(0,0,W,H);

    ctx.beginPath();
    roundRect(ctx, 8, 8, W-16, H-16, 18);
    ctx.fillStyle = "rgba(255,255,255,.55)";
    ctx.fill();

    ctx.strokeStyle = "rgba(100,116,139,.18)";
    ctx.lineWidth = 1;
    const gridLines = 5;
    for(let g=0; g<=gridLines; g++){
      const y = y0 + (g*(y1-y0))/gridLines;
      ctx.beginPath(); ctx.moveTo(x0,y); ctx.lineTo(x1,y); ctx.stroke();
    }

    ctx.fillStyle = "rgba(100,116,139,.9)";
    ctx.font = "12px ui-sans-serif, system-ui";
    for(let g=0; g<=gridLines; g++){
      const v = max - (g*(max-min))/gridLines;
      const y = y0 + (g*(y1-y0))/gridLines;
      ctx.fillText(`${v.toFixed(1)}k`, 18, y+4);
    }

    const step = labels.length > 12 ? 2 : 1;
    for(let i=0; i<labels.length; i+=step){
      const x = toX(i);
      ctx.fillText(labels[i], x-10, H-22);
    }

    const grad = ctx.createLinearGradient(0, y0, 0, y1);
    grad.addColorStop(0, "rgba(79,70,229,.28)");
    grad.addColorStop(1, "rgba(79,70,229,.02)");

    ctx.beginPath();
    seriesA.forEach((v,i)=>{ const x=toX(i), y=toY(v); i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
    ctx.lineTo(toX(labels.length-1), y1);
    ctx.lineTo(toX(0), y1);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.beginPath();
    seriesA.forEach((v,i)=>{ const x=toX(i), y=toY(v); i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
    ctx.strokeStyle = colors?.a || "#4f46e5";
    ctx.lineWidth = 3;
    ctx.stroke();

    if (seriesB && seriesB.length){
      ctx.beginPath();
      seriesB.forEach((v,i)=>{ const x=toX(i), y=toY(v); i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
      ctx.strokeStyle = colors?.b || "#10b981";
      ctx.lineWidth = 2.6;
      ctx.stroke();
    }
  }

  function roundRect(ctx,x,y,w,h,r){
    const rr = Math.min(r, w/2, h/2);
    ctx.moveTo(x+rr, y);
    ctx.arcTo(x+w, y, x+w, y+h, rr);
    ctx.arcTo(x+w, y+h, x, y+h, rr);
    ctx.arcTo(x, y+h, x, y, rr);
    ctx.arcTo(x, y, x+w, y, rr);
    ctx.closePath();
  }

  window.GestiumCharts = window.GestiumCharts || {};
  window.GestiumCharts.drawLineAreaChart = drawLineAreaChart;
})();
