"use strict";
(function(){
const DISC=[["theatre","Théâtre"],["musique","Musique"],["danse","Danse"],["cirque","Cirque"],["humour","Humour"],["cinema","Cinéma"],["lettres","Littérature et conférences"],["jeune","Jeune public"],["expo","Expositions et vernissages"],["autre","Autre / à préciser"]];
const DISC_LABEL=Object.fromEntries(DISC);
// Stations de métro (coordonnées approximatives) et lignes, dans l'ordre
const STN={"Angrignon":[45.4462,-73.6036],"Monk":[45.4510,-73.5932],"Jolicoeur":[45.4570,-73.5818],"Verdun":[45.4594,-73.5718],"De l'Église":[45.4620,-73.5668],"LaSalle":[45.4708,-73.5662],"Charlevoix":[45.4782,-73.5695],"Lionel-Groulx":[45.4829,-73.5797],"Atwater":[45.4898,-73.5862],"Guy-Concordia":[45.4958,-73.5795],"Peel":[45.5010,-73.5750],"McGill":[45.5040,-73.5717],"Place-des-Arts":[45.5080,-73.5687],"Saint-Laurent":[45.5107,-73.5649],"Berri-UQAM":[45.5153,-73.5612],"Beaudry":[45.5190,-73.5560],"Papineau":[45.5236,-73.5522],"Frontenac":[45.5332,-73.5521],"Préfontaine":[45.5418,-73.5545],"Joliette":[45.5470,-73.5513],"Pie-IX":[45.5536,-73.5516],"Viau":[45.5610,-73.5476],"Assomption":[45.5694,-73.5469],"Cadillac":[45.5770,-73.5464],"Langelier":[45.5829,-73.5432],"Radisson":[45.5893,-73.5398],"Honoré-Beaugrand":[45.5965,-73.5352],
 "Côte-Vertu":[45.5141,-73.6829],"Du Collège":[45.5093,-73.6744],"De la Savane":[45.5005,-73.6614],"Namur":[45.4949,-73.6527],"Plamondon":[45.4945,-73.6385],"Côte-Sainte-Catherine":[45.4924,-73.6332],"Snowdon":[45.4855,-73.6280],"Villa-Maria":[45.4797,-73.6197],"Vendôme":[45.4738,-73.6040],"Place-Saint-Henri":[45.4771,-73.5867],"Georges-Vanier":[45.4889,-73.5764],"Lucien-L'Allier":[45.4950,-73.5711],"Bonaventure":[45.4979,-73.5672],"Square-Victoria–OACI":[45.5019,-73.5631],"Place-d'Armes":[45.5061,-73.5600],"Champ-de-Mars":[45.5104,-73.5563],"Sherbrooke":[45.5193,-73.5689],"Mont-Royal":[45.5245,-73.5817],"Laurier":[45.5276,-73.5891],"Rosemont":[45.5314,-73.5976],"Beaubien":[45.5354,-73.6045],"Jean-Talon":[45.5394,-73.6136],"Jarry":[45.5434,-73.6287],"Crémazie":[45.5461,-73.6383],"Sauvé":[45.5508,-73.6560],"Henri-Bourassa":[45.5557,-73.6680],
 "Côte-des-Neiges":[45.4965,-73.6230],"Université-de-Montréal":[45.5032,-73.6178],"Édouard-Montpetit":[45.5103,-73.6125],"Outremont":[45.5200,-73.6150],"Acadie":[45.5236,-73.6236],"Parc":[45.5309,-73.6243],"De Castelnau":[45.5355,-73.6199],"Fabre":[45.5468,-73.6077],"D'Iberville":[45.5530,-73.6022],"Saint-Michel":[45.5597,-73.6000],"Jean-Drapeau":[45.5120,-73.5332]};
const LIGNES=[
 {nom:"verte",c:"var(--cinema)",st:["Angrignon","Monk","Jolicoeur","Verdun","De l'Église","LaSalle","Charlevoix","Lionel-Groulx","Atwater","Guy-Concordia","Peel","McGill","Place-des-Arts","Saint-Laurent","Berri-UQAM","Beaudry","Papineau","Frontenac","Préfontaine","Joliette","Pie-IX","Viau","Assomption","Cadillac","Langelier","Radisson","Honoré-Beaugrand"]},
 {nom:"orange",c:"var(--humour)",st:["Côte-Vertu","Du Collège","De la Savane","Namur","Plamondon","Côte-Sainte-Catherine","Snowdon","Villa-Maria","Vendôme","Place-Saint-Henri","Lionel-Groulx","Georges-Vanier","Lucien-L'Allier","Bonaventure","Square-Victoria–OACI","Place-d'Armes","Champ-de-Mars","Berri-UQAM","Sherbrooke","Mont-Royal","Laurier","Rosemont","Beaubien","Jean-Talon","Jarry","Crémazie","Sauvé","Henri-Bourassa"]},
 {nom:"jaune",c:"var(--cirque)",st:["Berri-UQAM","Jean-Drapeau"]},
 {nom:"bleue",c:"var(--musique)",st:["Snowdon","Côte-des-Neiges","Université-de-Montréal","Édouard-Montpetit","Outremont","Acadie","Parc","De Castelnau","Jean-Talon","Fabre","D'Iberville","Saint-Michel"]}];
const LIGNES_DE=n=>LIGNES.filter(l=>l.st.includes(n));
const POINTS=Object.keys(STN).sort((a,b)=>a.localeCompare(b,"fr")).map(n=>[n,STN[n][0],STN[n][1]]);
const DN=["dim.","lun.","mar.","mer.","jeu.","ven.","sam."];
const MOIS=["janv.","févr.","mars","avr.","mai","juin","juil.","août","sept.","oct.","nov.","déc."];
const MOIS_L=["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];
const JOURS=["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"];
const d=s=>{const[y,m,dd]=s.split("-").map(Number);return new Date(y,m-1,dd)};
const iso=x=>x.getFullYear()+"-"+String(x.getMonth()+1).padStart(2,"0")+"-"+String(x.getDate()).padStart(2,"0");
const addDays=(s,n)=>{const x=d(s);x.setDate(x.getDate()+n);return iso(x)};
const monday=s=>{const x=d(s);return addDays(s,-((x.getDay()+6)%7))};
const fmt=s=>{const x=d(s);return x.getDate()+" "+MOIS[x.getMonth()]};
const fmtLong=s=>{const x=d(s);return JOURS[x.getDay()]+" "+x.getDate()+" "+MOIS[x.getMonth()]};
const esc=t=>String(t).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $=id=>document.getElementById(id);
function km(a,b){const R=6371,r=x=>x*Math.PI/180,dl=r(b.lat-a.lat),dn=r(b.lon-a.lon);
  const h=Math.sin(dl/2)**2+Math.cos(r(a.lat))*Math.cos(r(b.lat))*Math.sin(dn/2)**2;return 2*R*Math.asin(Math.sqrt(h))}
const fmtKm=k=>k<1?Math.round(k*10)*100+" m":(Math.round(k*10)/10).toString().replace(".",",")+" km";

let D=null,byId=[],CFG={},FEST=[],FESTID={};
let st={on:Object.fromEntries(DISC.map(x=>[x[0],true])),view:"week",day:null,week:null,month:null,kids:false,pt:"",rayon:0,sort:"time",custom:null};
try{const s=JSON.parse(localStorage.getItem("cal-mtl")||"null");if(s&&s.on)Object.assign(st,s,{on:Object.assign(st.on,s.on)})}catch(e){}
st.pt="";st.rayon=0;st.sort="time";st.custom=null;st.fest=null;st.q="";
if(st.view==="month")st.view="week"; // la vue Mois est retirée // l'outil « Près de » est retiré
const save=()=>{try{localStorage.setItem("cal-mtl",JSON.stringify(st))}catch(e){}};

function origin(){if(st.pt==="addr")return st.custom;const p=POINTS.find(p=>p[0]===st.pt);return p?{lat:p[1],lon:p[2],libelle:p[0]}:null}
function dist(lieu){const o=origin(),c=D.lieux[lieu];if(!o||!c)return null;return km(o,c)}
function inRadius(lieu){if(!st.rayon||!origin())return true;const k=dist(lieu);return k!==null&&k<=st.rayon}
// Un événement peut être dans plusieurs disciplines (champ « aussi », ex. théâtre + danse)
// Un spectacle jeune public apparaît aussi dans sa discipline d'origine (« sous », ex. théâtre)
const discs=e=>[...new Set([e.discipline].concat(e.aussi||[],e.sous&&DISC_LABEL[e.sous]?[e.sous]:[]))];
const visible=()=>D.events.filter(e=>(st.fest?e.festival===st.fest:discs(e).some(k=>st.on[k]))&&inRadius(e.lieu));
const byTime=(a,b)=>(a.heure||"99").localeCompare(b.heure||"99");
const byDist=(a,b)=>{const x=dist(a.lieu),y=dist(b.lieu);return (x===null?1e9:x)-(y===null?1e9:y)||byTime(a,b)};

// ---- Agenda export (Google link + .ics file)
const pad=n=>String(n).padStart(2,"0");
function span(e){ // local start/end "YYYYMMDDTHHMMSS", or all-day "YYYYMMDD"
  const day=e.date.replace(/-/g,"");
  if(!e.heure)return{allDay:true,start:day,end:addDays(e.date,1).replace(/-/g,"")};
  const[h,m]=e.heure.split(":").map(Number);const s=d(e.date);s.setHours(h,m);const t=new Date(s.getTime()+2*3600e3);
  return{allDay:false,start:day+"T"+pad(h)+pad(m)+"00",end:iso(t).replace(/-/g,"")+"T"+pad(t.getHours())+pad(t.getMinutes())+"00"};
}
function descr(e){return (e.heure?"":"Heure à confirmer. ")+(e.resume?e.resume+"\n":"")+(e.prix?"Prix : "+e.prix+"\n":"")+"Détails : "+(e.billets||e.url)+"\n(Calendrier culturel montréalais)"}
function gcal(e){const s=span(e);
  return "https://calendar.google.com/calendar/render?action=TEMPLATE&text="+encodeURIComponent(e.titre)+"&dates="+s.start+"/"+s.end+
    (s.allDay?"":"&ctz=America/Toronto")+"&location="+encodeURIComponent(e.lieu+", Montréal")+"&details="+encodeURIComponent(descr(e))}
const icsEsc=t=>String(t).replace(/\\/g,"\\\\").replace(/;/g,"\\;").replace(/,/g,"\\,").replace(/\n/g,"\\n");
function ics(e){const s=span(e),now=new Date().toISOString().replace(/[-:]/g,"").slice(0,15)+"Z";
  const L=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Calendrier culturel montrealais//FR","CALSCALE:GREGORIAN","METHOD:PUBLISH",
   "BEGIN:VTIMEZONE","TZID:America/Toronto","BEGIN:DAYLIGHT","TZOFFSETFROM:-0500","TZOFFSETTO:-0400","TZNAME:EDT","DTSTART:19700308T020000","RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU","END:DAYLIGHT",
   "BEGIN:STANDARD","TZOFFSETFROM:-0400","TZOFFSETTO:-0500","TZNAME:EST","DTSTART:19701101T020000","RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU","END:STANDARD","END:VTIMEZONE",
   "BEGIN:VEVENT","UID:"+e.date+"-"+Math.abs([...e.url].reduce((h,c)=>(h*31+c.charCodeAt(0))|0,7))+"@calendrier-culturel-mtl","DTSTAMP:"+now,
   s.allDay?"DTSTART;VALUE=DATE:"+s.start:"DTSTART;TZID=America/Toronto:"+s.start,
   s.allDay?"DTEND;VALUE=DATE:"+s.end:"DTEND;TZID=America/Toronto:"+s.end,
   "SUMMARY:"+icsEsc(e.titre),"LOCATION:"+icsEsc(e.lieu+", Montréal"),"URL:"+e.url,"DESCRIPTION:"+icsEsc(descr(e)),"END:VEVENT","END:VCALENDAR"];
  return L.join("\r\n")+"\r\n"}
function saveIcs(i){const e=byId[i];if(!e)return;
  const name=(e.date+" "+e.titre).normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^\w -]+/g,"").trim().slice(0,60).replace(/\s+/g,"-")+".ics";
  const url=URL.createObjectURL(new Blob([ics(e)],{type:"text/calendar;charset=utf-8"}));
  const a=document.createElement("a");a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),4000);
}

