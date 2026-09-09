/* v6.0.30 — Powertrain Builder: passenger engine + heavy-truck diesel engine.
 * Local WebGL learning surface only. No API, XP or canonical game scoring ownership.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('powertrain-builder-v630'))return;
  const q=(s,x)=>(x||root.document).querySelector(s);
  const qa=(s,x)=>Array.from((x||root.document).querySelectorAll(s));
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const current=()=>{try{return frontend.get('app-state').current()}catch(_){return {language:'chinese',view:'games'}}};

  const CAR_ENGINE={
    block:['Блок цилиндров','缸体','gāngtǐ','cylinder block',[0,.10,0]],
    head:['Головка блока цилиндров','气缸盖','qìgāng gài','cylinder head',[0,1.30,0]],
    piston:['Поршень','活塞','huósāi','piston',[-1.25,.35,.72]],
    rod:['Шатун','连杆','liángǎn','connecting rod',[-.85,-.10,.72]],
    crank:['Коленчатый вал','曲轴','qūzhóu','crankshaft',[0,-.72,0]],
    cam:['Распределительный вал','凸轮轴','tūlúnzhóu','camshaft',[0,1.72,0]],
    intake:['Впускной коллектор','进气歧管','jìnqì qíguǎn','intake manifold',[.35,.95,1.45]],
    exhaust:['Выпускной коллектор','排气歧管','páiqì qíguǎn','exhaust manifold',[.35,.88,-1.42]],
    injector:['Форсунка','喷油器','pēnyóuqì','fuel injector',[-.55,1.48,.70]],
    spark:['Свеча зажигания','火花塞','huǒhuāsāi','spark plug',[.45,1.52,.70]],
    oil_filter:['Масляный фильтр','机油滤清器','jīyóu lǜqīngqì','oil filter',[-1.92,-.10,1.02]],
    alternator:['Генератор','发电机','fādiànjī','alternator',[1.95,.18,1.00]],
    water_pump:['Водяной насос','水泵','shuǐbèng','water pump',[1.78,.35,-.92]],
    timing:['Цепь ГРМ','正时链条','zhèngshí liàntiáo','timing chain',[1.78,1.08,0]]
  };
  const TRUCK_ENGINE={
    block:['Блок цилиндров','气缸体','qìgāngtǐ','cylinder block',[0,.05,0]],
    head:['Головка блока цилиндров','气缸盖','qìgāng gài','cylinder head',[0,1.42,0]],
    piston:['Поршень','活塞','huósāi','piston',[-1.65,.38,.76]],
    rod:['Шатун','连杆','liángǎn','connecting rod',[-1.20,-.12,.76]],
    crank:['Коленчатый вал','曲轴','qūzhóu','crankshaft',[0,-.82,0]],
    cam:['Распределительный вал','凸轮轴','tūlúnzhóu','camshaft',[0,1.86,0]],
    hp_pump:['Топливный насос высокого давления','高压油泵','gāoyā yóubèng','high-pressure fuel pump',[-2.40,.40,1.10]],
    rail:['Топливная рампа Common Rail','共轨','gòngguǐ','common rail',[0,1.70,1.02]],
    injector:['Форсунка','喷油器','pēnyóuqì','injector',[-.75,1.50,.76]],
    turbo:['Турбокомпрессор','涡轮增压器','wōlún zēngyāqì','turbocharger',[2.65,.72,-1.05]],
    intercooler:['Интеркулер','中冷器','zhōnglěngqì','intercooler',[2.50,.28,1.20]],
    intake:['Впускной коллектор','进气歧管','jìnqì qíguǎn','intake manifold',[.25,1.06,1.55]],
    exhaust:['Выпускной коллектор','排气歧管','páiqì qíguǎn','exhaust manifold',[.25,.92,-1.55]],
    oil_filter:['Масляный фильтр','机油滤清器','jīyóu lǜqīngqì','oil filter',[-2.20,-.15,-1.08]],
    flywheel:['Маховик','飞轮','fēilún','flywheel',[-2.92,-.30,0]]
  };
  const MODES={
    carEngine:{title:'Собери двигатель легкового автомобиля',subtitle:'Бензиновый силовой агрегат',catalog:CAR_ENGINE,kind:'carEngine',taskIds:['block','crank','piston','rod','head','cam','injector','intake','alternator','oil_filter']},
    truckEngine:{title:'Собери двигатель грузовика',subtitle:'Тяжёлый дизельный силовой агрегат',catalog:TRUCK_ENGINE,kind:'truckEngine',taskIds:['block','crank','piston','rod','head','rail','injector','turbo','flywheel','hp_pump']}
  };
  const TASKS={};
  Object.keys(MODES).forEach(mode=>{
    TASKS[mode]=MODES[mode].taskIds.map((zone,i)=>{
      const z=MODES[mode].catalog[zone];
      return {id:mode+'-'+String(i+1).padStart(2,'0'),zone,ru:z[0],zh:z[1],py:z[2],en:z[3],
        phraseZh:'请安装'+z[1]+'。',phrasePy:'qǐng ānzhuāng '+z[2]+'.',phraseRu:'Установите '+z[0].toLowerCase()+'.',phraseEn:'Install the '+z[3]+'.'};
    });
  });

  function id4(){return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1])}
  function mul(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o}
  function tr(x,y,z){const m=id4();m[12]=x;m[13]=y;m[14]=z;return m}
  function sc(x,y,z){const m=id4();m[0]=x;m[5]=y;m[10]=z;return m}
  function rx(a){const c=Math.cos(a),s=Math.sin(a),m=id4();m[5]=c;m[6]=s;m[9]=-s;m[10]=c;return m}
  function ry(a){const c=Math.cos(a),s=Math.sin(a),m=id4();m[0]=c;m[2]=-s;m[8]=s;m[10]=c;return m}
  function rz(a){const c=Math.cos(a),s=Math.sin(a),m=id4();m[0]=c;m[1]=s;m[4]=-s;m[5]=c;return m}
  function perspective(fov,aspect,n,f){const t=1/Math.tan(fov/2),nf=1/(n-f),m=new Float32Array(16);m[0]=t/aspect;m[5]=t;m[10]=(f+n)*nf;m[11]=-1;m[14]=2*f*n*nf;return m}
  function lookAt(e,t,u){let zx=e[0]-t[0],zy=e[1]-t[1],zz=e[2]-t[2],zl=Math.hypot(zx,zy,zz)||1;zx/=zl;zy/=zl;zz/=zl;let xx=u[1]*zz-u[2]*zy,xy=u[2]*zx-u[0]*zz,xz=u[0]*zy-u[1]*zx,xl=Math.hypot(xx,xy,xz)||1;xx/=xl;xy/=xl;xz/=xl;const yx=zy*xz-zz*xy,yy=zz*xx-zx*xz,yz=zx*xy-zy*xx,m=id4();m[0]=xx;m[1]=yx;m[2]=zx;m[4]=xy;m[5]=yy;m[6]=zy;m[8]=xz;m[9]=yz;m[10]=zz;m[12]=-(xx*e[0]+xy*e[1]+xz*e[2]);m[13]=-(yx*e[0]+yy*e[1]+yz*e[2]);m[14]=-(zx*e[0]+zy*e[1]+zz*e[2]);return m}
  function project(m,p){const x=p[0],y=p[1],z=p[2],w=m[3]*x+m[7]*y+m[11]*z+m[15]||1;return [(m[0]*x+m[4]*y+m[8]*z+m[12])/w,(m[1]*x+m[5]*y+m[9]*z+m[13])/w,(m[2]*x+m[6]*y+m[10]*z+m[14])/w]}
  function shader(gl,type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)||'shader');return s}
  function program(gl){const vs=shader(gl,gl.VERTEX_SHADER,'attribute vec3 aPos;attribute vec3 aNormal;uniform mat4 uMVP;uniform mat4 uModel;varying vec3 vN;void main(){vN=mat3(uModel)*aNormal;gl_Position=uMVP*vec4(aPos,1.0);}'),fs=shader(gl,gl.FRAGMENT_SHADER,'precision mediump float;uniform vec3 uColor;varying vec3 vN;void main(){vec3 n=normalize(vN);float l=.32+.68*max(dot(n,normalize(vec3(.42,.84,.35))),0.0);gl_FragColor=vec4(uColor*l,1.0);}'),p=gl.createProgram();gl.attachShader(p,vs);gl.attachShader(p,fs);gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)||'program');return p}
  function mesh(gl,verts,idx){const vb=gl.createBuffer(),ib=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(verts),gl.STATIC_DRAW);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(idx),gl.STATIC_DRAW);return {vb,ib,count:idx.length}}
  function cube(gl){const f=[[-1,-1,1,0,0,1],[1,-1,1,0,0,1],[1,1,1,0,0,1],[-1,1,1,0,0,1],[1,-1,-1,0,0,-1],[-1,-1,-1,0,0,-1],[-1,1,-1,0,0,-1],[1,1,-1,0,0,-1],[-1,1,1,0,1,0],[1,1,1,0,1,0],[1,1,-1,0,1,0],[-1,1,-1,0,1,0],[-1,-1,-1,0,-1,0],[1,-1,-1,0,-1,0],[1,-1,1,0,-1,0],[-1,-1,1,0,-1,0],[1,-1,1,1,0,0],[1,-1,-1,1,0,0],[1,1,-1,1,0,0],[1,1,1,1,0,0],[-1,-1,-1,-1,0,0],[-1,-1,1,-1,0,0],[-1,1,1,-1,0,0],[-1,1,-1,-1,0,0]],v=f.flat(),i=[];for(let k=0;k<6;k++){const o=k*4;i.push(o,o+1,o+2,o,o+2,o+3)}return mesh(gl,v,i)}
  function cylinder(gl,n){const v=[],i=[];for(let s=0;s<=n;s++){const a=s/n*Math.PI*2,x=Math.cos(a),y=Math.sin(a);v.push(x,y,-1,x,y,0,x,y,1,x,y,0)}for(let s=0;s<n;s++){const o=s*2;i.push(o,o+1,o+3,o,o+3,o+2)}return mesh(gl,v,i)}
  function geometry(kind){
    if(kind==='truckEngine')return [
      ['cube',[0,.02,0],[2.85,.82,1.28],[.18,.27,.34],1,'block'],['cyl',[0,-.72,0],[.30,.30,2.50],[.72,.75,.78],2,'crank'],
      ['cyl',[-1.75,.25,.62],[.34,.34,.72],[.62,.67,.72],3,'piston'],['cyl',[-1.05,.25,.62],[.34,.34,.72],[.62,.67,.72],3,'piston'],['cyl',[-.35,.25,.62],[.34,.34,.72],[.62,.67,.72],3,'piston'],['cyl',[.35,.25,.62],[.34,.34,.72],[.62,.67,.72],3,'piston'],['cyl',[1.05,.25,.62],[.34,.34,.72],[.62,.67,.72],3,'piston'],['cyl',[1.75,.25,.62],[.34,.34,.72],[.62,.67,.72],3,'piston'],
      ['cube',[0,1.25,0],[2.75,.38,1.22],[.26,.34,.40],5,'head'],['cyl',[0,1.70,0],[.18,.18,2.35],[.72,.72,.75],6,'cam'],['cube',[0,1.67,1.02],[2.25,.12,.12],[.45,.55,.62],6,'rail'],
      ['cyl',[2.55,.58,-1.05],[.62,.62,.42],[.35,.42,.48],8,'turbo'],['cyl',[-2.82,-.28,0],[.86,.86,.18],[.38,.42,.46],9,'flywheel'],['cube',[-2.35,.40,1.02],[.40,.50,.36],[.28,.36,.43],10,'pump']
    ];
    return [
      ['cube',[0,.05,0],[2.35,.76,1.18],[.20,.30,.38],1,'block'],['cyl',[0,-.66,0],[.27,.27,2.05],[.72,.75,.78],2,'crank'],
      ['cyl',[-1.20,.28,.60],[.31,.31,.66],[.64,.68,.73],3,'piston'],['cyl',[-.40,.28,.60],[.31,.31,.66],[.64,.68,.73],3,'piston'],['cyl',[.40,.28,.60],[.31,.31,.66],[.64,.68,.73],3,'piston'],['cyl',[1.20,.28,.60],[.31,.31,.66],[.64,.68,.73],3,'piston'],
      ['cube',[0,1.14,0],[2.25,.36,1.12],[.28,.36,.43],5,'head'],['cyl',[0,1.58,0],[.17,.17,1.95],[.72,.72,.75],6,'cam'],['cube',[.25,.92,1.36],[1.80,.18,.25],[.30,.42,.48],8,'intake'],['cyl',[1.88,.16,.98],[.58,.58,.36],[.40,.46,.52],9,'alternator'],['cyl',[-1.80,-.08,1.00],[.46,.46,.52],[.26,.34,.40],10,'filter']
    ];
  }

  function Engine3D(host,mode,onZone){this.host=host;this.mode=mode;this.cfg=MODES[mode];this.onZone=onZone;this.yaw=-.35;this.pitch=-.10;this.completed=0;this.complete=false;this.running=false;this.runAngle=0;this.raf=0;this.canvas=root.document.createElement('canvas');this.canvas.className='pt3d-canvas';this.markers=root.document.createElement('div');this.markers.className='pt3d-markers';host.append(this.canvas,this.markers);this.gl=this.canvas.getContext('webgl',{antialias:true,alpha:true})||this.canvas.getContext('experimental-webgl');if(!this.gl)throw new Error('WebGL unavailable');this.prog=program(this.gl);this.cube=cube(this.gl);this.cyl=cylinder(this.gl,28);this.aPos=this.gl.getAttribLocation(this.prog,'aPos');this.aNormal=this.gl.getAttribLocation(this.prog,'aNormal');this.uMVP=this.gl.getUniformLocation(this.prog,'uMVP');this.uModel=this.gl.getUniformLocation(this.prog,'uModel');this.uColor=this.gl.getUniformLocation(this.prog,'uColor');this.addMarkers();this.bind();this.resize();this.render();root.addEventListener('resize',()=>{this.resize();this.render()},{passive:true})}
  Engine3D.prototype.addMarkers=function(){Object.keys(this.cfg.catalog).forEach(id=>{const z=this.cfg.catalog[id],b=root.document.createElement('button');b.type='button';b.className='pt3d-marker';b.dataset.zone=id;b.innerHTML='<span>'+esc(z[1])+'</span><small>'+esc(z[2])+'</small>';b.title=z[0];b.onclick=()=>this.onZone(id);this.markers.appendChild(b)})};
  Engine3D.prototype.bind=function(){const c=this.canvas;let down=false,lx=0,ly=0;c.addEventListener('pointerdown',e=>{down=true;lx=e.clientX;ly=e.clientY;c.setPointerCapture&&c.setPointerCapture(e.pointerId)});c.addEventListener('pointermove',e=>{if(!down)return;this.yaw=Math.max(-1.1,Math.min(.9,this.yaw+(e.clientX-lx)*.008));this.pitch=Math.max(-.35,Math.min(.25,this.pitch+(e.clientY-ly)*.004));lx=e.clientX;ly=e.clientY;this.render()});c.addEventListener('pointerup',()=>down=false);c.addEventListener('pointercancel',()=>down=false)};
  Engine3D.prototype.resize=function(){const r=this.host.getBoundingClientRect(),d=Math.min(root.devicePixelRatio||1,1.6);this.canvas.width=Math.max(320,Math.floor(r.width*d));this.canvas.height=Math.max(280,Math.floor(r.height*d))};
  Engine3D.prototype.setCompleted=function(n){this.completed=n;this.render()};
  Engine3D.prototype.setCurrent=function(id){qa('.pt3d-marker',this.markers).forEach(b=>b.classList.toggle('current',b.dataset.zone===id))};
  Engine3D.prototype.setComplete=function(v){this.complete=!!v;this.completed=10;this.host.classList.toggle('is-running',this.complete);if(this.complete){this.running=true;this.tick()}else{this.running=false;root.cancelAnimationFrame(this.raf);this.render()}};
  Engine3D.prototype.tick=function(){if(!this.running)return;this.runAngle+=this.mode==='truckEngine'?.055:.075;this.render();this.raf=root.requestAnimationFrame(()=>this.tick())};
  Engine3D.prototype.render=function(){const gl=this.gl;if(!gl)return;const aspect=this.canvas.width/Math.max(1,this.canvas.height),p=perspective(Math.PI/4,aspect,.1,100),eye=this.mode==='truckEngine'?[8.6,4.4,8.8]:[7.6,3.9,7.8],v=lookAt(eye,[0,.45,0],[0,1,0]),world=mul(ry(this.yaw),rx(this.pitch)),vp=mul(p,v);gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.prog);geometry(this.cfg.kind).forEach(part=>{const step=part[4]||0;if(step>this.completed&&!this.complete)return;let pos=part[1].slice(),local=id4();if(this.running&&part[5]==='crank')local=rz(this.runAngle);if(this.running&&part[5]==='piston')pos[1]+=Math.sin(this.runAngle*2+pos[0])*.12;const model=mul(world,mul(tr(pos[0],pos[1],pos[2]),mul(local,sc(part[2][0],part[2][1],part[2][2])))),mvp=mul(vp,model),me=part[0]==='cyl'?this.cyl:this.cube;gl.bindBuffer(gl.ARRAY_BUFFER,me.vb);gl.enableVertexAttribArray(this.aPos);gl.vertexAttribPointer(this.aPos,3,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(this.aNormal);gl.vertexAttribPointer(this.aNormal,3,gl.FLOAT,false,24,12);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,me.ib);gl.uniformMatrix4fv(this.uMVP,false,mvp);gl.uniformMatrix4fv(this.uModel,false,model);let color=part[3].slice();if(this.complete&&part[5]==='head')color=[.28,.48,.60];gl.uniform3fv(this.uColor,new Float32Array(color));gl.drawElements(gl.TRIANGLES,me.count,gl.UNSIGNED_SHORT,0)});const rect=this.host.getBoundingClientRect(),comb=mul(vp,world);qa('.pt3d-marker',this.markers).forEach(btn=>{const z=this.cfg.catalog[btn.dataset.zone],pt=project(comb,z[4]);btn.style.left=((pt[0]*.5+.5)*rect.width)+'px';btn.style.top=((-pt[1]*.5+.5)*rect.height)+'px';btn.classList.toggle('is-back',pt[2]>.98)})};

  let session=null;
  function taskLanguage(i){if(session.language==='mixed')return i%2===0?'chinese':'english';return session.language}
  function termHtml(task,i){return taskLanguage(i)==='chinese'?'<b>'+esc(task.zh)+'</b><em>'+esc(task.py)+'</em><small>'+esc(task.ru)+'</small>':'<b>'+esc(task.en)+'</b><small>'+esc(task.ru)+'</small>'}
  function successHtml(task,i){return taskLanguage(i)==='chinese'?'<b>Верно.</b> '+esc(task.phraseZh)+' <em>'+esc(task.phrasePy)+'</em><small>'+esc(task.phraseRu)+'</small>':'<b>Верно.</b> '+esc(task.phraseEn)+' <small>'+esc(task.phraseRu)+'</small>'}
  function renderRail(){const rail=q('#ptRail');if(!rail)return;rail.innerHTML=session.tasks.map((t,i)=>'<div class="pt-rail-item '+(i<session.index?'done':i===session.index?'active':'')+'"><span>'+(i+1)+'</span>'+termHtml(t,i)+'</div>').join('')}
  function renderCurrent(){const task=session.tasks[session.index],box=q('#ptCurrent');if(!task){complete();return}box.innerHTML='<span>ОПЕРАЦИЯ '+(session.index+1)+' / 10</span><h2>Установите узел двигателя</h2><div class="pt-term">'+termHtml(task,session.index)+'</div><p>Поверните 3D-двигатель и выберите нужный узел.</p>';q('#ptStatus').textContent='Каждая успешная операция визуально достраивает силовой агрегат.';session.renderer.setCurrent(task.zone);renderRail();q('#ptProgress').textContent=session.index+' / 10';q('#ptProgressBar').style.width=(session.index*10)+'%'}
  function handleZone(id){if(!session||session.done)return;const task=session.tasks[session.index];if(id!==task.zone){const z=MODES[session.mode].catalog[id];q('#ptStatus').innerHTML='<b>Не этот узел.</b> '+esc(z[0])+' — попробуйте ещё раз.';const b=q('.pt3d-marker[data-zone="'+id+'"]');if(b){b.classList.add('wrong');setTimeout(()=>b.classList.remove('wrong'),480)}return}const b=q('.pt3d-marker[data-zone="'+id+'"]');if(b)b.classList.add('correct');q('#ptStatus').innerHTML=successHtml(task,session.index);session.index++;session.renderer.setCompleted(session.index);q('#ptProgressBar').style.width=(session.index*10)+'%';setTimeout(renderCurrent,650)}
  function startSound(isTruck){try{const C=root.AudioContext||root.webkitAudioContext;if(!C)return;const c=new C(),g=c.createGain(),o1=c.createOscillator(),o2=c.createOscillator(),lfo=c.createOscillator(),lg=c.createGain();o1.type='sawtooth';o2.type='square';lfo.type='sine';o1.frequency.setValueAtTime(isTruck?38:52,c.currentTime);o1.frequency.exponentialRampToValueAtTime(isTruck?72:105,c.currentTime+.8);o2.frequency.setValueAtTime(isTruck?19:26,c.currentTime);o2.frequency.exponentialRampToValueAtTime(isTruck?42:60,c.currentTime+.9);lfo.frequency.value=isTruck?6:9;lg.gain.value=isTruck?6:10;lfo.connect(lg);lg.connect(o1.frequency);g.gain.setValueAtTime(.0001,c.currentTime);g.gain.exponentialRampToValueAtTime(isTruck?.14:.10,c.currentTime+.07);g.gain.exponentialRampToValueAtTime(.035,c.currentTime+.95);g.gain.exponentialRampToValueAtTime(.0001,c.currentTime+1.45);o1.connect(g);o2.connect(g);g.connect(c.destination);o1.start();o2.start();lfo.start();o1.stop(c.currentTime+1.5);o2.stop(c.currentTime+1.5);lfo.stop(c.currentTime+1.5)}catch(_){}}
  function complete(){session.done=true;session.renderer.setComplete(true);startSound(session.mode==='truckEngine');const truck=session.mode==='truckEngine',title=truck?'Дизельный двигатель запущен':'Двигатель запущен';q('#ptCurrent').innerHTML='<div class="pt-complete-card"><span>MGC · POWERTRAIN READY</span><h2>'+title+'</h2><p>Силовой агрегат собран. Коленчатый вал вращается, поршневая группа работает, система перешла в running-state.</p><div class="pt-engine-state"><b>ENGINE RUNNING</b><span>'+(truck?'650':'800')+' RPM</span></div><div class="pt-complete-actions"><button id="ptRepeat" class="primary">Собрать ещё раз</button><button id="ptBack" class="ghost">Вернуться к играм</button></div></div>';q('#ptStatus').textContent='10 из 10 операций выполнены успешно.';q('#ptProgress').textContent='10 / 10';q('#ptProgressBar').style.width='100%';renderRail();q('#ptRepeat').onclick=()=>openBuilder(session.mode);q('#ptBack').onclick=backToGames}
  function backToGames(){if(session&&session.renderer){session.renderer.running=false;root.cancelAnimationFrame(session.renderer.raf)}session=null;const nav=q('[data-view="games"]');if(nav)nav.click()}
  function openBuilder(mode){const cfg=MODES[mode],main=q('#main');if(!main)return;const lang=current().language==='english'?'english':'chinese';session={mode,language:lang,index:0,tasks:TASKS[mode],renderer:null,done:false};main.innerHTML='<section class="pt-shell"><header class="pt-head"><div><span>MGC · POWERTRAIN BUILDER · 3D</span><h1>'+esc(cfg.title)+'</h1><p>'+esc(cfg.subtitle)+' · '+Object.keys(cfg.catalog).length+' интерактивных узлов · 10 операций сборки</p></div><button id="ptClose" class="ghost">← Игры</button></header><div class="pt-language"><button data-pt-lang="chinese" class="'+(lang==='chinese'?'active':'')+'">中文 + Pinyin</button><button data-pt-lang="english" class="'+(lang==='english'?'active':'')+'">English</button><button data-pt-lang="mixed">Mixed</button></div><div class="pt-progress"><span id="ptProgress">0 / 10</span><i><b id="ptProgressBar"></b></i></div><div class="pt-layout"><aside class="pt-task" id="ptCurrent"></aside><div class="pt-model"><div id="pt3dHost" class="pt3d-host"><div class="pt3d-badge"><span>⚙</span><b>POWERTRAIN 3D</b><small>Вращайте и выбирайте узлы</small></div><div class="pt-combustion"></div></div><div class="pt-status" id="ptStatus"></div></div><aside class="pt-rail" id="ptRail"></aside></div></section>';q('#ptClose').onclick=backToGames;qa('[data-pt-lang]').forEach(btn=>btn.onclick=()=>{session.language=btn.dataset.ptLang;qa('[data-pt-lang]').forEach(x=>x.classList.toggle('active',x===btn));renderCurrent()});try{session.renderer=new Engine3D(q('#pt3dHost'),mode,handleZone);renderCurrent()}catch(_){q('#pt3dHost').innerHTML='<div class="pt-fallback"><b>3D недоступно на этом устройстве</b><p>Откройте сервис в современном браузере с WebGL.</p></div>'}}

  function injectCards(){if(current().view!=='games'||current().gameSession)return;const main=q('#main');if(!main||q('.powertrain-builder-entry',main))return;const anchor=q('.assembly-builder-entry',main)||q('.game-grid',main);if(!anchor)return;const wrap=root.document.createElement('section');wrap.className='powertrain-builder-entry';wrap.innerHTML='<div class="section-title"><div><span class="kicker">POWERTRAIN BUILDER · 3D</span><h2>Соберите двигатель</h2><p>Изучайте силовой агрегат через реальные узлы: от блока и коленвала до турбокомпрессора и Common Rail.</p></div></div><div class="pt-entry-grid">'+Object.keys(MODES).map(k=>'<button data-pt-open="'+k+'"><span>'+esc(MODES[k].subtitle)+'</span><h3>'+esc(MODES[k].title)+'</h3><p>'+Object.keys(MODES[k].catalog).length+' интерактивных узлов · 10 готовых заданий</p><b>Начать →</b></button>').join('')+'</div>';anchor.parentNode.insertBefore(wrap,anchor.nextSibling);qa('[data-pt-open]',wrap).forEach(b=>b.onclick=()=>openBuilder(b.dataset.ptOpen))}
  let pending=false;function schedule(){if(pending)return;pending=true;root.requestAnimationFrame(()=>{pending=false;injectCards()})}
  function install(){injectCards();new MutationObserver(schedule).observe(root.document.body,{subtree:true,childList:true})}
  frontend.register('powertrain-builder-v630',{install,open:openBuilder,modes:MODES,tasks:TASKS});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
