/* v6.0.30 — Heavy Truck 3D learning example.
 * Generic Chinese heavy tractor architecture, SHACMAN-class reference only.
 * No logos, external assets, API, XP, scoring or answer ownership.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('digital-truck-3d-v630')) return;

  const TRUCK_ZONES=Object.freeze({
    cab:{ru:'Кабина',zh:'驾驶室',py:'jiàshǐshì',en:'cab',anchor:[2.00,1.45,0.92]},
    grille:{ru:'Решётка радиатора',zh:'散热器格栅',py:'sànrèqì géshān',en:'radiator grille',anchor:[3.12,.88,.92]},
    bumper:{ru:'Передний бампер',zh:'前保险杠',py:'qián bǎoxiǎnggàng',en:'front bumper',anchor:[3.30,.24,.92]},
    headlamp:{ru:'Фара',zh:'前照灯',py:'qiánzhàodēng',en:'headlamp',anchor:[3.18,.62,1.18]},
    fuel_tank:{ru:'Топливный бак',zh:'燃油箱',py:'rányóuxiāng',en:'fuel tank',anchor:[.20,.12,1.16]},
    fifth_wheel:{ru:'Седельно-сцепное устройство',zh:'第五轮',py:'dìwǔlún',en:'fifth wheel',anchor:[-.92,.80,0]},
    drive_axle:{ru:'Ведущая ось',zh:'驱动桥',py:'qūdòngqiáo',en:'drive axle',anchor:[-2.08,-.18,.92]},
    wheel:{ru:'Колесо',zh:'车轮',py:'chēlún',en:'wheel',anchor:[-2.34,-.62,1.18]}
  });
  const ORDER=['cab','grille','bumper','headlamp','fuel_tank','fifth_wheel','drive_axle','wheel'];

  function q(sel,scope){return (scope||root.document).querySelector(sel)}
  function qa(sel,scope){return Array.from((scope||root.document).querySelectorAll(sel))}
  function clamp(v,a,b){return Math.max(a,Math.min(b,v))}
  function id4(){return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1])}
  function mul(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o}
  function tr(x,y,z){const m=id4();m[12]=x;m[13]=y;m[14]=z;return m}
  function sc(x,y,z){const m=id4();m[0]=x;m[5]=y;m[10]=z;return m}
  function ry(a){const c=Math.cos(a),s=Math.sin(a),m=id4();m[0]=c;m[2]=-s;m[8]=s;m[10]=c;return m}
  function rx(a){const c=Math.cos(a),s=Math.sin(a),m=id4();m[5]=c;m[6]=s;m[9]=-s;m[10]=c;return m}
  function perspective(fov,aspect,n,f){const t=1/Math.tan(fov/2),nf=1/(n-f),m=new Float32Array(16);m[0]=t/aspect;m[5]=t;m[10]=(f+n)*nf;m[11]=-1;m[14]=2*f*n*nf;return m}
  function lookAt(e,t,u){let zx=e[0]-t[0],zy=e[1]-t[1],zz=e[2]-t[2],zl=Math.hypot(zx,zy,zz)||1;zx/=zl;zy/=zl;zz/=zl;let xx=u[1]*zz-u[2]*zy,xy=u[2]*zx-u[0]*zz,xz=u[0]*zy-u[1]*zx,xl=Math.hypot(xx,xy,xz)||1;xx/=xl;xy/=xl;xz/=xl;const yx=zy*xz-zz*xy,yy=zz*xx-zx*xz,yz=zx*xy-zy*xx,m=id4();m[0]=xx;m[1]=yx;m[2]=zx;m[4]=xy;m[5]=yy;m[6]=zy;m[8]=xz;m[9]=yz;m[10]=zz;m[12]=-(xx*e[0]+xy*e[1]+xz*e[2]);m[13]=-(yx*e[0]+yy*e[1]+yz*e[2]);m[14]=-(zx*e[0]+zy*e[1]+zz*e[2]);return m}
  function project(m,p){const x=p[0],y=p[1],z=p[2],w=m[3]*x+m[7]*y+m[11]*z+m[15]||1;return[(m[0]*x+m[4]*y+m[8]*z+m[12])/w,(m[1]*x+m[5]*y+m[9]*z+m[13])/w,(m[2]*x+m[6]*y+m[10]*z+m[14])/w]}

  const cubeV=new Float32Array([
    -1,-1,1,0,0,1,1,-1,1,0,0,1,1,1,1,0,0,1,-1,1,1,0,0,1,
    1,-1,-1,0,0,-1,-1,-1,-1,0,0,-1,-1,1,-1,0,0,-1,1,1,-1,0,0,-1,
    -1,1,1,0,1,0,1,1,1,0,1,0,1,1,-1,0,1,0,-1,1,-1,0,1,0,
    -1,-1,-1,0,-1,0,1,-1,-1,0,-1,0,1,-1,1,0,-1,0,-1,-1,1,0,-1,0,
    1,-1,1,1,0,0,1,-1,-1,1,0,0,1,1,-1,1,0,0,1,1,1,1,0,0,
    -1,-1,-1,-1,0,0,-1,-1,1,-1,0,0,-1,1,1,-1,0,0,-1,1,-1,-1,0,0
  ]);
  const cubeI=new Uint16Array([0,1,2,0,2,3,4,5,6,4,6,7,8,9,10,8,10,11,12,13,14,12,14,15,16,17,18,16,18,19,20,21,22,20,22,23]);
  function cylMesh(n){const v=[],i=[];for(let k=0;k<n;k++){const a=2*Math.PI*k/n,c=Math.cos(a),s=Math.sin(a);v.push(c,s,-1,c,s,0,c,s,1,c,s,0)}for(let k=0;k<n;k++){const m=(k+1)%n,a=k*2,b=m*2;i.push(a,b,a+1,b,a+1,b+1)}return{v:new Float32Array(v),i:new Uint16Array(i)}}
  const cyl=cylMesh(18);

  const TRUCK_PARTS=Object.freeze([
    {mesh:'cube',pos:[1.92,.78,0],scale:[1.05,1.38,1.04],color:[.12,.36,.62]},
    {mesh:'cube',pos:[2.98,.70,0],scale:[.18,.74,.92],color:[.08,.18,.27]},
    {mesh:'cube',pos:[3.28,.17,0],scale:[.24,.22,1.02],color:[.08,.28,.48]},
    {mesh:'cube',pos:[2.98,1.28,.70],scale:[.16,.18,.22],color:[.74,.94,1]},
    {mesh:'cube',pos:[2.98,1.28,-.70],scale:[.16,.18,.22],color:[.74,.94,1]},
    {mesh:'cube',pos:[-.55,.20,0],scale:[2.00,.16,.78],color:[.18,.23,.28]},
    {mesh:'cube',pos:[.20,.18,1.03],scale:[.78,.38,.30],color:[.22,.28,.31]},
    {mesh:'cube',pos:[-.92,.78,0],scale:[.44,.10,.58],color:[.10,.13,.16]},
    {mesh:'cyl',pos:[2.02,-.60,1.12],scale:[.54,.54,.25],color:[.04,.05,.06]},
    {mesh:'cyl',pos:[2.02,-.60,-1.12],scale:[.54,.54,.25],color:[.04,.05,.06]},
    {mesh:'cyl',pos:[-1.72,-.60,1.12],scale:[.56,.56,.25],color:[.04,.05,.06]},
    {mesh:'cyl',pos:[-1.72,-.60,-1.12],scale:[.56,.56,.25],color:[.04,.05,.06]},
    {mesh:'cyl',pos:[-2.55,-.60,1.12],scale:[.56,.56,.25],color:[.04,.05,.06]},
    {mesh:'cyl',pos:[-2.55,-.60,-1.12],scale:[.56,.56,.25],color:[.04,.05,.06]}
  ]);

  function shader(gl,type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)||'shader');return s}
  function makeProgram(gl){const vs=shader(gl,gl.VERTEX_SHADER,'attribute vec3 aPos;attribute vec3 aNormal;uniform mat4 uMVP;uniform mat4 uModel;varying vec3 vN;void main(){gl_Position=uMVP*vec4(aPos,1.0);vN=normalize(mat3(uModel)*aNormal);}'),fs=shader(gl,gl.FRAGMENT_SHADER,'precision mediump float;uniform vec3 uColor;varying vec3 vN;void main(){vec3 l=normalize(vec3(.4,.8,.5));float d=max(dot(normalize(vN),l),0.0);gl_FragColor=vec4(uColor*(.40+.60*d),1.0);}'),p=gl.createProgram();gl.attachShader(p,vs);gl.attachShader(p,fs);gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)||'program');return p}
  function mesh(gl,v,i){const vb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,v,gl.STATIC_DRAW);const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,i,gl.STATIC_DRAW);return{vb:vb,ib:ib,count:i.length}}

  function Truck3D(host){
    this.host=host;this.yaw=-.18;this.pitch=-.06;this.drag=false;this.lastX=0;this.lastY=0;
    this.canvas=root.document.createElement('canvas');this.canvas.className='dv3d-canvas';this.canvas.setAttribute('aria-hidden','true');
    this.markers=root.document.createElement('div');this.markers.className='dv3d-markers';host.appendChild(this.canvas);host.appendChild(this.markers);
    this.gl=this.canvas.getContext('webgl',{alpha:true,antialias:true,powerPreference:'low-power'});if(!this.gl)throw new Error('WebGL unavailable');
    const gl=this.gl;this.prog=makeProgram(gl);this.cube=mesh(gl,cubeV,cubeI);this.cyl=mesh(gl,cyl.v,cyl.i);this.aPos=gl.getAttribLocation(this.prog,'aPos');this.aNormal=gl.getAttribLocation(this.prog,'aNormal');this.uMVP=gl.getUniformLocation(this.prog,'uMVP');this.uModel=gl.getUniformLocation(this.prog,'uModel');this.uColor=gl.getUniformLocation(this.prog,'uColor');
    this.addMarkers();this.bind();this.resize();this.render();this.ro=new ResizeObserver(()=>{this.resize();this.render()});this.ro.observe(host);
  }
  Truck3D.prototype.addMarkers=function(){ORDER.forEach(id=>{const z=TRUCK_ZONES[id],b=root.document.createElement('button');b.type='button';b.className='dv3d-marker dv3d-truck-marker';b.dataset.truckZone=id;b.innerHTML='<span>'+z.zh+'</span><small>'+z.py+'</small>';b.title=z.ru;b.onclick=()=>this.showInfo(id);this.markers.appendChild(b)})};
  Truck3D.prototype.showInfo=function(id){const z=TRUCK_ZONES[id];qa('.dv3d-zone-info',this.host).forEach(n=>n.remove());this.host.insertAdjacentHTML('beforeend','<div class="dv3d-zone-info"><div class="dv3d-learning"><span>ГРУЗОВОЙ УЧЕБНЫЙ ОБЪЕКТ</span><b>'+z.zh+'</b><em>'+z.py+'</em><small>'+z.ru+' · '+z.en+'</small></div></div>')};
  Truck3D.prototype.bind=function(){const c=this.canvas;c.addEventListener('pointerdown',e=>{this.drag=true;this.lastX=e.clientX;this.lastY=e.clientY;c.setPointerCapture&&c.setPointerCapture(e.pointerId)});c.addEventListener('pointermove',e=>{if(!this.drag)return;this.yaw=clamp(this.yaw+(e.clientX-this.lastX)*.008,-.8,.65);this.pitch=clamp(this.pitch+(e.clientY-this.lastY)*.004,-.22,.14);this.lastX=e.clientX;this.lastY=e.clientY;this.render()});c.addEventListener('pointerup',()=>this.drag=false);c.addEventListener('pointercancel',()=>this.drag=false)};
  Truck3D.prototype.resize=function(){const r=this.host.getBoundingClientRect(),d=Math.min(root.devicePixelRatio||1,1.75),w=Math.max(320,Math.floor(r.width*d)),h=Math.max(220,Math.floor(r.height*d));if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h}};
  Truck3D.prototype.matrices=function(){const p=perspective(Math.PI/4,this.canvas.width/Math.max(1,this.canvas.height),.1,100),v=lookAt([9.5,4.6,9.4],[.35,.25,0],[0,1,0]),world=mul(ry(this.yaw),rx(this.pitch));return{world:world,vp:mul(p,v)}};
  Truck3D.prototype.render=function(){const gl=this.gl;if(!gl)return;const m=this.matrices();gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.prog);TRUCK_PARTS.forEach(part=>{const model=mul(m.world,mul(tr(part.pos[0],part.pos[1],part.pos[2]),sc(part.scale[0],part.scale[1],part.scale[2]))),mvp=mul(m.vp,model),me=part.mesh==='cyl'?this.cyl:this.cube;gl.bindBuffer(gl.ARRAY_BUFFER,me.vb);gl.enableVertexAttribArray(this.aPos);gl.vertexAttribPointer(this.aPos,3,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(this.aNormal);gl.vertexAttribPointer(this.aNormal,3,gl.FLOAT,false,24,12);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,me.ib);gl.uniformMatrix4fv(this.uMVP,false,mvp);gl.uniformMatrix4fv(this.uModel,false,model);gl.uniform3fv(this.uColor,new Float32Array(part.color));gl.drawElements(gl.TRIANGLES,me.count,gl.UNSIGNED_SHORT,0)});const rect=this.host.getBoundingClientRect(),comb=mul(m.vp,m.world);qa('[data-truck-zone]',this.markers).forEach(btn=>{const p=project(comb,TRUCK_ZONES[btn.dataset.truckZone].anchor);btn.style.left=((p[0]*.5+.5)*rect.width)+'px';btn.style.top=((-p[1]*.5+.5)*rect.height)+'px';btn.classList.toggle('is-back',p[2]>.98)})};

  function installTruckSelector(){
    const panel=q('[data-ad-panel="2"]'),proof=panel&&q('.mgc-showcase-proof',panel);if(!panel||!proof)return;
    const carBtn=q('.dv3d-showcase-trigger',proof);if(carBtn&&!carBtn.dataset.vehicleLabel){carBtn.textContent='Легковой автомобиль · 3D';carBtn.dataset.vehicleLabel='car'}
    if(q('.dv3d-truck-trigger',proof))return;
    const btn=root.document.createElement('button');btn.type='button';btn.className='dv3d-showcase-trigger dv3d-truck-trigger';btn.textContent='Грузовик класса SHACMAN · 3D';btn.title='Учебный пример тяжёлого китайского тягача без фирменного брендинга';
    btn.onclick=function(){
      const visual=q('.mgc-showcase-visual',panel);if(!visual)return;
      const carHost=q('.dv3d-showcase-host',visual);if(carHost)carHost.classList.remove('active');
      let host=q('.dv3d-truck-host',visual);if(host){host.classList.toggle('active');return}
      host=root.document.createElement('div');host.className='dv3d-showcase-host dv3d-truck-host active';host.innerHTML='<div class="dv3d-badge"><span>M</span><b>HEAVY TRUCK · 3D</b><small>SHACMAN-class reference · без логотипа</small></div>';
      visual.appendChild(host);try{host._truck3d=new Truck3D(host)}catch(_){host.remove()}
    };
    proof.appendChild(btn);
  }
  function install(){installTruckSelector();new MutationObserver(installTruckSelector).observe(root.document.body,{subtree:true,childList:true})}
  frontend.register('digital-truck-3d-v630',{install:install,zones:TRUCK_ZONES});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