function flagsHTML(e){
  return (e.complet?'<span class="badge">Complet</span>':"")+(e.serie?`<span class="badge s">à l'affiche jusqu'au ${fmt(e.serie.fin)}</span>`:"");
}
function lieuHTML(e,grand){
  const c=D.lieux[e.lieu],k=dist(e.lieu);
  const q=c&&c.quartier?`<span class="q">${esc(c.quartier)}</span>`:"";
  const m=c&&c.metro?`<span class="metro" title="Station la plus proche, à ${fmtKm(c.metro.km)}">${LIGNES_DE(c.metro.nom).map(l=>`<i style="background:${l.c}"></i>`).join("")}${esc(c.metro.nom)}</span>`:"";
  const kmTag=origin()?`<span class="km">${k===null?"distance ?":fmtKm(k)}</span>`:"";
  return `<div class="lieu${grand?" grand":""}"><span class="pin" aria-hidden="true"></span><span class="nom">${esc(e.lieu)}</span>${q}${m}${kmTag}</div>`;
}
function calHTML(e){
  const src=(D.sources[e.source]||{}).nom||e.source;
  return `<div class="cal"><span class="calk">+ mon agenda :</span><a href="${esc(gcal(e))}" target="_blank" rel="noopener" title="Ajouter à Google Agenda">Google</a><button type="button" data-ics="${e._i}" title="Fichier .ics pour Apple Calendrier, Outlook, etc.">iCal</button><span class="src">source : ${esc(src)}</span></div>`;
}
const heureTxt=e=>e.heure?e.heure.replace(":"," h "):e.serie?"voir horaire":"heure à confirmer";
const sousTag=e=>e.discipline==="jeune"&&e.sous&&DISC_LABEL[e.sous]?`<span class="sous">${esc(DISC_LABEL[e.sous])}</span>`:"";
function evHTML(e){
  return `<article class="ev" data-d="${e.discipline}" style="--c:var(--${e.discipline})"><a class="main" href="${esc(e.url)}" target="_blank" rel="noopener" title="${esc(DISC_LABEL[e.discipline]||"")}">
    <div class="tm">${heureTxt(e)}</div><div>${lieuHTML(e)}<div class="t">${esc(e.titre)}${flagsHTML(e)}</div>${sousTag(e)}</div></a>
    ${calHTML(e)}</article>`;
}
// Vue Semaine : ligne compacte (un survol) ; le détail est dans la vue Jour
const MAX_SEM=Infinity; // tout afficher dans la semaine
function rowHTML(e){const c=D.lieux[e.lieu];
  return `<button type="button" class="row${e.aussi&&e.aussi.length?" multi":""}${e.festival&&FESTID[e.festival]?" enfest":""}" data-ev="${e._i}" style="--c:var(--${e.discipline})${e.aussi&&e.aussi.length?`;--c2:var(--${e.aussi[0]})`:""}${e.festival&&FESTID[e.festival]?`;--f:${FESTID[e.festival].coul}`:""}" title="${discs(e).map(k=>esc(DISC_LABEL[k]||"")).join(" · ")}"><span class="rti">${esc(e.titre)}${e.complet?` <span class="cpl">complet</span>`:""}</span><span class="rl"><b class="${e.heure?"":"nh"}">${heureTxt(e)}</b> · <span class="v">${esc(e.lieu)}</span>${c&&c.metro?` · ${esc(c.metro.nom)}`:""}${e.festival&&!st.fest&&FESTID[e.festival]?` <span class="fx" style="--f:${FESTID[e.festival].coul};--ft:${FESTID[e.festival].coulTxt}">${esc(FESTID[e.festival].court)}</span>`:""}</span></button>`}
