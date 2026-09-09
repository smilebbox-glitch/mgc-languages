/* v6.0.30 — Digital Vehicle 3D learning layer.
 * Local WebGL only. No API, XP, scoring or answer ownership.
 * 3D hotspot buttons delegate to canonical Game Lab controls.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('digital-vehicle-3d-v630')) return;

  const ZONES=Object.freeze({
    bumper:{ru:'Передний бампер',zh:'前保险杠',py:'qián bǎoxiǎnggàng',en:'front bumper',anchor:[3.55,-0.05,0.85],native:'bumper'},
    hood:{ru:'Капот',zh:'发动机盖',py:'fādòngjī gài',en:'hood',anchor:[2.05,0.75,0.82],native:'hood'},
    windshield:{ru:'Лобовое стекло',zh:'挡风玻璃',py:'dǎngfēng bōli',en:'windshield',anchor:[0.65,1.45,0.82],native:'windshield'},
    mirror:{ru:'Наружное зеркало',zh:'后视镜',py:'hòushìjìng',en:'side mirror',anchor:[0.78,1.05,1.28],native:'mirror'},
    door:{ru:'Дверь',zh:'车门',py:'chēmén',en:'door',anchor:[-0.45,0.35,1.22],native:'door'},
    fender:{ru:'Переднее крыло',zh:'前翼子板',py:'qián yìzǐbǎn',en:'front fender',anchor:[2.35,0.18,1.18],native:'fender'},
    headlamp:{ru:'Фара',zh:'前照灯',py:'qiánzhàodēng',en:'headlamp',anchor:[3.18,0.38,0.88],native:'headlamp'},
    wheel:{ru:'Колесо',zh:'车轮',py:'chēlún',en:'wheel',anchor:[2.05,-0.65,1.25],native:'wheel'}
  });
  const ORDER=['bumper','hood','windshield','mirror','door','fender','headlamp','wheel'];

  function state(){
    try{return frontend.has('app-state')?frontend.get('app-state').current():{}}catch(_){return {}}
  }
  function q(sel,scope){return (scope||root.document).querySelector(sel)}
  function qa(sel,scope){return Array.from((scope||root.document).querySelectorAll(sel))}
  function clamp(v,a,b){return Math.max(a,Math.min(b,v))}
  function mat4(){
    return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
  }
  function mul(a,b){
    const o=new Float32Array(16);
    for(let c=0;c<4;c++) for(let r=0;r<4;r++){
      o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];
    }
    return o;
  }
  function translate(x,y,z){
    const m=mat4();m[12]=x;m[13]=y;m[14]=z;return m;
  }
  function scale(x,y,z){
    const m=mat4();m[0]=x;m[5]=y;m[10]=z;return m;
  }
  function rotX(a){
    const c=Math.cos(a),s=Math.sin(a),m=mat4();
    m[5]=c;m[6]=s;m[9]=-s;m[10]=c;return m;
  }
  function rotY(a){
    const c=Math.cos(a),s=Math.sin(a),m=mat4();
    m[0]=c;m[2]=-s;m[8]=s;m[10]=c;return m;
  }
  function perspective(fovy,aspect,near,far){
    const f=1/Math.tan(fovy/2),nf=1/(near-far),m=new Float32Array(16);
    m[0]=f/aspect;m[5]=f;m[10]=(far+near)*nf;m[11]=-1;m[14]=2*far*near*nf;return m;
  }
  function lookAt(eye,target,up){
    let zx=eye[0]-target[0],zy=eye[1]-target[1],zz=eye[2]-target[2];
    let zlen=Math.hypot(zx,zy,zz)||1;zx/=zlen;zy/=zlen;zz/=zlen;
    let xx=up[1]*zz-up[2]*zy,xy=up[2]*zx-up[0]*zz,xz=up[0]*zy-up[1]*zx;
    let xlen=Math.hypot(xx,xy,xz)||1;xx/=xlen;xy/=xlen;xz/=xlen;
    let yx=zy*xz-zz*xy,yy=zz*xx-zx*xz,yz=zx*xy-zy*xx;
    const m=mat4();
    m[0]=xx;m[1]=yx;m[2]=zx;
    m[4]=xy;m[5]=yy;m[6]=zy;
    m[8]=xz;m[9]=yz;m[10]=zz;
    m[12]=-(xx*eye[0]+xy*eye[1]+xz*eye[2]);
    m[13]=-(yx*eye[0]+yy*eye[1]+yz*eye[2]);
    m[14]=-(zx*eye[0]+zy*eye[1]+zz*eye[2]);
    return m;
  }
  function transformPoint(m,p){
    const x=p[0],y=p[1],z=p[2];
    const w=m[3]*x+m[7]*y+m[11]*z+m[15]||1;
    return [(m[0]*x+m[4]*y+m[8]*z+m[12])/w,(m[1]*x+m[5]*y+m[9]*z+m[13])/w,(m[2]*x+m[6]*y+m[10]*z+m[14])/w];
  }

  const cubeVertices=new Float32Array([
    -1,-1, 1, 0,0,1,  1,-1, 1,0,0,1,  1,1,1,0,0,1, -1,1,1,0,0,1,
     1,-1,-1, 0,0,-1, -1,-1,-1,0,0,-1, -1,1,-1,0,0,-1, 1,1,-1,0,0,-1,
    -1, 1, 1, 0,1,0,  1, 1, 1,0,1,0,  1,1,-1,0,1,0, -1,1,-1,0,1,0,
    -1,-1,-1, 0,-1,0, 1,-1,-1,0,-1,0, 1,-1,1,0,-1,0, -1,-1,1,0,-1,0,
     1,-1, 1, 1,0,0, 1,-1,-1,1,0,0, 1,1,-1,1,0,0, 1,1,1,1,0,0,
    -1,-1,-1,-1,0,0,-1,-1,1,-1,0,0,-1,1,1,-1,0,0,-1,1,-1,-1,0,0
  ]);
  const cubeIndices=new Uint16Array([
    0,1,2,0,2,3, 4,5,6,4,6,7, 8,9,10,8,10,11, 12,13,14,12,14,15,
    16,17,18,16,18,19, 20,21,22,20,22,23
  ]);

  function cylinderMesh(segments){
    const v=[],idx=[];
    for(let i=0;i<segments;i++){
      const a=2*Math.PI*i/segments,c=Math.cos(a),s=Math.sin(a);
      v.push(c,s,-1,c,s,0, c,s,1,c,s,0);
    }
    for(let i=0;i<segments;i++){
      const n=(i+1)%segments,a=i*2,b=n*2;
      idx.push(a,b,a+1,b,a+1,b+1);
    }
    return {vertices:new Float32Array(v),indices:new Uint16Array(idx)};
  }
  const cyl=cylinderMesh(18);

  const PARTS=Object.freeze([
    {mesh:'cube',pos:[0,0,0],scale:[2.45,.55,1.08],color:[.10,.42,.70]},
    {mesh:'cube',pos:[2.35,.30,0],scale:[1.10,.30,1.02],color:[.12,.48,.78]},
    {mesh:'cube',pos:[-.35,1.02,0],scale:[1.55,.55,.92],color:[.08,.30,.50]},
    {mesh:'cube',pos:[3.48,-.02,0],scale:[.30,.28,1.12],color:[.08,.34,.58]},
    {mesh:'cube',pos:[-2.65,-.02,0],scale:[.30,.28,1.08],color:[.07,.29,.48]},
    {mesh:'cube',pos:[3.10,.42,.76],scale:[.28,.12,.30],color:[.72,.92,1.0]},
    {mesh:'cube',pos:[3.10,.42,-.76],scale:[.28,.12,.30],color:[.72,.92,1.0]},
    {mesh:'cube',pos:[.75,1.02,1.12],scale:[.22,.10,.16],color:[.14,.39,.58]},
    {mesh:'cube',pos:[.75,1.02,-1.12],scale:[.22,.10,.16],color:[.14,.39,.58]},
    {mesh:'cyl',pos:[2.0,-.62,1.13],scale:[.48,.48,.24],color:[.06,.08,.10]},
    {mesh:'cyl',pos:[2.0,-.62,-1.13],scale:[.48,.48,.24],color:[.06,.08,.10]},
    {mesh:'cyl',pos:[-1.85,-.62,1.13],scale:[.48,.48,.24],color:[.06,.08,.10]},
    {mesh:'cyl',pos:[-1.85,-.62,-1.13],scale:[.48,.48,.24],color:[.06,.08,.10]}
  ]);

  function shader(gl,type,source){
    const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)||'shader');
    return s;
  }
  function program(gl){
    const vs=shader(gl,gl.VERTEX_SHADER,
      'attribute vec3 aPos;attribute vec3 aNormal;uniform mat4 uMVP;uniform mat4 uModel;varying vec3 vN;void main(){gl_Position=uMVP*vec4(aPos,1.0);vN=normalize(mat3(uModel)*aNormal);}');
    const fs=shader(gl,gl.FRAGMENT_SHADER,
      'precision mediump float;uniform vec3 uColor;varying vec3 vN;void main(){vec3 l=normalize(vec3(.35,.8,.55));float d=max(dot(normalize(vN),l),0.0);vec3 c=uColor*(.42+.58*d);gl_FragColor=vec4(c,1.0);}');
    const p=gl.createProgram();gl.attachShader(p,vs);gl.attachShader(p,fs);gl.linkProgram(p);
    if(!gl.getProgramParameter(p,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p)||'program');
    return p;
  }
  function makeMesh(gl,vertices,indices){
    const vb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,vertices,gl.STATIC_DRAW);
    const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);
    return {vb:vb,ib:ib,count:indices.length};
  }

  function Vehicle3D(host,opts){
    this.host=host;this.opts=opts||{};this.yaw=-0.18;this.pitch=-0.08;this.drag=false;this.lastX=0;this.lastY=0;this.raf=0;this.visible=true;
    this.canvas=root.document.createElement('canvas');this.canvas.className='dv3d-canvas';this.canvas.setAttribute('aria-hidden','true');
    this.markerLayer=root.document.createElement('div');this.markerLayer.className='dv3d-markers';
    host.appendChild(this.canvas);host.appendChild(this.markerLayer);
    this.gl=this.canvas.getContext('webgl',{alpha:true,antialias:true,powerPreference:'low-power'});
    if(!this.gl){this.destroy();throw new Error('WebGL unavailable')}
    const gl=this.gl;this.prog=program(gl);this.cube=makeMesh(gl,cubeVertices,cubeIndices);this.cyl=makeMesh(gl,cyl.vertices,cyl.indices);
    this.aPos=gl.getAttribLocation(this.prog,'aPos');this.aNormal=gl.getAttribLocation(this.prog,'aNormal');
    this.uMVP=gl.getUniformLocation(this.prog,'uMVP');this.uModel=gl.getUniformLocation(this.prog,'uModel');this.uColor=gl.getUniformLocation(this.prog,'uColor');
    this.installMarkers();this.installInput();this.resize();this.render();
    this.ro=new ResizeObserver(()=>{this.resize();this.render()});this.ro.observe(host);
    if('IntersectionObserver' in root){
      this.io=new IntersectionObserver(entries=>{this.visible=entries[0]?entries[0].isIntersecting:true;if(this.visible)this.render()},{threshold:.05});this.io.observe(host);
    }
  }
  Vehicle3D.prototype.installMarkers=function(){
    const interactive=!!this.opts.interactive;
    ORDER.forEach(id=>{
      if(!interactive&&this.opts.highlight!==id) return;
      const z=ZONES[id],b=root.document.createElement('button');
      b.type='button';b.className='dv3d-marker';b.dataset.dv3dZone=id;b.innerHTML='<span>'+z.zh+'</span><small>'+z.py+'</small>';
      b.title=z.ru;
      if(!interactive)b.tabIndex=-1;
      if(interactive){
        b.addEventListener('click',()=>this.delegate(id));
      }
      this.markerLayer.appendChild(b);
    });
  };
  Vehicle3D.prototype.delegate=function(id){
    if(typeof this.opts.onZone==='function'){this.opts.onZone(id);return}
    const z=ZONES[id],native=q('[data-hotspot-zone="'+z.native+'"]',this.opts.scope||this.host.parentElement);
    if(native) native.click();
  };
  Vehicle3D.prototype.installInput=function(){
    const c=this.canvas;
    c.addEventListener('pointerdown',ev=>{this.drag=true;this.lastX=ev.clientX;this.lastY=ev.clientY;c.setPointerCapture&&c.setPointerCapture(ev.pointerId)});
    c.addEventListener('pointermove',ev=>{
      if(!this.drag)return;
      const dx=ev.clientX-this.lastX,dy=ev.clientY-this.lastY;this.lastX=ev.clientX;this.lastY=ev.clientY;
      this.yaw=clamp(this.yaw+dx*.008,-.75,.55);this.pitch=clamp(this.pitch+dy*.004,-.22,.12);this.render();
    });
    c.addEventListener('pointerup',()=>{this.drag=false});c.addEventListener('pointercancel',()=>{this.drag=false});
  };
  Vehicle3D.prototype.resize=function(){
    const r=this.host.getBoundingClientRect(),dpr=Math.min(root.devicePixelRatio||1,1.75);
    const w=Math.max(320,Math.floor(r.width*dpr)),h=Math.max(220,Math.floor(r.height*dpr));
    if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h}
  };
  Vehicle3D.prototype.viewMatrices=function(){
    const aspect=this.canvas.width/Math.max(1,this.canvas.height);
    const proj=perspective(Math.PI/4,aspect,.1,100);
    const view=lookAt([8.4,4.2,8.6],[.35,.15,0],[0,1,0]);
    const world=mul(rotY(this.yaw),rotX(this.pitch));
    return {world:world,vp:mul(proj,view)};
  };
  Vehicle3D.prototype.render=function(){
    if(!this.gl||!this.visible)return;
    const gl=this.gl,mats=this.viewMatrices();gl.viewport(0,0,this.canvas.width,this.canvas.height);
    gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.cullFace(gl.BACK);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    gl.useProgram(this.prog);
    PARTS.forEach(part=>{
      let model=mul(mats.world,mul(translate(part.pos[0],part.pos[1],part.pos[2]),scale(part.scale[0],part.scale[1],part.scale[2])));
      const mvp=mul(mats.vp,model),mesh=part.mesh==='cyl'?this.cyl:this.cube;
      gl.bindBuffer(gl.ARRAY_BUFFER,mesh.vb);gl.enableVertexAttribArray(this.aPos);gl.vertexAttribPointer(this.aPos,3,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(this.aNormal);gl.vertexAttribPointer(this.aNormal,3,gl.FLOAT,false,24,12);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,mesh.ib);gl.uniformMatrix4fv(this.uMVP,false,mvp);gl.uniformMatrix4fv(this.uModel,false,model);gl.uniform3fv(this.uColor,new Float32Array(part.color));gl.drawElements(gl.TRIANGLES,mesh.count,gl.UNSIGNED_SHORT,0);
    });
    this.positionMarkers(mats);
  };
  Vehicle3D.prototype.positionMarkers=function(mats){
    const rect=this.host.getBoundingClientRect(),combined=mul(mats.vp,mats.world);
    qa('[data-dv3d-zone]',this.markerLayer).forEach(btn=>{
      const z=ZONES[btn.dataset.dv3dZone],p=transformPoint(combined,z.anchor);
      const x=(p[0]*.5+.5)*rect.width,y=(-p[1]*.5+.5)*rect.height;
      btn.style.left=x+'px';btn.style.top=y+'px';btn.classList.toggle('is-back',p[2]>.98);
    });
  };
  Vehicle3D.prototype.destroy=function(){
    if(this.ro)this.ro.disconnect();if(this.io)this.io.disconnect();if(this.raf)root.cancelAnimationFrame(this.raf);
    if(this.canvas&&this.canvas.parentNode)this.canvas.parentNode.removeChild(this.canvas);
    if(this.markerLayer&&this.markerLayer.parentNode)this.markerLayer.parentNode.removeChild(this.markerLayer);
    this.gl=null;
  };

  function learningCard(zone){
    const z=ZONES[zone]||ZONES.bumper,s=state(),cn=s.language==='chinese';
    return '<div class="dv3d-learning"><span>УЧЕБНЫЙ ОБЪЕКТ</span><b>'+(cn?z.zh:z.en)+'</b>'+
      (cn?'<em>'+z.py+'</em>':'')+'<small>'+z.ru+'</small></div>';
  }
  function hotspot(){
    const stage=q('.car-hotspot-stage');if(!stage||stage.dataset.dv3d==='1')return;
    const nativeSvg=q('svg',stage);if(!nativeSvg)return;
    const host=root.document.createElement('div');host.className='dv3d-host dv3d-hotspot';host.innerHTML='<div class="dv3d-badge"><span>M</span><b>3D VEHICLE · HOTSPOT</b><small>Поверните автомобиль мышкой или пальцем</small></div>';
    stage.insertBefore(host,nativeSvg);stage.classList.add('dv3d-enabled');
    try{stage._dv3d=new Vehicle3D(host,{interactive:true,scope:stage});stage.dataset.dv3d='1'}
    catch(_){host.remove();stage.classList.remove('dv3d-enabled')}
  }
  function contextPanel(mode,highlight){
    const panel=root.document.createElement('section');panel.className='dv3d-context '+mode;
    panel.innerHTML='<div class="dv3d-context-copy"><span>MGC · DIGITAL VEHICLE</span><h3>'+(mode==='assembly'?'Сборочная операция':'Контроль качества')+'</h3><p>'+
      (mode==='assembly'?'Последовательность остаётся канонической; 3D-машина показывает производственный объект и текущий контекст.':'Ответ выбирается в стандартном Quality Gate; 3D-машина показывает проверяемую зону.')+
      '</p>'+learningCard(highlight)+'</div><div class="dv3d-host"></div>';
    const host=q('.dv3d-host',panel);
    try{panel._dv3d=new Vehicle3D(host,{interactive:false,highlight:highlight})}catch(_){panel.classList.add('fallback')}
    return panel;
  }
  function assembly(){
    const stage=q('.game-stage.kind-order');if(!stage||q('.dv3d-context',stage))return;
    const panel=contextPanel('assembly','wheel');stage.insertBefore(panel,stage.firstChild);
  }
  function quality(){
    const stage=q('.game-stage.kind-quality-gate,.game-stage.kind-spec');if(!stage||q('.dv3d-context',stage))return;
    const panel=contextPanel('quality','door');stage.insertBefore(panel,stage.firstChild);
  }
  function showcase(){
    const panel=q('[data-ad-panel="2"]');if(!panel||q('.dv3d-showcase-trigger',panel))return;
    const proof=q('.mgc-showcase-proof',panel);if(!proof)return;
    const btn=root.document.createElement('button');btn.type='button';btn.className='dv3d-showcase-trigger';btn.textContent='3D Digital Vehicle · интерактив →';
    btn.onclick=function(){
      const visual=q('.mgc-showcase-visual',panel);if(!visual)return;
      const old=q('.dv3d-showcase-host',visual);if(old){old.classList.toggle('active');return}
      const host=root.document.createElement('div');host.className='dv3d-showcase-host active';host.innerHTML='<div class="dv3d-badge"><span>M</span><b>WEBGL DIGITAL VEHICLE</b><small>8 учебных зон · local rendering</small></div>';
      visual.appendChild(host);try{host._dv3d=new Vehicle3D(host,{interactive:true,onZone:function(id){
        qa('.dv3d-zone-info',host).forEach(n=>n.remove());host.insertAdjacentHTML('beforeend','<div class="dv3d-zone-info">'+learningCard(id)+'</div>');
      }})}catch(_){host.remove()}
    };proof.appendChild(btn);
  }
  function refresh(){hotspot();assembly();quality();showcase()}
  let scheduled=false;
  function schedule(){if(scheduled)return;scheduled=true;root.requestAnimationFrame(function(){scheduled=false;refresh()})}
  function install(){
    refresh();new MutationObserver(schedule).observe(root.document.body,{subtree:true,childList:true});
  }
  frontend.register('digital-vehicle-3d-v630',{install:install,refresh:refresh,zones:ZONES});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
