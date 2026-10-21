// 把一段 ease-in-out 类运动拟合成 cubic-bezier（网格搜索，约几秒）。来自 B 片分析（B/fit.js），原样复用。
// usage: node fit_bezier.js "t0:v0,t1:v1,..." [起点t] [终点t]   -> 输出 best cubic-bezier x1,y1,x2,y2 与 rmse（归一化进度）
// 例：node fit_bezier.js "0:0,0.2:0.06,0.4:0.3,0.6:0.75,0.8:0.95,1.0:1"
const pts=process.argv[2].split(',').map(s=>s.split(':').map(Number));
const t0=process.argv[3]!==undefined?+process.argv[3]:pts[0][0];
const tEnd=process.argv[4]!==undefined?+process.argv[4]:pts[pts.length-1][0];
const v0=pts[0][1], v1=pts[pts.length-1][1];
const S=pts.map(([t,v])=>[(t-t0)/(tEnd-t0),(v-v0)/(v1-v0)]);
function bez(x1,y1,x2,y2,x){ // solve t for x
 let lo=0,hi=1;for(let i=0;i<40;i++){const m=(lo+hi)/2;const bx=3*(1-m)*(1-m)*m*x1+3*(1-m)*m*m*x2+m*m*m;if(bx<x)lo=m;else hi=m;}
 const m=(lo+hi)/2;return 3*(1-m)*(1-m)*m*y1+3*(1-m)*m*m*y2+m*m*m;}
let best=[1e9];
for(let x1=0;x1<=1;x1+=0.05)for(let y1=-0.5;y1<=1.5;y1+=0.1)for(let x2=0;x2<=1;x2+=0.05)for(let y2=0;y2<=1.6;y2+=0.1){
 let e=0;for(const [x,p] of S){if(x<=0||x>=1)continue;const d=bez(x1,y1,x2,y2,x)-p;e+=d*d;}
 if(e<best[0])best=[e,x1,y1,x2,y2];}
console.log('best cubic-bezier',best.slice(1).map(v=>+v.toFixed(2)).join(','),'rmse',Math.sqrt(best[0]/S.length).toFixed(3));