// Écouter / bande-annonce : seulement des liens vérifiés (page de l'événement, MusicBrainz, TMDb).
// Sinon, un simple lien de recherche, présenté honnêtement comme une recherche.
const NOMS_LIEN={bandcamp:"Bandcamp",spotify:"Spotify",apple:"Apple Music",soundcloud:"SoundCloud",youtube:"YouTube",vimeo:"Vimeo",site:"Site officiel","bande-annonce":"▶ Bande-annonce"};
function ecouteHTML(e){
  const d=discs(e),film=d.includes("cinema"),mus=d.includes("musique");
  if(!film&&!mus)return"";
  if(e.liens&&e.liens.length){
    const parNom={};e.liens.forEach(l=>{const k=l.nom||"";(parNom[k]=parNom[k]||[]).push(l)});
    return `<div class="ecoute"><span>${film?"Voir :":"Écouter :"}</span>${Object.entries(parNom).map(([nom,ls])=>
      `${nom&&Object.keys(parNom).length>1?`<em>${esc(nom)}</em>`:""}${ls.map(l=>`<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label||NOMS_LIEN[l.type]||l.type)}</a>`).join("")}`).join("")}</div>`}
  const q=encodeURIComponent(film?artiste(e.titre)+" bande-annonce":artiste(e.titre)+" "+e.lieu.split(/[–(]/)[0]+" Montréal");
  return `<div class="ecoute rech"><span>Pas encore de lien vérifié :</span><a href="https://www.youtube.com/results?search_query=${q}" target="_blank" rel="noopener">chercher sur YouTube</a></div>`}
// Vue Jour : fiche détaillée
function artiste(t){return t.split(/ – | - |, avec | avec |\(|:| \+ /)[0].trim()}
function detailHTML(e){
  const c=D.lieux[e.lieu];
  const gmaps="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(e.lieu+", Montréal");
  const ecoute=ecouteHTML(e);
  const carte=c&&CFG.cartes!==false?`<iframe class="carte" loading="lazy" title="Carte : ${esc(e.lieu)}" src="https://www.openstreetmap.org/export/embed.html?bbox=${(c.lon-.006).toFixed(4)}%2C${(c.lat-.0035).toFixed(4)}%2C${(c.lon+.006).toFixed(4)}%2C${(c.lat+.0035).toFixed(4)}&layer=mapnik&marker=${c.lat}%2C${c.lon}"></iframe>`:"";
  // Affiche : image fournie par la salle (formulaire), sinon l'image de promotion de la page officielle,
  // affichée depuis son site d'origine avec le crédit et le lien. Si elle ne charge pas, le cadre disparaît.
  const aff=e.image?{url:e.image,credit:"fournie par l'organisateur"}:(CFG.affiches!==false&&e.affiche)||null;
  const img=aff?`<figure class="det-aff"><a href="${esc(aff.lien||e.url)}" target="_blank" rel="noopener"><img src="${esc(aff.url)}" alt="Affiche : ${esc(e.titre)}" loading="lazy" referrerpolicy="no-referrer" onerror="const m=this.closest('.det-media');this.closest('figure').remove();if(m)m.classList.remove('deux')"></a><figcaption>Image : ${esc(aff.credit||"")}</figcaption></figure>`:"";
  // L'affiche et la carte à droite, avec prix, billets et itinéraire juste dessous ; écouter et agenda sous le résumé.
  const actions=`<div class="actions">
        ${e.prix?`<span class="prix">${esc(e.prix)}</span>`:""}
        <a class="btn" href="${esc(e.billets||e.url)}" target="_blank" rel="noopener">${e.billets?"Acheter des billets":"Voir l'événement"}</a>
        <a class="btn ghost" href="${gmaps}" target="_blank" rel="noopener">Itinéraire</a>
      </div>`;
  const extra=`${ecoute}${calHTML(e)}`;
  const media=img||carte?`<div class="det-media${img&&carte?" deux":""}">${img}${carte}</div>`:"";
  return `<article class="ev det" id="ev-${e._i}" data-d="${e.discipline}" style="--c:var(--${e.discipline})">
    <div class="det-info">
      <h3 class="t"><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.titre)}</a></h3>
      <div class="det-top"><div class="tm${e.heure?"":" nh"}">${heureTxt(e)}</div><span class="disc">${discs(e).map(k=>esc(DISC_LABEL[k]||"")).join(" · ")}</span>${sousTag(e)}${e.festival&&FESTID[e.festival]?`<button type="button" class="fx" data-fest="${e.festival}" style="--f:${FESTID[e.festival].coul};--ft:${FESTID[e.festival].coulTxt}">${/^festival/i.test(FESTID[e.festival].court)?"":"Festival · "}${esc(FESTID[e.festival].court)}</button>`:""}${flagsHTML(e)}</div>
      ${lieuHTML(e,true)}
      ${e.resume?`<p class="resume">${esc(e.resume)}</p>`:""}
      ${media?"":actions}
      ${extra}
    </div>
    ${media?`<div class="det-side">${media}${actions}</div>`:""}
  </article>`;
}
function renderChips(){
  const counts={};D.events.forEach(e=>discs(e).forEach(k=>counts[k]=(counts[k]||0)+1));
  counts.expo=(counts.expo||0)+D.expos.filter(x=>!estMusee(x)).length;
  $("chips").innerHTML=DISC.map(([k,l])=>{const n=counts[k]||0;
    return `<button type="button" class="chip" style="--c:var(--${k})" data-k="${k}" data-d="${k}" aria-pressed="${n&&st.on[k]?"true":"false"}" ${n?"":"disabled"}><span class="dot"></span>${l} <span class="n">${n||"aucun"}</span></button>`}).join("");
}
const inRange=s=>s>=D.debut&&s<=D.fin;
function weekDays(){return [0,1,2,3,4,5,6].map(i=>addDays(st.week,i))}
function renderStrip(){
  const v=visible();$("strip").hidden=st.view==="month";
  $("strip").innerHTML=weekDays().map(s=>{const n=inRange(s)?v.filter(e=>e.date===s).length:"—",x=d(s);
    return `<button type="button" class="day${inRange(s)?"":" nodata"}${s===iso(new Date())?" today":""}" data-d="${s}" aria-current="${st.view==="day"&&st.day===s}" ${inRange(s)?"":"disabled"}><span class="dn">${s===iso(new Date())?"auj.":DN[x.getDay()]}</span><span class="dd">${x.getDate()}</span><span class="dc">${n}</span></button>`}).join("");
}
function renderNav(){
  let label,prevOk,nextOk;
  if(st.view==="month"){const[y,m]=st.month.split("-").map(Number);label=MOIS_L[m-1]+" "+y;
    prevOk=st.month>D.debut.slice(0,7);nextOk=st.month<D.fin.slice(0,7)}
  else if(st.view==="week"){const end=addDays(st.week,6);label=fmt(st.week)+" → "+fmt(end);prevOk=st.week>D.debut;nextOk=end<D.fin}
  else{label=fmtLong(st.day);prevOk=st.day>D.debut;nextOk=st.day<D.fin}
  $("navLabel").textContent=label;$("prev").disabled=!prevOk;$("next").disabled=!nextOk;
  // coverage note
  const from=st.view==="month"?st.month+"-01":st.view==="week"?st.week:st.day;
  const to=st.view==="month"?st.month+"-31":st.view==="week"?addDays(st.week,6):st.day;
  const p=$("partial");p.hidden=to<=D.completJusqua;
  p.textContent=`Après le ${fmt(D.completJusqua)}, la liste est partielle : surtout des concerts et les spectacles des grandes salles. Elle se complète à mesure que la date approche.`;
}
/* Expositions en cours : elles n'ont pas de date de représentation, on les montre « ouvertes ce jour-là » */
// Musées : expositions présentées dans un musée ou un grand lieu d'exposition → onglet Musées. Le reste (vernissages,
// petites expos de galeries, expos courtes) reste au calendrier.
const RE_MUSEE=/mus[ée]e|mbam|mccord|pointe-à-callière|centre canadien d'architecture|\bcca\b|\bphi\b|biosphère|biodôme|planétarium|insectarium|jardin botanique|château (ramezay|dufresne)|écomusée|\bmem\b|centre des mémoires|arsenal art contemporain|fonderie darling|galerie de l'uqam|oasis immersion|maison saint-gabriel|centre d'histoire/i;
const estMusee=x=>RE_MUSEE.test(x.lieu||"");
function exposDu(j){if(!inRange(j))return[];const ok=x=>st.fest?x.festival===st.fest:(st.on.expo&&!estMusee(x));
  return D.expos.filter(x=>ok(x)&&x.debut<=j&&x.fin>=j&&inRadius(x.lieu))}
function expoCarte(j){const n=exposDu(j).length;
  return n?`<button type="button" class="expocard" data-act="jour" data-d="${j}"><b>${n}</b> expo${n>1?"s":""} ouverte${n>1?"s":""}<span>voir la liste →</span></button>`:""}
function exposJourHTML(j){
  const L=exposDu(j).sort(origin()&&st.sort==="dist"?(a,b)=>{const x=dist(a.lieu),y=dist(b.lieu);return (x===null?1e9:x)-(y===null?1e9:y)}:(a,b)=>a.fin.localeCompare(b.fin));
  if(!L.length)return"";const bientot=addDays(j,7);
  return `<h2 class="label xhead">Expositions ouvertes ce jour-là · ${L.length}</h2><p class="xnote">Sans heure de représentation : vérifie les heures d'ouverture du lieu.</p>
    <div class="xjour">${L.map(x=>`<article class="xd"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titre)}</a>${lieuHTML(x)}
      <div class="end${x.fin<=bientot?" soon":""}">${x.fin<=bientot?"Se termine le ":"Jusqu'au "}${fmt(x.fin)}</div></article>`).join("")}</div>`}
/* ---------- Festivals ---------- */
const MOIS_N=["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];
function festEtat(f){
  const today=iso(new Date()),d2=f.fin,d1=f.debut||(d2&&d2>=today?today:d2); // sans date de début : « jusqu'au … »
  if(d1&&d2&&d1<=today&&today<=d2)return{etat:"cours",reste:Math.round((d(d2)-d(today))/864e5)};
  if(d1&&d1>today)return{etat:"bientot",dans:Math.round((d(d1)-d(today))/864e5)};
  // Édition passée (ou sans dates) : la prochaine revient d'habitude au même mois
  const m=f.mois?f.mois-1:(d1?d(d1).getMonth():null),now=new Date();
  const an=m===null?null:(m>now.getMonth()?now.getFullYear():now.getFullYear()+1);
  return{etat:"plus",mois:m,an};
}
const fDates=f=>{const d1=f.debut,d2=f.fin;if(!d2)return"";
  return !d1?`jusqu'au ${fmt(d2)}`:d1===d2?fmt(d1):`${fmt(d1)} → ${fmt(d2)}`};
function festOuvert(f){return(f.disciplines||[]).some(k=>st.on[k]!==false)}
function festCompte(id){return D.events.filter(e=>e.festival===id).length+D.expos.filter(x=>x.festival===id).length}
function festChips(j){
  if(!inRange(j)||!FEST.length)return"";
  const L=FEST.filter(f=>{const d1=f.debut||D.debut;return d1&&f.fin&&d1<=j&&j<=f.fin&&festOuvert(f)});
  // Pastille pleine : le festival a des activités datées ce jour-là. Pastille contour : il est en cours,
  // mais rien de daté ce jour-là (ex. une exposition), ou sa programmation n'est pas encore connue.
  const html=L.map(f=>{const n=D.events.filter(e=>e.festival===f.id&&e.date===j).length,x=D.expos.some(e=>e.festival===f.id&&e.debut<=j&&e.fin>=j);
    const info=n?`${n} activité${n>1?"s":""} ce jour-là`:x?"exposition en cours, rien d'autre de daté ce jour-là":"en cours ; programmation de ce jour pas encore connue";
    return `<button type="button" class="fchip${n?"":" vide"}" data-fest="${f.id}" style="--f:${f.coul};--ft:${f.coulTxt}" title="${esc(f.nom)} : ${info}">${esc(f.court)}${n?` <b>${n}</b>`:x?" · expo":""}</button>`}).join("");
  return L.length?`<div class="fchips">${html}</div>`:""}
function ouvrirFestival(id){
  const f=FESTID[id];if(!f)return;
  st.fest=id;st.view="week";const today=iso(new Date());
  const debut=(f.debut&&f.debut>today)?f.debut:today;st.day=inRange(debut)?debut:st.day;st.week=monday(st.day);
  render();window.scrollTo({top:$("navBar").getBoundingClientRect().top+window.scrollY-20,behavior:"smooth"});
}
function renderFestBanner(){
  const b=$("festBanner"),f=st.fest&&FESTID[st.fest];b.hidden=!f;if(!f)return;
  b.style.setProperty("--c",f.coul||`var(--${f.disciplines[0]})`);
  b.innerHTML=`<div><b>${esc(f.nom)}</b><span>${fDates(f)} · ${festCompte(f.id)} activité${festCompte(f.id)>1?"s":""} au calendrier</span></div>
    <div class="fbact">${f.site?`<a href="${esc(f.site)}" target="_blank" rel="noopener">Site officiel ↗</a>`:""}<button type="button" class="btn" data-act="festoff">✕ Tout le calendrier</button></div>`;
}
function festCarte(f){
  const e=festEtat(f),n=festCompte(f.id),c=f.disciplines[0];
  const badge=e.etat==="cours"?`<span class="fbadge on">En cours${e.reste?` · encore ${e.reste} jour${e.reste>1?"s":""}`:" · dernier jour"}</span>`
    :e.etat==="bientot"?`<span class="fbadge">Dans ${e.dans} jour${e.dans>1?"s":""}</span>`:"";
  const quand=e.etat==="plus"?(e.mois===null?"Dates à venir":`Prochaine édition : vers ${MOIS_N[e.mois]} ${e.an} <i>(dates à confirmer)</i>`)
    :`${fDates(f)}${f.verifier?" <i>(à confirmer)</i>":""}`;
  return `<article class="fest" style="--c:${f.coul||`var(--${c})`}">
    <div class="fh"><h3>${esc(f.nom)}</h3>${badge}</div>
    <p class="fd">${quand}${f.lieu?` · ${esc(f.lieu)}`:""}</p>
    <div class="ftags">${f.disciplines.map(k=>`<span style="--c:var(--${k})">${esc(DISC_LABEL[k]||k)}</span>`).join("")}</div>
    <div class="fa">${n?`<button type="button" class="btn" data-fest="${f.id}">Programmation au calendrier · ${n}</button>`
      :`<span class="fwait">${e.etat==="plus"?"Programmation ajoutée quand elle sera en ligne":"Programmation : ajoutée dès qu'elle est en ligne"}</span>`}
      ${f.site?`<a href="${esc(f.site)}" target="_blank" rel="noopener">Site officiel ↗</a>`:""}</div></article>`}
function renderFestivals(){
  const el=$("view");if(!FEST.length){el.innerHTML='<div class="empty">La liste des festivals n\'a pas pu être chargée.</div>';return}
  const L=FEST.filter(festOuvert).map(f=>({f,e:festEtat(f)}));
  const cours=L.filter(x=>x.e.etat==="cours").sort((a,b)=>a.f.fin.localeCompare(b.f.fin));
  const bientot=L.filter(x=>x.e.etat==="bientot").sort((a,b)=>(a.f.debut||a.f.fin).localeCompare(b.f.debut||b.f.fin));
  const prochains=bientot.filter(x=>x.e.dans<=90),loin=bientot.filter(x=>x.e.dans>90);
  const plus=L.filter(x=>x.e.etat==="plus").map(x=>({...x,k:x.e.mois===null?99:(x.e.an*12+x.e.mois)})).sort((a,b)=>a.k-b.k);
  const parMois={};loin.forEach(x=>{const k=(x.f.debut||x.f.fin).slice(0,7);(parMois[k]=parMois[k]||[]).push(x)});
  plus.forEach(x=>{const k=x.e.mois===null?"zz":`${x.e.an}-${String(x.e.mois+1).padStart(2,"0")}`;(parMois[k]=parMois[k]||[]).push(x)});
  const moisLbl=k=>k==="zz"?"Dates à venir":`${MOIS_N[Number(k.slice(5))-1]} ${k.slice(0,4)}`;
  const grille=xs=>`<div class="festgrid">${xs.map(x=>festCarte(x.f)).join("")}</div>`;
  el.innerHTML=`<div class="festview">
    <p class="festintro">Les festivals de l'île, de l'édition en cours à celles de l'an prochain. Quand la programmation d'un festival est en ligne, ses spectacles s'ajoutent au calendrier : clique « Programmation au calendrier ». Les disciplines choisies plus haut filtrent cette liste.</p>
    <h2 class="label">En cours · ${cours.length}</h2>${cours.length?grille(cours):'<p class="empty">Aucun festival en cours pour ces disciplines.</p>'}
    <h2 class="label">Dans les 3 prochains mois · ${prochains.length}</h2>${prochains.length?grille(prochains):'<p class="empty">Rien d\'annoncé pour l\'instant.</p>'}
    <h2 class="label">Plus tard dans l'année</h2>
    ${Object.keys(parMois).sort().map(k=>`<h3 class="fmois">${moisLbl(k)}</h3>${grille(parMois[k])}`).join("")}
  </div>`;
}
/* ---------- Recherche ---------- */
const plat=t=>(t||"").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g," ").trim();
function correspond(mots,...champs){const t=" "+plat(champs.join(" "))+" ";return mots.every(m=>t.includes(" "+m)||t.includes(m))}
function renderRecherche(){
  const mots=plat(st.q).split(" ").filter(Boolean),el=$("view");
  const today=iso(new Date());
  const champsE=e=>[e.titre,e.lieu,(D.lieux[e.lieu]||{}).quartier||"",e.resume||"",e.festival&&FESTID[e.festival]?FESTID[e.festival].nom+" "+FESTID[e.festival].court:"",discs(e).map(k=>DISC_LABEL[k]).join(" ")];
  const ev=D.events.filter(e=>e.date>=today&&correspond(mots,...champsE(e)));
  const ex=D.expos.filter(x=>x.fin>=today&&correspond(mots,x.titre,x.lieu,x.festival&&FESTID[x.festival]?FESTID[x.festival].nom:""));
  const fe=FEST.filter(f=>correspond(mots,f.nom,f.court,f.lieu||""));
  // Une pièce jouée plusieurs soirs : on la montre une fois par jour, mais on regroupe par date
  const par={};ev.slice(0,400).forEach(e=>(par[e.date]=par[e.date]||[]).push(e));
  const n=ev.length+ex.length+fe.length;
  el.innerHTML=`<div class="resultats">
    <h2 class="label">« ${esc(st.q)} » · ${n} résultat${n>1?"s":""}</h2>
    ${n?"":`<p class="empty">Rien trouvé. Essaie un autre mot (nom du groupe, de la pièce, de la salle…). La recherche ignore les accents et les filtres de discipline.</p>`}
    ${fe.length?`<h3 class="fmois">Festivals</h3><div class="festgrid">${fe.map(festCarte).join("")}</div>`:""}
    ${Object.keys(par).sort().map(j=>`<h3 class="fmois">${fmtLong(j)}</h3><div class="rows">${par[j].sort(byTime).map(rowHTML).join("")}</div>`).join("")}
    ${ev.length>400?`<p class="empty">… et ${ev.length-400} autres. Précise ta recherche.</p>`:""}
    ${ex.length?`<h3 class="fmois">Expositions</h3><div class="xjour">${ex.map(x=>`<article class="xd"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titre)}</a>${lieuHTML(x)}<div class="end">Jusqu'au ${fmt(x.fin)}</div></article>`).join("")}</div>`:""}
  </div>`;
}
/* ---------- Festivals de la semaine (une seule rangée, à côté de la date) ---------- */
function renderFestSemaine(){
  const el=$("festSemaine");
  if(st.view!=="week"||st.fest||!FEST.length){el.innerHTML="";return}
  const a=st.week,b=addDays(st.week,6);
  const L=FEST.filter(f=>{const d1=f.debut||D.debut;return f.fin&&d1<=b&&f.fin>=a&&festOuvert(f)});
  el.innerHTML=L.length?`<span class="fslbl">En festival :</span>${L.map(f=>{const n=D.events.filter(e=>e.festival===f.id&&e.date>=a&&e.date<=b).length;
    return `<button type="button" class="fchip${n?"":" vide"}" data-fest="${f.id}" style="--f:${f.coul};--ft:${f.coulTxt}" title="${esc(f.nom)} · ${fDates(f)}">${esc(f.court)}${n?` <b>${n}</b>`:""}</button>`}).join("")}`:"";
}
/* ---------- Musées ---------- */
function renderMusees(){
  const today=iso(new Date()),bientot=addDays(today,21),recent=addDays(today,-14);
  const L=D.expos.filter(x=>estMusee(x)&&x.fin>=today);
  const carte=x=>`<article class="xd mus${x.fin<=bientot?" fin":""}"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titre)}</a>
    <div class="end${x.fin<=bientot?" soon":""}">${x.debut>today?`Ouvre le ${fmt(x.debut)} · `:x.debut>=recent?"Vient d'ouvrir · ":""}${x.fin<=bientot?"Se termine le ":"Jusqu'au "}${fmt(x.fin)}${x.fin.slice(0,4)!==today.slice(0,4)?" "+x.fin.slice(0,4):""}</div>
    ${x.festival&&FESTID[x.festival]?`<button type="button" class="fx" data-fest="${x.festival}" style="--f:${FESTID[x.festival].coul};--ft:${FESTID[x.festival].coulTxt}">${esc(FESTID[x.festival].court)}</button>`:""}</article>`;
  const par={};L.forEach(x=>(par[x.lieu]=par[x.lieu]||[]).push(x));
  const fin=L.filter(x=>x.fin<=bientot).sort((a,b)=>a.fin.localeCompare(b.fin));
  $("view").innerHTML=`<div class="festview">
    <p class="festintro">Les expositions des musées et des grands lieux, qui durent souvent plusieurs mois. Les vernissages, finissages et petites expos de galeries, plus éphémères, restent dans le calendrier (Expositions et vernissages).</p>
    ${fin.length?`<h2 class="label">Dernière chance · se termine dans moins de 3 semaines</h2><div class="xjour">${fin.map(x=>carte(x).replace('<a href','<span class="mlieu">'+esc(x.lieu)+'</span><a href')).join("")}</div>`:""}
    <h2 class="label">Par lieu · ${Object.keys(par).length} musées et lieux · ${L.length} expositions</h2>
    ${Object.keys(par).sort((a,b)=>a.localeCompare(b,"fr")).map(l=>`<section class="musee"><h3 class="fmois">${esc(l)}</h3>${lieuHTML({lieu:l})}<div class="xjour">${par[l].sort((a,b)=>a.fin.localeCompare(b.fin)).map(carte).join("")}</div></section>`).join("")}
  </div>`;
}
function renderView(){
  const v=visible(),el=$("view"),useDist=origin()&&st.sort==="dist";
  $("sortSeg").hidden=!origin()||st.view==="month";
  if(st.view==="month"){
    const[y,m]=st.month.split("-").map(Number);const first=st.month+"-01";let s=monday(first);
    const cells=[];const today=iso(new Date());
    while(true){
      for(let i=0;i<7;i++){const x=d(s),own=x.getMonth()===m-1,ok=own&&inRange(s);
        const list=ok?v.filter(e=>e.date===s):[],nx=ok?exposDu(s).length:0;
        const disc=[...new Set(list.map(e=>e.discipline))];
        cells.push(own?`<button type="button" class="cell${ok?"":" out"}${s===today?" today":""}" data-d="${s}" ${ok?"":"disabled"} aria-label="${esc(fmtLong(s))} : ${list.length} activités">
          <span class="num">${x.getDate()}</span>${ok?`<span class="cnt">${list.length} activité${list.length>1?"s":""}${nx?` <em>+ ${nx} expo${nx>1?"s":""}</em>`:""}</span><span class="dots">${disc.map(k=>`<i style="background:var(--${k})" title="${esc(DISC_LABEL[k])}"></i>`).join("")}</span>
          <span class="peek">${list.sort(byTime).slice(0,3).map(e=>esc(e.titre)).join(" · ")}</span>`:""}</button>`:`<div></div>`);
        s=addDays(s,1)}
      if(d(s).getMonth()!==m-1)break}
    el.innerHTML=`<div class="month">${["lun.","mar.","mer.","jeu.","ven.","sam.","dim."].map(x=>`<div class="mhead">${x}</div>`).join("")}${cells.join("")}</div>`;
  }else if(st.view==="week"){
    el.innerHTML=`<div class="board">${weekDays().map(s=>{
      const list=inRange(s)?v.filter(e=>e.date===s).sort(useDist?byDist:byTime):[];
      const xc=expoCarte(s);
      const plus=list.length-MAX_SEM;
      const auj=s===iso(new Date());
      return `<section class="col${list.length||xc?"":" emptycol"}${auj?" today":""}"><button type="button" class="colhead" data-act="jour" data-d="${s}" ${inRange(s)?"":"disabled"}>${auj?`<i class="aujtag">aujourd'hui</i>`:""}${fmtLong(s)} <span>${list.length}</span></button>
        ${list.length?`<div class="rows">${list.slice(0,MAX_SEM).map(rowHTML).join("")}</div>`:""}${plus>0?`<button type="button" class="more" data-act="jour" data-d="${s}">+ ${plus} autre${plus>1?"s":""} · voir la journée →</button>`:""}${xc}${list.length||xc?"":`<div class="empty">${inRange(s)?"Rien pour ces critères.":"Hors de la période couverte."}</div>`}</section>`}).join("")}</div>`;
  }else{
    const list=v.filter(e=>e.date===st.day).sort(useDist?byDist:byTime);
    el.innerHTML=`${st.fest?"":festChips(st.day)}<div class="dayhead"><button type="button" class="btn ghost" data-act="semaine">← Toute la semaine</button><h2 class="label">${st.day===iso(new Date())?`<i class="aujtag">aujourd'hui</i> `:""}${fmtLong(st.day)} · ${list.length} activité${list.length>1?"s":""}</h2></div>
      <div class="dayview">${list.map(detailHTML).join("")||(exposDu(st.day).length?'<div class="empty">Aucun spectacle daté pour ces critères ce jour-là.</div>':'<div class="empty">Rien pour ces critères ce jour-là.</div>')}</div>${exposJourHTML(st.day)}`;
  }
}
function periodBounds(){
  if(st.view==="month")return[st.month+"-01",st.month+"-31"];
  if(st.view==="week")return[st.week,addDays(st.week,6)];
  return[st.day,st.day]}
function renderExpos(){
  $("expos").hidden=true;return; // remplacé par l'onglet Musées et la carte « expos ouvertes »
  const[from,to]=periodBounds();
  let list=D.expos.filter(x=>x.debut<=to&&x.fin>=from&&inRadius(x.lieu));
  list.sort(origin()?(a,b)=>{const x=dist(a.lieu),y=dist(b.lieu);return (x===null?1e9:x)-(y===null?1e9:y)}:(a,b)=>a.fin.localeCompare(b.fin));
  const soon=addDays(to>D.fin?D.fin:to,7);
  $("xcount").textContent=`(${list.length} pendant cette période)`;
  $("xlist").innerHTML=list.map(x=>{const s=x.fin<=soon,k=dist(x.lieu);
    const tag=x.discipline&&x.discipline!=="expo"?`<span class="km">${esc(DISC_LABEL[x.discipline]||x.discipline)}</span>`:"";
    return `<div class="x" style="--c:var(--${x.discipline&&x.discipline!=="expo"&&DISC_LABEL[x.discipline]?x.discipline:"expo"})"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titre)}</a>${tag}<div class="p">${esc(x.lieu)}${origin()?`<span class="km">${k===null?"distance ?":fmtKm(k)}</span>`:""}</div>
      <div class="end${s?" soon":""}">${s?"Se termine le ":"Jusqu'au "}${fmt(x.fin)}${x.fin.slice(0,4)!==from.slice(0,4)?" "+x.fin.slice(0,4):""}</div></div>`}).join("")||'<div class="empty">Aucune exposition pour ces critères.</div>';
}
function renderStat(){
  if(!$("stat"))return;
  const[from,to]=periodBounds();const n=visible().filter(e=>e.date>=from&&e.date<=to).length,by={};D.events.forEach(e=>by[e.source]=(by[e.source]||0)+1);
  $("stat").innerHTML=`<b>${n}</b>activité${n>1?"s":""} dans cette période · ${D.events.length} au total<br>`+
    Object.entries(by).map(([k,c])=>`${esc((D.sources[k]||{}).nom||k)} ${c}`).join(" · ");
}
function renderNear(){
  const o=origin();$("addrBox").hidden=st.pt!=="addr";
  if(st.pt==="addr"&&o)$("nearMsg").textContent=`Point trouvé : ${o.libelle} (position approximative).`;
  else if(o)$("nearMsg").textContent="Distances à vol d'oiseau. Positions des salles approximatives (± quelques centaines de mètres).";
  else if(st.pt!=="addr")$("nearMsg").textContent="";
}
function clamp(){
  const today=iso(new Date());const start=inRange(today)?today:D.debut;
  if(!st.day||!inRange(st.day))st.day=start;
  if(!st.week||addDays(st.week,6)<D.debut||st.week>D.fin)st.week=monday(st.day);
  if(!st.month||st.month<D.debut.slice(0,7)||st.month>D.fin.slice(0,7))st.month=st.day.slice(0,7);
}
function render(){
  if(!D)return;clamp();
  renderChips();
  const rq=(st.q||"").trim().length>=2,fv=st.view==="fest"||st.view==="musee"||rq;$("navBar").hidden=fv;$("strip").hidden=fv||st.view==="month";$("partial").hidden=true;
  $("qClear").hidden=!st.q;document.body.classList.toggle("en-recherche",rq);
  if(rq){renderRecherche();$("expos").hidden=true;$("festBanner").hidden=true}
  else if(st.view==="musee"){renderMusees();$("expos").hidden=true;$("festBanner").hidden=true}
  else if(fv){renderFestivals();$("expos").hidden=true;$("festBanner").hidden=true}
  else{renderNav();renderStrip();renderView();renderExpos();renderFestBanner()}
  renderFestSemaine();
  renderStat();renderNear();
  ["week","day","fest","musee"].forEach(k=>$("v-"+k).setAttribute("aria-pressed",st.view===k));
  $("s-time").setAttribute("aria-pressed",st.sort!=="dist");$("s-dist").setAttribute("aria-pressed",st.sort==="dist");
  $("pt").value=st.pt;$("rayon").value=String(st.rayon);
  save();
}
function renderFooter(){
  $("foot").innerHTML=`<div>Sources : ${Object.values(D.sources).filter(x=>x.url).map(x=>`<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.nom)}</a>`).join(", ")}, et sites de salles. Seule l'île de Montréal est gardée. Les activités non culturelles (cours, informatique, sport, séances du conseil) et les événements annulés ou reportés sont écartés.</div>
  <div>Le classement par discipline se fait d'après les titres et les catégories des sources : certains sont des suppositions; un spectacle peut être dans deux disciplines. Les positions des salles sont approximatives. Les concerts sans heure connue s'ajoutent à votre agenda comme événements d'une journée.</div>
  <div>Cartes : © les contributeurs d'<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>. <a href="sources.html">Nos sources et salles</a> · <a href="salles.html">Pour les salles et organismes</a> · <a href="rapport.json">Rapport de la dernière collecte</a></div>`;
  $("majInfo").textContent=`Mis à jour le ${fmtLong(D.miseAJour).toLowerCase()} · événements du ${fmt(D.debut)} au ${fmt(D.fin)}.`;
}

$("pt").innerHTML=`<option value="">— n'importe où —</option>`+POINTS.map(p=>`<option value="${esc(p[0])}">Métro ${esc(p[0])}</option>`).join("")+`<option value="addr">Une adresse…</option>`;

$("chips").addEventListener("click",e=>{const b=e.target.closest(".chip");if(!b||b.disabled)return;st.on[b.dataset.k]=!st.on[b.dataset.k];render()});
$("strip").addEventListener("click",e=>{const b=e.target.closest(".day");if(!b||b.disabled)return;
  if(st.view==="day"&&st.day===b.dataset.d){st.week=monday(st.day);st.view="week"}else{st.day=b.dataset.d;st.view="day"}render()});
$("view").addEventListener("click",e=>{
  const c=e.target.closest(".cell");if(c&&!c.disabled){st.day=c.dataset.d;st.week=monday(st.day);st.view="day";render();return}
  const r=e.target.closest(".row[data-ev]");if(r){const ev=byId[r.dataset.ev];if(ev){sortirRecherche();st.day=ev.date;st.view="day";render();
    const a=$("ev-"+ev._i);if(a){a.classList.add("flash");a.scrollIntoView({block:"start",behavior:"smooth"})}}return}
  const fb=e.target.closest("[data-fest]");if(fb){sortirRecherche();ouvrirFestival(fb.dataset.fest);return}
  const xj=e.target.closest('[data-act="jour"]');if(xj){st.day=xj.dataset.d;st.view="day";render();window.scrollTo({top:$("navLabel").getBoundingClientRect().top+window.scrollY-20});return}
  if(e.target.closest('[data-act="semaine"]')){st.week=monday(st.day);st.view="week";render();window.scrollTo({top:$("navLabel").getBoundingClientRect().top+window.scrollY-20});return}
  const b=e.target.closest("[data-ics]");if(b)saveIcs(Number(b.dataset.ics));
});
let qT=null;
$("q").addEventListener("input",e=>{clearTimeout(qT);qT=setTimeout(()=>{st.q=e.target.value;render()},180)});
$("q").addEventListener("keydown",e=>{if(e.key==="Escape"){e.target.value="";st.q="";render()}});
$("qClear").addEventListener("click",()=>{$("q").value="";st.q="";render();$("q").focus()});
const sortirRecherche=()=>{if(st.q){st.q="";$("q").value=""}};
$("v-fest").addEventListener("click",()=>{sortirRecherche();st.view="fest";st.fest=null;render()});
$("festSemaine").addEventListener("click",e=>{const b=e.target.closest("[data-fest]");if(b)ouvrirFestival(b.dataset.fest)});
$("festBanner").addEventListener("click",e=>{if(e.target.closest("[data-act=\"festoff\"]")){st.fest=null;render()}});
$("v-musee").addEventListener("click",()=>{sortirRecherche();st.view="musee";st.fest=null;render()});
$("v-week").addEventListener("click",()=>{sortirRecherche();if(st.view==="day")st.week=monday(st.day);st.view="week";render()});
$("v-day").addEventListener("click",()=>{sortirRecherche();if(st.view==="week"&&!(st.day>=st.week&&st.day<=addDays(st.week,6)))st.day=inRange(st.week)?st.week:D.debut;st.view="day";render()});
function step(n){
  if(st.view==="month"){const[y,m]=st.month.split("-").map(Number);const x=new Date(y,m-1+n,1);st.month=iso(x).slice(0,7)}
  else if(st.view==="week"){st.week=addDays(st.week,7*n)}
  else{st.day=addDays(st.day,n);st.week=monday(st.day)}
  render()}
$("prev").addEventListener("click",()=>step(-1));
$("next").addEventListener("click",()=>step(1));
$("s-time").addEventListener("click",()=>{st.sort="time";render()});
$("s-dist").addEventListener("click",()=>{st.sort="dist";render()});
$("allOn").addEventListener("click",()=>{DISC.forEach(([k])=>st.on[k]=true);st.rayon=0;render()});
$("pt").addEventListener("change",e=>{st.pt=e.target.value;st.sort=st.pt?"dist":"time";render();if(st.pt==="addr"&&!st.custom)$("addr").focus()});
$("rayon").addEventListener("change",e=>{st.rayon=Number(e.target.value);render()});
// Carte du métro : décorative (une évocation), sans filtre

let dernierGeo=0;
async function findAddr(){
  const q=$("addr").value.trim();if(!q)return;
  const msg=$("nearMsg");msg.className="msg";
  if(Date.now()-dernierGeo<1500){msg.textContent="Un instant…";return}
  dernierGeo=Date.now();msg.textContent="Recherche de l'adresse…";$("addrGo").disabled=true;
  try{
    const u="https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=ca&bounded=1&viewbox=-73.98,45.71,-73.47,45.40&accept-language=fr&q="+encodeURIComponent(/montr/i.test(q)?q:q+", Montréal");
    const r=await fetch(u,{headers:{"Accept":"application/json"}});if(!r.ok)throw new Error(r.status);
    const j=await r.json();
    if(j&&j[0]){const lat=+j[0].lat,lon=+j[0].lon;st.custom={lat,lon,libelle:j[0].display_name.split(",").slice(0,3).join(",")};st.sort="dist";render()}
    else{msg.className="msg err";msg.textContent="Adresse non trouvée sur l'île de Montréal. Essaie avec le numéro et la rue."}
  }catch(err){msg.className="msg err";msg.textContent="La recherche d'adresse ne répond pas. Choisis plutôt une station de métro."}
  finally{$("addrGo").disabled=false}
}
$("addrGo").addEventListener("click",findAddr);
$("addr").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();findAddr()}});

fetch("config.json",{cache:"no-store"}).then(r=>r.ok?r.json():{}).then(c=>{
  CFG=c||{};if(c&&c.formulaireEvenement){const a=$("lienProposer");a.href=c.formulaireEvenement;a.hidden=false}
  if(c&&c.don){$("donLien").href=c.don;if(c.donTexte)$("donLien").textContent=c.donTexte;$("donLien").hidden=false;$("don").hidden=false}
  if(c&&c.donInterac){$("donCourriel").textContent=c.donInterac;$("donInterac").hidden=false;$("don").hidden=false;
    $("donCopier").addEventListener("click",()=>{const ok=()=>{$("donCopier").textContent="Copié ✓"};
      try{navigator.clipboard.writeText(c.donInterac).then(ok,()=>{})}catch(e){}})}
  if(D)render();
}).catch(()=>{});
fetch("festivals.json",{cache:"no-store"}).then(r=>r.ok?r.json():[]).catch(()=>[]).then(L=>{
  FEST=Array.isArray(L)?L:[];FEST.forEach(f=>{FESTID[f.id]=f;f.court=f.court||f.nom;f.disciplines=(f.disciplines||[]).filter(k=>DISC_LABEL[k]);if(!f.disciplines.length)f.disciplines=["autre"]});
  // Une couleur propre à chaque festival (dans l'ordre des dates : deux festivals simultanés n'ont pas la même)
  const PAL=[["#7048e8","#fff"],["#0ca678","#fff"],["#f76707","#fff"],["#e64980","#fff"],["#1971c2","#fff"],["#fab005","#121212"],
    ["#862e9c","#fff"],["#2b8a3e","#fff"],["#c92a2a","#fff"],["#15aabf","#121212"],["#8d6e63","#fff"],["#343a40","#fff"]];
  FEST.slice().sort((a,b)=>(a.debut||a.fin||"9").localeCompare(b.debut||b.fin||"9")).forEach((f,i)=>{const p=f.couleur?[f.couleur,"#fff"]:PAL[i%PAL.length];f.coul=p[0];f.coulTxt=p[1]});
  if(D)render()});
fetch("data.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(j=>{
  D=j;
  // Pièces, danse et cirque « à l'affiche du X au Y » : une entrée par jour, pour qu'elles suivent les filtres
  const mot=t=>(t||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").split(/[^a-z0-9]+/).find(w=>w.length>2)||"";
  const deja=new Set(D.events.map(e=>e.date+"|"+e.lieu+"|"+mot(e.titre)));
  const series=[];D.expos=D.expos.filter(x=>{
    if(!x.discipline||x.discipline==="expo"||!DISC_LABEL[x.discipline])return true;
    for(let s=x.debut<D.debut?D.debut:x.debut;s<=x.fin&&s<=D.fin;s=addDays(s,1))
      if(!deja.has(s+"|"+x.lieu+"|"+mot(x.titre)))series.push({date:s,heure:null,discipline:x.discipline,titre:x.titre,lieu:x.lieu,url:x.url,complet:false,jeunePublic:x.discipline==="jeune",sous:x.sous,aussi:x.aussi,festival:x.festival,resume:x.resume,prix:x.prix,billets:x.billets,source:x.source||"salles",serie:{debut:x.debut,fin:x.fin}});
    return false});
  D.events=D.events.concat(series).sort((a,b)=>(a.date+(a.heure||"99")).localeCompare(b.date+(b.heure||"99")));
  D.events.forEach((e,i)=>{if(e.jeunePublic&&e.discipline!=="jeune"){e.sous=e.discipline;e.discipline="jeune"}e._i=i;byId[i]=e});
  for(const n in D.lieux){const c=D.lieux[n];if(!c)continue;let best=null;
    for(const s in STN){const k=km(c,{lat:STN[s][0],lon:STN[s][1]});if(!best||k<best.km)best={nom:s,km:k}}
    if(best&&best.km<=1.3)c.metro=best}
  if(!D.debut&&D.semaine){D.debut=D.semaine[0];D.fin=D.semaine[D.semaine.length-1]}
  if(!D.completJusqua)D.completJusqua=D.fin;
  renderFooter();render();
}).catch(()=>{$("view").innerHTML='<div class="empty">Les événements n\'ont pas pu être chargés. Rechargez la page.</div>'});
})();
