"use strict";
(function(){
// Langue de la page (<html lang="en"> pour la version anglaise, dans /en/) ; BASE : chemin vers les données du site
const EN=(document.documentElement.lang||"").toLowerCase().startsWith("en");
const L=(fr,en)=>EN?en:fr,LL=L;
const SRC_EN={ville:"City of Montréal",theatre:"theatre websites",salles:"venue websites",galeries:"AGAC galleries",formulaire:"public submissions",recurrents:"verified weekly events"};
const BASE=document.documentElement.dataset.base||"";
const DISC=EN?[["theatre","Theatre"],["musique","Music"],["danse","Dance"],["cirque","Circus"],["humour","Comedy & cabaret"],["cinema","Film"],["poesie","Poetry, slam & rap battles"],["lettres","Literature"],["conference","Talks"],["jeune","Kids & family"],["atelier","Workshops"],["fete","Parties & celebrations"],["quiz","Quiz nights"],["expo","Openings"],["autre","Other"]]
  :[["theatre","Théâtre"],["musique","Musique"],["danse","Danse"],["cirque","Cirque"],["humour","Humour et cabaret"],["cinema","Cinéma"],["poesie","Poésie, slam et rap battle"],["lettres","Littérature"],["conference","Conférences"],["jeune","Jeune public"],["atelier","Ateliers"],["fete","Fêtes et célébrations"],["quiz","Quiz"],["expo","Vernissages"],["autre","Autre / à préciser"]];
const DISC_LABEL=Object.fromEntries(DISC);
const V2=document.documentElement.classList.contains("v2"); // aperçu du nouveau design (?v2)
// Nouveau design : le bas de page est réorganisé (mise à jour, programmation dans un ovale, don au centre, liens à droite)
if(V2)(()=>{const q=s=>document.querySelector(s),f=q(".v2-pied");if(!f)return;
  const mv=(el,dest)=>{if(el&&dest)dest.appendChild(el)};
  mv(q("#majInfo"),q(".vp-maj"));
  document.querySelectorAll(".note .toplinks a").forEach(a=>mv(a,q(".vp-pill")));
  mv(q("#donBtn"),q(".vp-don"));mv(q("#donPop"),q(".vp-don"));
  [...document.querySelectorAll(".pied-bts .pied-bt")].reverse().forEach(a=>q(".vp-liens").prepend(a));})();
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
const DN=EN?["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]:["dim.","lun.","mar.","mer.","jeu.","ven.","sam."];
const MOIS=EN?["Jan.","Feb.","March","April","May","June","July","Aug.","Sept.","Oct.","Nov.","Dec."]:["janv.","févr.","mars","avr.","mai","juin","juil.","août","sept.","oct.","nov.","déc."];
const MOIS_L=EN?["January","February","March","April","May","June","July","August","September","October","November","December"]:["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];
const JOURS=EN?["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]:["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"];
const d=s=>{const[y,m,dd]=s.split("-").map(Number);return new Date(y,m-1,dd)};
const iso=x=>x.getFullYear()+"-"+String(x.getMonth()+1).padStart(2,"0")+"-"+String(x.getDate()).padStart(2,"0");
const addDays=(s,n)=>{const x=d(s);x.setDate(x.getDate()+n);return iso(x)};
const monday=s=>{const x=d(s);return addDays(s,-((x.getDay()+6)%7))};
const fmt=s=>{const x=d(s);return EN?MOIS[x.getMonth()]+" "+x.getDate():x.getDate()+" "+MOIS[x.getMonth()]};
const fmtLong=s=>{const x=d(s);return EN?JOURS[x.getDay()]+", "+MOIS[x.getMonth()]+" "+x.getDate():JOURS[x.getDay()]+" "+x.getDate()+" "+MOIS[x.getMonth()]};
// Heure : « 19 h 30 » en français, « 7:30 p.m. » en anglais
const hFmt=h=>{if(!EN)return h.replace(":"," h ");const[a,b]=h.split(":").map(Number);return (a%12||12)+(b?":"+String(b).padStart(2,"0"):"")+(a>=12?" p.m.":" a.m.")};
// Résumé dans la langue de la page (traduction faite à la collecte), sinon l'original
// Prix en anglais : « 25,50 $ » → « $25.50 », « Gratuit » → « Free »
const prixDe=p=>!EN||!p?p:p.replace(/^Gratuit$/i,"Free").replace(/^Payant$/i,"Paid").replace(/^Contribution volontaire$/i,"Pay what you can").replace(/^Entrée libre$/i,"Free admission")
  .replace(/(\d+)(?:[,.](\d{1,2}))? à (\d+)(?:[,.](\d{1,2}))? ?\$/g,(m,a,b,c,dd)=>"$"+a+(b?"."+b.padEnd(2,"0"):"")+" to $"+c+(dd?"."+dd.padEnd(2,"0"):""))
  .replace(/(\d+)(?:[,.](\d{1,2}))? ?\$/g,(m,a,b)=>"$"+a+(b?"."+b.padEnd(2,"0"):"")).replace(/taxes incluses/,"taxes included").replace(/à la porte/,"at the door").replace(/ à /g," to ");
const resumeDe=e=>EN&&e.resume_en?e.resume_en:e.resume;
const esc=t=>String(t).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $=id=>document.getElementById(id);
function km(a,b){const R=6371,r=x=>x*Math.PI/180,dl=r(b.lat-a.lat),dn=r(b.lon-a.lon);
  const h=Math.sin(dl/2)**2+Math.cos(r(a.lat))*Math.cos(r(b.lat))*Math.sin(dn/2)**2;return 2*R*Math.asin(Math.sqrt(h))}
const fmtKm=k=>k<1?Math.round(k*10)*100+" m":(Math.round(k*10)/10).toString().replace(".",EN?".":",")+" km";

let D=null,byId=[],CFG={},FEST=[],FESTID={};
const DEPART="theatre"; // catégorie affichée seule à la première visite (les autres se cochent dans « Disciplines »)
let st={on:Object.fromEntries(DISC.map(x=>[x[0],x[0]===DEPART])),view:"week",day:null,week:null,month:null,kids:false,pt:"",rayon:0,sort:"time",custom:null};
st.v=2; // v2 : une seule catégorie au départ ; les choix enregistrés avant v2 sont ignorés
try{const s=JSON.parse(localStorage.getItem("cal-mtl")||"null");if(s&&s.on&&s.v===2)Object.assign(st,s,{on:Object.assign(st.on,s.on)})}catch(e){}
st.pt="";st.rayon=0;st.sort="time";st.custom=null;st.fest=null;st.q="";
st.seul=null;st.cible=null;
st.day=null;st.week=null;st.month=null; // on ouvre toujours sur aujourd'hui (les catégories choisies sont gardées)
st.view="week"; // on ouvre toujours en mode Semaine, sur la semaine en cours // l'outil « Près de » est retiré
const save=()=>{try{localStorage.setItem("cal-mtl",JSON.stringify(st))}catch(e){}};

function origin(){if(st.pt==="addr")return st.custom;const p=POINTS.find(p=>p[0]===st.pt);return p?{lat:p[1],lon:p[2],libelle:p[0]}:null}
function dist(lieu){const o=origin(),c=D.lieux[lieu];if(!o||!c)return null;return km(o,c)}
function inRadius(lieu){if(!st.rayon||!origin())return true;const k=dist(lieu);return k!==null&&k<=st.rayon}
// Un événement peut être dans plusieurs disciplines (champ « aussi », ex. théâtre + danse)
// Un spectacle jeune public apparaît aussi dans sa discipline d'origine (« sous », ex. théâtre)
const discs=e=>[...new Set([e.discipline].concat(e.aussi||[],e.sous&&DISC_LABEL[e.sous]?[e.sous]:[]))];
// Styles de musique (larges). Aucun style choisi = toute la musique.
// Mots qu'on peut taper dans la recherche pour trouver chaque style
const STYLE_MOTS={rock:"rock indie alternatif alternative garage",pop:"pop chanson francophone",hiphop:"hip-hop hiphop rap r&b rnb soul funk",electro:"électro electro électronique electronic techno house dj rave",jazz:"jazz blues swing",classique:"classique classical opéra opera orchestre orchestra baroque chambre chamber",monde:"monde world afro latin reggae",folk:"folk trad country bluegrass",metal:"métal metal punk hardcore",experimental:"expérimental experimental noise improvisation improv"};
const STYLES=EN?{rock:"Rock & indie",pop:"Pop & chanson",hiphop:"Hip-hop & R&B",electro:"Electronic",jazz:"Jazz & blues",classique:"Classical & opera",monde:"World music",folk:"Folk, trad & country",metal:"Metal & punk",experimental:"Experimental"}
  :{rock:"Rock et indie",pop:"Pop et chanson",hiphop:"Hip-hop et R&B",electro:"Électro",jazz:"Jazz et blues",classique:"Classique et opéra",monde:"Musiques du monde",folk:"Folk, trad et country",metal:"Métal et punk",experimental:"Expérimental"};
// Pour les filtres : un spectacle jeune public n'apparaît que si « Jeune public » est coché (pas sous Théâtre, Musique…)
const discsFiltre=e=>e.discipline==="jeune"?["jeune"]:e.discipline==="expo"?["expo"]:discs(e);
// st.seul = "expo" : le calendrier d'accueil, mais avec les vernissages seulement (bouton Vernissages de la page Expositions)
// st.cible : l'événement ouvert depuis la recherche ou un lien partagé reste visible ce jour-là, même si sa catégorie n'est pas cochée
const visible=()=>D.events.filter(e=>(st.cible===e._i&&e.date===st.day)||(st.seul?e.discipline===st.seul:st.fest?e.festival===st.fest:discsFiltre(e).some(k=>st.on[k]))&&inRadius(e.lieu));
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
function descr(e){return (e.heure?"":L("Heure à confirmer. ","Time to be confirmed. "))+(resumeDe(e)?resumeDe(e)+"\n":"")+(e.prix?L("Prix : ","Price: ")+prixDe(e.prix)+"\n":"")+L("Détails : ","Details: ")+(e.billets||e.url)+"\n"+L("(Calendrier culturel montréalais)","(Montreal's cultural calendar)")}
function gcal(e){const s=span(e);
  return "https://calendar.google.com/calendar/render?action=TEMPLATE&text="+encodeURIComponent(e.titre)+"&dates="+s.start+"/"+s.end+
    (s.allDay?"":"&ctz=America/Toronto")+"&location="+encodeURIComponent(e.lieu+", Montréal")+"&details="+encodeURIComponent(descr(e))}
function outlook(e){const s=span(e),f=x=>x.length===8?x.slice(0,4)+"-"+x.slice(4,6)+"-"+x.slice(6):x.slice(0,4)+"-"+x.slice(4,6)+"-"+x.slice(6,8)+"T"+x.slice(9,11)+":"+x.slice(11,13)+":00";
  return "https://outlook.live.com/calendar/0/deeplink/compose?path=/calendar/action/compose&rru=addevent&subject="+encodeURIComponent(e.titre)+
    "&startdt="+f(s.start)+"&enddt="+f(s.end)+(s.allDay?"&allday=true":"")+"&location="+encodeURIComponent(e.lieu+", Montréal")+"&body="+encodeURIComponent(descr(e))}
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
  return (e.complet?`<span class="badge">${L("Complet","Sold out")}</span>`:"")+(e.serie?`<span class="badge s">${L("à l'affiche jusqu'au ","running until ")}${fmt(e.serie.fin)}</span>`:"");
}
function lieuHTML(e,grand){
  const c=D.lieux[e.lieu],k=dist(e.lieu);
  const q=c&&c.quartier?`<span class="q">${esc(c.quartier)}</span>`:"";
  const m=c&&c.metro?`<span class="metro" title="${L("Station la plus proche, à ","Nearest station, ")}${fmtKm(c.metro.km)}${L(""," away")}">${LIGNES_DE(c.metro.nom).map(l=>`<i style="background:${l.c}"></i>`).join("")}${esc(c.metro.nom)}</span>`:"";
  const kmTag=origin()?`<span class="km">${k===null?L("distance ?","distance?"):fmtKm(k)}</span>`:"";
  return `<div class="lieu${grand?" grand":""}"><span class="pin" aria-hidden="true"></span><span class="nom">${esc(e.lieu)}</span>${q}${m}${kmTag}</div>`;
}
function calHTML(e){
  const src=(EN&&SRC_EN[e.source])||(D.sources[e.source]||{}).nom||e.source;
  // iCal : lien vers le fichier .ics publié avec le site → « Ajouter au calendrier » directement (iPhone, Mac, Android…)
  const ical=e.ics?`<a href="${BASE}ics/${e.ics}.ics" title="${L("Ajouter à Apple Calendrier, ou à l'agenda de ton téléphone","Add to Apple Calendar or your phone's calendar")}">iCal</a>`
    :`<button type="button" data-ics="${e._i}" title="${L("Fichier .ics pour Apple Calendrier, Outlook, etc.",".ics file for Apple Calendar, Outlook, etc.")}">iCal</button>`;
  return `<div class="cal"><span class="calk">${L("+ mon agenda :","+ my calendar:")}</span><a href="${esc(gcal(e))}" target="_blank" rel="noopener" title="${L("Ajouter à Google Agenda","Add to Google Calendar")}">Google</a>${ical}<a href="${esc(outlook(e))}" target="_blank" rel="noopener" title="${L("Ajouter à Outlook","Add to Outlook")}">Outlook</a><span class="src">source${L(" : ",": ")}${esc(src)}</span></div>`;
}
const heureTxt=e=>e.heure?hFmt(e.heure):e.serie?L("voir horaire","see schedule"):L("heure à confirmer","time TBC");
const sousTag=e=>e.discipline==="jeune"&&e.sous&&DISC_LABEL[e.sous]?`<span class="sous">${esc(DISC_LABEL[e.sous])}</span>`:"";
function evHTML(e){
  return `<article class="ev" data-d="${e.discipline}" style="--c:var(--${e.discipline})"><a class="main" href="${esc(e.url)}" target="_blank" rel="noopener" title="${esc(DISC_LABEL[e.discipline]||"")}">
    <div class="tm">${heureTxt(e)}</div><div>${lieuHTML(e)}<div class="t">${esc(e.titre)}${flagsHTML(e)}</div>${sousTag(e)}</div></a>
    ${calHTML(e)}</article>`;
}
// Vue Semaine : ligne compacte (un survol) ; le détail est dans la vue Jour
const MAX_SEM=Infinity; // tout afficher dans la semaine
function rowV2(e){ // nouveau design : carte pleine couleur, discipline à gauche, heure à droite, titre, salle
  const f=e.festival&&FESTID[e.festival];
  return `<button type="button" class="row v2row${f?" enfest":""}" data-ev="${e._i}" data-d="${e.discipline}" style="--c:var(--${e.discipline})${f?`;--f:${FESTID[e.festival].coul}`:""}" title="${discs(e).map(k=>esc(DISC_LABEL[k]||"")).join(" · ")}${f?" · "+esc(FESTID[e.festival].court):""}"><span class="r2h"><span class="r2d">${esc((DISC_LABEL[e.discipline]||"").split(/ et |, | \/ /)[0])}</span><b class="${e.heure?"":"nh"}">${e.heure?(EN?hFmt(e.heure):e.heure):"—"}</b></span><span class="rti">${esc(e.titre)}${e.complet?` <span class="cpl">${L("complet","sold out")}</span>`:""}</span><span class="rl">${esc(e.lieu)}</span></button>`}
function rowHTML(e){if(V2)return rowV2(e);const c=D.lieux[e.lieu];
  return `<button type="button" class="row${e.aussi&&e.aussi.length?" multi":""}${e.festival&&FESTID[e.festival]?" enfest":""}" data-ev="${e._i}" style="--c:var(--${e.discipline})${e.aussi&&e.aussi.length?`;--c2:var(--${e.aussi[0]})`:""}${e.festival&&FESTID[e.festival]?`;--f:${FESTID[e.festival].coul}`:""}" title="${discs(e).map(k=>esc(DISC_LABEL[k]||"")).join(" · ")}${e.style&&STYLES[e.style]?" · "+esc(STYLES[e.style]):""}"><span class="rti">${esc(e.titre)}${e.complet?` <span class="cpl">${L("complet","sold out")}</span>`:""}</span><span class="rl"><b class="${e.heure?"":"nh"}">${heureTxt(e)}</b> · <span class="v">${esc(e.lieu)}</span>${c&&c.metro?` · ${esc(c.metro.nom)}`:""}${e.festival&&!st.fest&&FESTID[e.festival]?` <span class="fx" style="--f:${FESTID[e.festival].coul};--ft:${FESTID[e.festival].coulTxt}">${esc(FESTID[e.festival].court)}</span>`:""}</span></button>`}
// Écouter / bande-annonce : seulement des liens vérifiés (page de l'événement, MusicBrainz, TMDb).
// Sinon, un simple lien de recherche, présenté honnêtement comme une recherche.
const NOMS_LIEN={bandcamp:"Bandcamp",spotify:"Spotify",apple:"Apple Music",deezer:"Deezer",tidal:"Tidal",soundcloud:"SoundCloud",youtube:"YouTube",vimeo:"Vimeo",site:L("Site officiel","Official site"),"bande-annonce":L("▶ Bande-annonce","▶ Trailer")};
function ecouteHTML(e){
  const d=discs(e),film=d.includes("cinema"),mus=d.includes("musique");
  if(!film&&!mus)return"";
  if(e.liens&&e.liens.length){
    const parNom={};e.liens.forEach(l=>{const k=l.nom||"";(parNom[k]=parNom[k]||[]).push(l)});
    return `<div class="ecoute"><span>${film?L("Voir :","Watch:"):L("Écouter :","Listen:")}</span>${Object.entries(parNom).map(([nom,ls])=>
      `${nom&&Object.keys(parNom).length>1?`<em>${esc(nom)}</em>`:""}${ls.map(l=>`<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label||NOMS_LIEN[l.type]||l.type)}</a>`).join("")}`).join("")}</div>`}
  if(V2)return""; // nouveau design : sans lien vérifié, rien (les gens chercheront s'ils le veulent)
  const q=encodeURIComponent(film?artiste(e.titre)+L(" bande-annonce"," trailer"):artiste(e.titre)+" "+e.lieu.split(/[–(]/)[0]+" Montréal");
  return `<div class="ecoute rech"><span>${L("Pas encore de lien vérifié :","No verified link yet:")}</span><a href="https://www.youtube.com/results?search_query=${q}" target="_blank" rel="noopener">${L("chercher sur YouTube","search YouTube")}</a></div>`}
// Vue Jour : fiche détaillée
function artiste(t){return t.split(/ – | - |, avec | avec |\(|:| \+ /)[0].trim()}
function detailHTML(e){
  const c=D.lieux[e.lieu];
  const gmaps="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(e.lieu+", Montréal");
  const ecoute=ecouteHTML(e);
  const carte=c&&CFG.cartes!==false?`<iframe class="carte" loading="lazy" title="${L("Carte : ","Map: ")}${esc(e.lieu)}" src="https://www.openstreetmap.org/export/embed.html?bbox=${(c.lon-.006).toFixed(4)}%2C${(c.lat-.0035).toFixed(4)}%2C${(c.lon+.006).toFixed(4)}%2C${(c.lat+.0035).toFixed(4)}&layer=mapnik&marker=${c.lat}%2C${c.lon}"></iframe>`:"";
  // Affiche : image fournie par la salle (formulaire), sinon l'image de promotion de la page officielle,
  // affichée depuis son site d'origine avec le crédit et le lien. Si elle ne charge pas, le cadre disparaît.
  const aff=e.image?{url:e.image,credit:L("fournie par l'organisateur","provided by the organizer")}:(CFG.affiches!==false&&e.affiche)||null;
  const img=aff?`<figure class="det-aff"><a href="${esc(aff.lien||e.url)}" target="_blank" rel="noopener"><img src="${esc(aff.url)}" alt="${L("Affiche : ","Poster: ")}${esc(e.titre)}" loading="lazy" referrerpolicy="no-referrer"${aff.petit?` data-petit="${esc(aff.petit)}"`:""} onerror="if(this.dataset.petit&&this.src!==this.dataset.petit){this.src=this.dataset.petit;return}const v=this.closest('.det-vis');this.closest('figure').remove();if(v&&!v.children.length)v.remove()"></a><figcaption>${aff.salle?L("Image de la salle : ","Venue image: "):L("Image : ","Image: ")}${esc(aff.credit||"")}</figcaption></figure>`:"";
  // L'affiche et la carte à droite, avec prix, billets et itinéraire juste dessous ; écouter et agenda sous le résumé.
  const actions=`<div class="actions">
        <a class="btn" href="${esc(e.billets||e.url)}" target="_blank" rel="noopener">${e.billets?(V2?`<span class="btl-l">${L("Acheter des billets","Buy tickets")}</span><span class="btl-c">${L("Billets","Tickets")}</span>`:L("Acheter des billets","Buy tickets")):/gratuit|free|entrée libre|contribution volontaire/i.test(e.prix||"")?L("Voir l'événement","See the event"):L("Billets et infos","Tickets & info")}</a>
        <a class="btn ghost" href="${gmaps}" target="_blank" rel="noopener">${L("Itinéraire","Directions")}</a>
        <button type="button" class="btn ghost" data-partage="${e._i}">${L("Partager","Share")}</button>
      </div>`;
  const extra=`${V2?"":ecoute}${calHTML(e)}`; // nouveau design : écouter/voir sous l'affiche (ou sous le résumé sans affiche)
  const media=img||carte?`<div class="det-media${img&&carte?" deux":""}">${img}${carte}</div>`:"";
  return `<article class="ev det${st.cible===e._i?" flash cible":""}" id="ev-${e._i}" data-d="${e.discipline}" style="--c:var(--${e.discipline})">
    <div class="det-info">
      <h3 class="t"><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.titre)}</a></h3>
      <div class="det-top"><div class="tm${e.heure?"":" nh"}">${heureTxt(e)}</div><span class="disc">${discs(e).map(k=>esc(DISC_LABEL[k]||"")).join(" · ")}${e.style&&STYLES[e.style]?` · ${esc(STYLES[e.style])}`:""}</span>${sousTag(e)}${e.festival&&FESTID[e.festival]?`<button type="button" class="fx" data-fest="${e.festival}" style="--f:${FESTID[e.festival].coul};--ft:${FESTID[e.festival].coulTxt}">${/^festival/i.test(FESTID[e.festival].court)?"":"Festival · "}${esc(FESTID[e.festival].court)}</button>`:""}${flagsHTML(e)}${V2&&e.prix?`<span class="prix-main prix-tel">${esc(prixDe(e.prix).length>28?prixDe(e.prix).slice(0,26)+"…":prixDe(e.prix))}</span>`:""}</div>
      ${lieuHTML(e,true)}
      ${resumeDe(e)?`<p class="resume">${esc(resumeDe(e))}</p>`:""}${V2&&!media?ecoute:""}
      ${e.prix?`<span class="prix-main">${esc(prixDe(e.prix).length>28?prixDe(e.prix).slice(0,26)+"…":prixDe(e.prix))}</span>`:""}
    </div>
    ${media?`<div class="det-vis">${media}${V2?ecoute:""}</div>`:""}
    <div class="det-side seul">${V2&&e.prix?`<span class="prix-main prix-side">${esc(prixDe(e.prix).length>28?prixDe(e.prix).slice(0,26)+"…":prixDe(e.prix))}</span>`:""}${actions}${extra}</div>
  </article>`;
}
function renderChips(){
  const counts={};D.events.forEach(e=>discsFiltre(e).forEach(k=>counts[k]=(counts[k]||0)+1));

  const t0=iso(new Date()),nExpos=D.expos.filter(x=>x.fin>=t0&&(!x.discipline||x.discipline==="expo")).length;
  // « Expositions » (juste après Vernissages) : ouvre la page des expositions en cours ; un 2e clic revient au calendrier
  const chipExpos=nExpos?`<button type="button" class="chip chip-page" style="--c:var(--expo)" data-page="expos" data-d="expo" aria-pressed="${st.view==="musee"}"><span class="dot"></span>${L("Expositions","Exhibitions")} <span class="n">${nExpos}</span></button>`:"";
  $("chips").innerHTML=DISC.map(([k,l])=>{const n=counts[k]||0;
    return `<button type="button" class="chip" style="--c:var(--${k})" data-k="${k}" data-d="${k}" aria-pressed="${n&&st.on[k]?"true":"false"}" ${n?"":"disabled"}><span class="dot"></span>${l} <span class="n">${n||L("aucun","none")}</span></button>`+(k==="expo"?chipExpos:"")}).join("");
  // Sélection rapide : « tout » / « aucun » (grisé quand c'est déjà le cas)
  const actives=DISC.filter(([k])=>counts[k]);
  $("discTout").disabled=actives.every(([k])=>st.on[k]);$("discRien").disabled=!actives.some(([k])=>st.on[k]);
}
const inRange=s=>s>=D.debut&&s<=D.fin;
function weekDays(){return [0,1,2,3,4,5,6].map(i=>addDays(st.week,i))}
function renderStrip(){
  const v=visible();$("strip").hidden=st.view==="month";
  $("strip").innerHTML=weekDays().map(s=>{const n=inRange(s)?v.filter(e=>e.date===s).length:"—",x=d(s);
    return `<button type="button" class="day${inRange(s)?"":" nodata"}${s===iso(new Date())?" today":""}" data-d="${s}" aria-current="${st.view==="day"&&st.day===s}" ${inRange(s)?"":"disabled"}><span class="dn">${s===iso(new Date())?L("auj.","today"):DN[x.getDay()]}</span><span class="dd">${x.getDate()}</span><span class="dc">${n}</span></button>`}).join("");
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
  p.textContent=L(`Après le ${fmt(D.completJusqua)}, la liste est partielle : surtout des concerts et les spectacles des grandes salles. Elle se complète à mesure que la date approche.`,
    `After ${fmt(D.completJusqua)}, the list is partial: mostly concerts and shows at the big venues. It fills in as the date gets closer.`);
}
/* Expositions en cours : elles n'ont pas de date de représentation, on les montre « ouvertes ce jour-là » */
// Musées : expositions présentées dans un musée ou un grand lieu d'exposition → onglet Musées. Le reste (vernissages,
// petites expos de galeries, expos courtes) reste au calendrier.
const RE_MUSEE=/mus[ée]e|mbam|mccord|pointe-à-callière|centre canadien d'architecture|\bcca\b|\bphi\b|biosphère|biodôme|planétarium|insectarium|jardin botanique|château (ramezay|dufresne)|écomusée|\bmem\b|centre des mémoires|arsenal art contemporain|fonderie darling|galerie de l'uqam|oasis immersion|maison saint-gabriel|centre d'histoire/i;
const estMusee=x=>RE_MUSEE.test(x.lieu||"");
function exposDu(j){if(!inRange(j)||!st.fest)return[];const ok=x=>x.festival===st.fest; // les expos en cours sont dans l'onglet Expos
  return D.expos.filter(x=>ok(x)&&x.debut<=j&&x.fin>=j&&inRadius(x.lieu))}
function expoCarte(j){const n=exposDu(j).length;
  return n?`<button type="button" class="expocard" data-act="jour" data-d="${j}"><b>${n}</b> ${L(`expo${n>1?"s":""} ouverte${n>1?"s":""}`,`exhibition${n>1?"s":""} open`)}<span>${L("voir la liste →","see the list →")}</span></button>`:""}
function exposJourHTML(j){
  const X=exposDu(j).sort(origin()&&st.sort==="dist"?(a,b)=>{const x=dist(a.lieu),y=dist(b.lieu);return (x===null?1e9:x)-(y===null?1e9:y)}:(a,b)=>a.fin.localeCompare(b.fin));
  if(!X.length)return"";const bientot=addDays(j,7);
  return `<h2 class="label xhead">${LL("Expositions ouvertes ce jour-là","Exhibitions open that day")} · ${X.length}</h2><p class="xnote">${LL("Sans heure de représentation : vérifie les heures d'ouverture du lieu.","No showtimes: check the venue's opening hours.")}</p>
    <div class="xjour">${X.map(x=>`<article class="xd"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titre)}</a>${lieuHTML(x)}
      <div class="end${x.fin<=bientot?" soon":""}">${x.fin<=bientot?LL("Se termine le ","Ends "):LL("Jusqu'au ","Until ")}${fmt(x.fin)}</div></article>`).join("")}</div>`}
/* ---------- Festivals ---------- */
const MOIS_N=MOIS_L;
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
  return !d1?L(`jusqu'au ${fmt(d2)}`,`until ${fmt(d2)}`):d1===d2?fmt(d1):`${fmt(d1)} → ${fmt(d2)}`};
function festOuvert(f){return(f.disciplines||[]).some(k=>st.on[k]!==false)}
function festCompte(id){return D.events.filter(e=>e.festival===id).length+D.expos.filter(x=>x.festival===id).length}
function festChips(j){
  if(!inRange(j)||!FEST.length)return"";
  const FL=FEST.filter(f=>{const d1=f.debut||D.debut;return d1&&f.fin&&d1<=j&&j<=f.fin&&festOuvert(f)});
  // Pastille pleine : le festival a des activités datées ce jour-là. Pastille contour : il est en cours,
  // mais rien de daté ce jour-là (ex. une exposition), ou sa programmation n'est pas encore connue.
  const html=FL.map(f=>{const n=D.events.filter(e=>e.festival===f.id&&e.date===j).length,x=D.expos.some(e=>e.festival===f.id&&e.debut<=j&&e.fin>=j);
    const info=n?L(`${n} activité${n>1?"s":""} ce jour-là`,`${n} event${n>1?"s":""} that day`):x?L("exposition en cours, rien d'autre de daté ce jour-là","exhibition on, nothing else scheduled that day"):L("en cours ; programmation de ce jour pas encore connue","on now; this day's program not yet known");
    return `<button type="button" class="fchip${n?"":" vide"}" data-fest="${f.id}" style="--f:${f.coul};--ft:${f.coulTxt}" title="${esc(f.nom)} : ${info}">${esc(f.court)}${n?` <b>${n}</b>`:x?" · expo":""}</button>`}).join("");
  return FL.length?`<div class="fchips">${html}</div>`:""}
function ouvrirFestival(id){
  const f=FESTID[id];if(!f)return;
  st.fest=id;st.view="week";const today=iso(new Date());
  const debut=(f.debut&&f.debut>today)?f.debut:today;st.day=inRange(debut)?debut:st.day;st.week=monday(st.day);
  render();window.scrollTo({top:$("navBar").getBoundingClientRect().top+window.scrollY-20,behavior:"smooth"});
}
function renderFestBanner(){
  const b=$("festBanner"),f=st.fest&&FESTID[st.fest];b.hidden=!f;if(!f)return;
  b.style.setProperty("--c",f.coul||`var(--${f.disciplines[0]})`);
  b.innerHTML=`<div><b>${esc(f.nom)}</b><span>${fDates(f)} · ${festCompte(f.id)} ${L(`activité${festCompte(f.id)>1?"s":""} au calendrier`,`event${festCompte(f.id)>1?"s":""} on the calendar`)}</span></div>
    <div class="fbact">${f.site?`<a href="${esc(f.site)}" target="_blank" rel="noopener">${L("Site officiel ↗","Official site ↗")}</a>`:""}<button type="button" class="btn" data-act="festoff">${L("✕ Tout le calendrier","✕ Full calendar")}</button></div>`;
}
function festCarte(f){
  const e=festEtat(f),n=festCompte(f.id),c=f.disciplines[0];
  const badge=e.etat==="cours"?`<span class="fbadge on">${L("En cours","On now")}${e.reste?L(` · encore ${e.reste} jour${e.reste>1?"s":""}`,` · ${e.reste} more day${e.reste>1?"s":""}`):L(" · dernier jour"," · last day")}</span>`
    :e.etat==="bientot"?`<span class="fbadge">${L(`Dans ${e.dans} jour${e.dans>1?"s":""}`,`In ${e.dans} day${e.dans>1?"s":""}`)}</span>`:"";
  const quand=e.etat==="plus"?(e.mois===null?L("Dates à venir","Dates to come"):L(`Prochaine édition : vers ${MOIS_N[e.mois]} ${e.an} <i>(dates à confirmer)</i>`,`Next edition: around ${MOIS_N[e.mois]} ${e.an} <i>(dates TBC)</i>`))
    :`${fDates(f)}${f.verifier?L(" <i>(à confirmer)</i>"," <i>(TBC)</i>"):""}`;
  return `<article class="fest" style="--c:${f.coul||`var(--${c})`}">
    <div class="fh"><h3>${esc(f.nom)}</h3>${badge}</div>
    <p class="fd">${quand}${f.lieu?` · ${esc(f.lieu)}`:""}</p>
    <div class="ftags">${f.disciplines.map(k=>`<span style="--c:var(--${k})">${esc(DISC_LABEL[k]||k)}</span>`).join("")}</div>
    <div class="fa">${n?`<button type="button" class="btn" data-fest="${f.id}">${L("Programmation au calendrier","Program on the calendar")} · ${n}</button>`
      :`<span class="fwait">${e.etat==="plus"?L("Programmation ajoutée quand elle sera en ligne","Program added once it's online"):L("Programmation : ajoutée dès qu'elle est en ligne","Program: added as soon as it's online")}</span>`}
      ${f.site?`<a href="${esc(f.site)}" target="_blank" rel="noopener">${L("Site officiel ↗","Official site ↗")}</a>`:""}</div></article>`}
function renderFestivals(){
  const el=$("view");if(!FEST.length){el.innerHTML=`<div class="empty">${L("La liste des festivals n'a pas pu être chargée.","The festival list could not be loaded.")}</div>`;return}
  const FL=FEST.filter(festOuvert).map(f=>({f,e:festEtat(f)}));
  const cours=FL.filter(x=>x.e.etat==="cours").sort((a,b)=>a.f.fin.localeCompare(b.f.fin));
  const bientot=FL.filter(x=>x.e.etat==="bientot").sort((a,b)=>(a.f.debut||a.f.fin).localeCompare(b.f.debut||b.f.fin));
  const prochains=bientot.filter(x=>x.e.dans<=90),loin=bientot.filter(x=>x.e.dans>90);
  const plus=FL.filter(x=>x.e.etat==="plus").map(x=>({...x,k:x.e.mois===null?99:(x.e.an*12+x.e.mois)})).sort((a,b)=>a.k-b.k);
  const parMois={};loin.forEach(x=>{const k=(x.f.debut||x.f.fin).slice(0,7);(parMois[k]=parMois[k]||[]).push(x)});
  plus.forEach(x=>{const k=x.e.mois===null?"zz":`${x.e.an}-${String(x.e.mois+1).padStart(2,"0")}`;(parMois[k]=parMois[k]||[]).push(x)});
  const moisLbl=k=>k==="zz"?L("Dates à venir","Dates to come"):`${MOIS_N[Number(k.slice(5))-1]} ${k.slice(0,4)}`;
  const grille=xs=>`<div class="festgrid">${xs.map(x=>festCarte(x.f)).join("")}</div>`;
  el.innerHTML=`<div class="festview">
    <h2 class="label">${L("En cours","On now")} · ${cours.length}</h2>${cours.length?grille(cours):`<p class="empty">${L("Aucun festival en cours pour ces disciplines.","No festival on now for these disciplines.")}</p>`}
    <h2 class="label">${L("Dans les 3 prochains mois","In the next 3 months")} · ${prochains.length}</h2>${prochains.length?grille(prochains):`<p class="empty">${L("Rien d'annoncé pour l'instant.","Nothing announced yet.")}</p>`}
    <h2 class="label">${L("Plus tard dans l'année","Later in the year")}</h2>
    ${Object.keys(parMois).sort().map(k=>`<h3 class="fmois">${moisLbl(k)}</h3>${grille(parMois[k])}`).join("")}
  </div>`;
}
/* ---------- Recherche ---------- */
const plat=t=>(t||"").toLowerCase().replace(/ø/g,"o").replace(/æ/g,"ae").replace(/œ/g,"oe").replace(/ß/g,"ss").replace(/ł/g,"l").normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/[^a-z0-9]+/g," ").trim();
function correspond(mots,...champs){const t=" "+plat(champs.join(" "))+" ";return mots.every(m=>t.includes(" "+m)||t.includes(m))}
function renderRecherche(){
  const mots=plat(st.q).split(" ").filter(Boolean),el=$("view");
  const today=iso(new Date());
  const champsE=e=>[e.titre,e.lieu,(D.lieux[e.lieu]||{}).quartier||"",e.resume||"",e.resume_en||"",e.festival&&FESTID[e.festival]?FESTID[e.festival].nom+" "+FESTID[e.festival].court:"",discs(e).map(k=>DISC_LABEL[k]).join(" "),e.style&&STYLES[e.style]?STYLES[e.style]+" "+STYLE_MOTS[e.style]:""];
  const ev=D.events.filter(e=>e.date>=today&&correspond(mots,...champsE(e)));
  const ex=D.expos.filter(x=>x.fin>=today&&correspond(mots,x.titre,x.lieu,x.festival&&FESTID[x.festival]?FESTID[x.festival].nom:""));
  const fe=FEST.filter(f=>correspond(mots,f.nom,f.court,f.lieu||""));
  // Une pièce jouée plusieurs soirs : on la montre une fois par jour, mais on regroupe par date
  const par={};ev.slice(0,400).forEach(e=>(par[e.date]=par[e.date]||[]).push(e));
  const n=ev.length+ex.length+fe.length;
  el.innerHTML=`<div class="resultats">
    <h2 class="label">${L(`« ${esc(st.q)} »`,`“${esc(st.q)}”`)} · ${n} ${L(`résultat${n>1?"s":""}`,`result${n===1?"":"s"}`)}</h2>
    ${n?"":`<p class="empty">${L("Rien trouvé. Essaie un autre mot (nom du groupe, de la pièce, de la salle…). La recherche ignore les accents et les filtres de discipline.","Nothing found. Try another word (band, play or venue name…). Search ignores accents and discipline filters.")}</p>`}
    ${fe.length?`<h3 class="fmois">Festivals</h3><div class="festgrid">${fe.map(festCarte).join("")}</div>`:""}
    ${Object.keys(par).sort().map(j=>`<h3 class="fmois">${fmtLong(j)}</h3><div class="rows">${par[j].sort(byTime).map(rowHTML).join("")}</div>`).join("")}
    ${ev.length>400?`<p class="empty">${L(`… et ${ev.length-400} autres. Précise ta recherche.`,`… and ${ev.length-400} more. Narrow your search.`)}</p>`:""}
    ${ex.length?`<h3 class="fmois">${L("Expositions","Exhibitions")}</h3><div class="xjour">${ex.map(x=>`<article class="xd"><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titre)}</a>${lieuHTML(x)}<div class="end">${L("Jusqu'au ","Until ")}${fmt(x.fin)}</div></article>`).join("")}</div>`:""}
  </div>`;
}
/* ---------- Festivals de la semaine (une seule rangée, à côté de la date) ---------- */
function renderFestSemaine(){
  const el=$("festSemaine");
  if(st.view!=="week"||st.fest||!FEST.length){el.innerHTML="";return}
  const a=st.week,b=addDays(st.week,6);
  const FL=FEST.filter(f=>{const d1=f.debut||D.debut;return f.fin&&d1<=b&&f.fin>=a&&festOuvert(f)});
  el.innerHTML=FL.length?`<span class="fslbl">${L("En festival :","Festivals on:")}</span>${FL.map(f=>{const n=D.events.filter(e=>e.festival===f.id&&e.date>=a&&e.date<=b).length;
    return `<button type="button" class="fchip${n?"":" vide"}" data-fest="${f.id}" style="--f:${f.coul};--ft:${f.coulTxt}" title="${esc(f.nom)} · ${fDates(f)}">${esc(f.court)}${n?` <b>${n}</b>`:""}</button>`}).join("")}`:"";
}
/* ---------- Musées ---------- */
// Onglet Expos : toutes les expositions en cours (musées, galeries, centres d'artistes), hors du calendrier.
const RE_GALERIE=/galerie|gallery|art contemporain|contemporain\b|\bart m[uû]r|blouin|bradley|pfoac|duran|chiguer|robertson|nicolas robert|hugues charbonneau|lacerte|poulin|mikhail|tian|wishbone|laroche|ellephant|c\.o\.a/i;
const typeExpo=x=>estMusee(x)?"musee":(x.source==="galeries"||RE_GALERIE.test(x.lieu||""))?"galerie":"centre";
const TYPES_EXPO=EN?[["","All"],["musee","Museums"],["galerie","Galleries"],["centre","Artist-run centres & other venues"]]:[["","Tout"],["musee","Musées"],["galerie","Galeries"],["centre","Centres d'artistes et autres lieux"]];
function renderMusees(){
  const today=iso(new Date()),bientot=addDays(today,14),recent=addDays(today,-14);
  const tous=D.expos.filter(x=>x.fin>=today&&(!x.discipline||x.discipline==="expo"));
  const quart=x=>(D.lieux[x.lieu]||{}).quartier||L("Autres secteurs","Other areas");
  const parType=tous.filter(x=>!st.xtype||typeExpo(x)===st.xtype);
  const nq={};parType.forEach(x=>{const q=quart(x);nq[q]=(nq[q]||0)+1});
  if(st.xq&&!nq[st.xq])st.xq="";
  const XL=parType.filter(x=>!st.xq||quart(x)===st.xq);
  const carte=(x,avecLieu)=>`<article class="xd mus${x.fin<=bientot?" fin":""}">${avecLieu?`<span class="mlieu">${esc(x.lieu)}</span>`:""}<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.titre)}</a>
    <div class="end${x.fin<=bientot?" soon":""}">${x.debut>today?L(`Ouvre le ${fmt(x.debut)} · `,`Opens ${fmt(x.debut)} · `):""}${x.fin<=bientot?L("Se termine le ","Ends "):L("Jusqu'au ","Until ")}${fmt(x.fin)}${x.fin.slice(0,4)!==today.slice(0,4)?" "+x.fin.slice(0,4):""}</div>
    ${x.festival&&FESTID[x.festival]?`<button type="button" class="fx" data-fest="${x.festival}" style="--f:${FESTID[x.festival].coul};--ft:${FESTID[x.festival].coulTxt}">${esc(FESTID[x.festival].court)}</button>`:""}</article>`;
  const fin=XL.filter(x=>x.fin<=bientot).sort((a,b)=>a.fin.localeCompare(b.fin));
  const neuf=XL.filter(x=>x.debut>=recent&&x.fin>bientot).sort((a,b)=>b.debut.localeCompare(a.debut));
  const par={};XL.forEach(x=>(par[x.lieu]=par[x.lieu]||[]).push(x));
  const nt={};tous.forEach(x=>{const t=typeExpo(x);nt[t]=(nt[t]||0)+1});
  $("view").innerHTML=`<div class="festview expoview">
    <div class="xfiltres" role="group" aria-label="${L("Type de lieu","Venue type")}">${TYPES_EXPO.map(([k,l])=>`<button type="button" class="xf" data-xtype="${k}" aria-pressed="${(st.xtype||"")===k}">${l} <span class="n">${k?nt[k]||0:tous.length}</span></button>`).join("")}</div>
    <div class="xquart" role="group" aria-label="${L("Quartier","Neighbourhood")}"><span class="xq-l">${L("Quartier :","Neighbourhood:")}</span><button type="button" class="xq" data-xq="" aria-pressed="${!st.xq}">${L("tous","all")}</button>${Object.keys(nq).sort((a,b)=>nq[b]-nq[a]||a.localeCompare(b,"fr")).map(q=>`<button type="button" class="xq" data-xq="${esc(q)}" aria-pressed="${st.xq===q}">${esc(q)} <span class="n">${nq[q]}</span></button>`).join("")}</div>
    ${`
    ${fin.length?`<h2 class="label">${L("Dernière chance · se termine dans moins de 2 semaines","Last chance · closing within 2 weeks")}</h2><div class="xjour">${fin.map(x=>carte(x,true)).join("")}</div>`:""}
    ${neuf.length?`<h2 class="label">${L("Vient d'ouvrir","Just opened")}</h2><div class="xjour">${neuf.map(x=>carte(x,true)).join("")}</div>`:""}
    <h2 class="label">${L("Par lieu","By venue")} · ${Object.keys(par).length} ${L("lieux","venues")} · ${XL.length} ${L("expositions","exhibitions")}</h2>
    ${Object.keys(par).sort((a,b)=>a.localeCompare(b,"fr")).map(l=>`<section class="musee"><h3 class="fmois">${esc(l)}</h3>${lieuHTML({lieu:l})}<div class="xjour">${par[l].sort((a,b)=>a.fin.localeCompare(b.fin)).map(x=>carte(x,false)).join("")}</div></section>`).join("")||`<div class="empty">${L("Aucune exposition pour ce choix.","No exhibitions for this choice.")}</div>`}`}
  </div>`;
}
function bandeauSeul(){return st.seul==="expo"?`<div class="bandseul"><b>${L("Vernissages seulement","Openings only")}</b><button type="button" class="btn ghost" data-act="expos">${L("← Retour aux expositions","← Back to exhibitions")}</button><button type="button" class="btn ghost" data-act="tout-cal">${L("Tout le calendrier","Full calendar")}</button></div>`:""}
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
        cells.push(own?`<button type="button" class="cell${ok?"":" out"}${s===today?" today":""}" data-d="${s}" ${ok?"":"disabled"} aria-label="${esc(fmtLong(s))}: ${list.length} ${L("activités","events")}">
          <span class="num">${x.getDate()}</span>${ok?`<span class="cnt">${list.length} ${L(`activité${list.length>1?"s":""}`,`event${list.length===1?"":"s"}`)}${nx?` <em>+ ${nx} expo${nx>1?"s":""}</em>`:""}</span><span class="dots">${disc.map(k=>`<i style="background:var(--${k})" title="${esc(DISC_LABEL[k])}"></i>`).join("")}</span>
          <span class="peek">${list.sort(byTime).slice(0,3).map(e=>esc(e.titre)).join(" · ")}</span>`:""}</button>`:`<div></div>`);
        s=addDays(s,1)}
      if(d(s).getMonth()!==m-1)break}
    el.innerHTML=`<div class="month">${(EN?["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:["lun.","mar.","mer.","jeu.","ven.","sam.","dim."]).map(x=>`<div class="mhead">${x}</div>`).join("")}${cells.join("")}</div>`;
  }else if(st.view==="week"){
    el.innerHTML=`${bandeauSeul()}<div class="board">${weekDays().map(s=>{
      const list=inRange(s)?v.filter(e=>e.date===s).sort(useDist?byDist:byTime):[];
      const xc=expoCarte(s);
      const plus=list.length-MAX_SEM;
      const auj=s===iso(new Date());
      return `<section class="col${list.length||xc?"":" emptycol"}${auj?" today":""}${s<iso(new Date())?" passe":""}${s===st.day&&!auj?" sel":""}" data-d="${s}"><button type="button" class="colhead" data-act="jour" data-d="${s}" ${inRange(s)?"":"disabled"}>${V2?`<span class="ch-j">${DN[d(s).getDay()]}${auj?L(" · auj."," · today"):""}</span><span class="ch-n">${d(s).getDate()}</span><span class="ch-c">${list.length} ${L(`sortie${list.length>1?"s":""}`,`event${list.length===1?"":"s"}`)}</span>`:`${auj?`<i class="aujtag">${L("aujourd'hui","today")}</i>`:""}${fmtLong(s)} <span>${list.length}</span>`}</button>
        ${list.length?`<div class="rows">${list.slice(0,MAX_SEM).map(rowHTML).join("")}</div>`:""}${plus>0?`<button type="button" class="more" data-act="jour" data-d="${s}">+ ${plus} ${L(`autre${plus>1?"s":""} · voir la journée →`,`more · see the day →`)}</button>`:""}${xc}${list.length||xc?"":`<div class="empty">${inRange(s)?L("Rien pour ces critères.","Nothing for these filters."):L("Hors de la période couverte.","Outside the period covered.")}</div>`}</section>`}).join("")}</div>`;
  }else{
    const list=v.filter(e=>e.date===st.day).sort(useDist?byDist:byTime);
    el.innerHTML=`${bandeauSeul()}${st.fest||st.seul?"":festChips(st.day)}<div class="dayhead"><button type="button" class="btn ghost" data-act="semaine">${L("← Toute la semaine","← Whole week")}</button><h2 class="label">${st.day===iso(new Date())?`<i class="aujtag">${L("aujourd'hui","today")}</i> `:""}${fmtLong(st.day)} · ${list.length} ${L(`activité${list.length>1?"s":""}`,`event${list.length===1?"":"s"}`)}</h2></div>
      <div class="dayview">${list.map(detailHTML).join("")||(exposDu(st.day).length?`<div class="empty">${L("Aucun spectacle daté pour ces critères ce jour-là.","No scheduled shows for these filters that day.")}</div>`:`<div class="empty">${L("Rien pour ces critères ce jour-là.","Nothing for these filters that day.")}</div>`)}</div>${exposJourHTML(st.day)}`;
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
  $("stat").innerHTML=`<b>${n}</b>${L(`activité${n>1?"s":""} dans cette période · ${D.events.length} au total`,`event${n===1?"":"s"} in this period · ${D.events.length} in all`)}<br>`+
    Object.entries(by).map(([k,c])=>`${esc((EN&&SRC_EN[k])||(D.sources[k]||{}).nom||k)} ${c}`).join(" · ");
}
function renderNear(){
  const o=origin();$("addrBox").hidden=st.pt!=="addr";
  if(st.pt==="addr"&&o)$("nearMsg").textContent=L(`Point trouvé : ${o.libelle} (position approximative).`,`Found: ${o.libelle} (approximate position).`);
  else if(o)$("nearMsg").textContent=L("Distances à vol d'oiseau. Positions des salles approximatives (± quelques centaines de mètres).","Straight-line distances. Venue positions are approximate (± a few hundred metres).");
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
  const auj=iso(new Date()),ecart=Math.round((new Date(auj+"T12:00")-new Date(D.miseAJour+"T12:00"))/864e5);
  const quand=ecart<=0?L("ce matin","this morning"):ecart===1?L("hier","yesterday"):L(`${JOURS[new Date(D.miseAJour+"T12:00").getDay()].toLowerCase()} dernier`,`last ${JOURS[new Date(D.miseAJour+"T12:00").getDay()]}`);
  const n=D.events.filter(e=>e.date>=auj).length;
  $("majInfo").textContent=L(`Mise à jour ${quand} ✓  ·  ${n.toLocaleString("fr-CA")} sorties au menu d'ici le ${fmtLong(D.fin).toLowerCase().replace(/^\S+ /,"")}`,
    `Updated ${quand} ✓  ·  ${n.toLocaleString("en-CA")} things to do until ${fmt(D.fin)}`);
}

$("pt").innerHTML=`<option value="">${L("— n'importe où —","— anywhere —")}</option>`+POINTS.map(p=>`<option value="${esc(p[0])}">${L("Métro ","Metro ")}${esc(p[0])}</option>`).join("")+`<option value="addr">${L("Une adresse…","An address…")}</option>`;

$("chips").addEventListener("click",e=>{const b=e.target.closest(".chip");if(!b||b.disabled)return;
  if(b.dataset.page==="expos"){if(st.view==="musee")st.view="week";else{sortirRecherche();st.view="musee";st.fest=null}render();return}
  st.on[b.dataset.k]=!st.on[b.dataset.k];if(st.view==="musee")st.view="week";render()});
$("strip").addEventListener("click",e=>{const b=e.target.closest(".day");if(!b||b.disabled)return;
  // En mode Semaine, on reste en Semaine : la journée choisie est mise en évidence et on s'y rend
  if(st.view==="week"){st.day=b.dataset.d;render();const c=document.querySelector(`.col[data-d="${st.day}"]`);
    if(c)c.scrollIntoView({block:"start",behavior:"smooth"});return}
  if(st.view==="day"&&st.day===b.dataset.d){st.week=monday(st.day);st.view="week"}else{st.day=b.dataset.d;st.view="day"}render()});
$("view").addEventListener("click",e=>{
  const c=e.target.closest(".cell");if(c&&!c.disabled){st.day=c.dataset.d;st.week=monday(st.day);st.view="day";render();return}
  const r=e.target.closest(".row[data-ev]");if(r){const ev=byId[r.dataset.ev];if(ev){sortirRecherche();st.day=ev.date;st.view="day";st.cible=ev._i;render();
    const a=$("ev-"+ev._i);if(a){a.classList.add("flash");a.scrollIntoView({block:"start",behavior:"smooth"})}}return}
  const xt=e.target.closest("[data-xtype]");if(xt){st.xtype=xt.dataset.xtype;render();return}
  const xw=e.target.closest("[data-xw]");if(xw){st.xweek=addDays(st.xweek,Number(xw.dataset.xw));render();return}
  const xq=e.target.closest("[data-xq]");if(xq){st.xq=xq.dataset.xq;render();return}
  const fb=e.target.closest("[data-fest]");if(fb){sortirRecherche();ouvrirFestival(fb.dataset.fest);return}
  const xj=e.target.closest('[data-act="jour"]');if(xj){st.day=xj.dataset.d;st.view="day";render();window.scrollTo({top:$("navLabel").getBoundingClientRect().top+window.scrollY-20});return}
  if(e.target.closest('[data-act="tout-cal"]')){st.seul=null;render();return}
  if(e.target.closest('[data-act="expos"]')){st.view="musee";st.seul=null;render();window.scrollTo({top:$("view").getBoundingClientRect().top+window.scrollY-80});return}
  if(e.target.closest('[data-act="semaine"]')){st.week=monday(st.day);st.view="week";render();window.scrollTo({top:$("navLabel").getBoundingClientRect().top+window.scrollY-20});return}
  const b=e.target.closest("[data-ics]");if(b)saveIcs(Number(b.dataset.ics));
  const pb=e.target.closest("[data-partage]");if(pb)partager(byId[pb.dataset.partage],pb);
});
function partager(ev,bt){if(!ev)return;
  const url=ev.ics?`https://ccmtl.ca/${L("","en/")}e/${ev.ics}.html`:`https://ccmtl.ca/${L("","en/")}?d=${ev.date}`;
  const d={title:ev.titre,text:`${ev.titre} · ${fmtLong(ev.date)}${ev.heure?" · "+hFmt(ev.heure):""} · ${ev.lieu}`,url};
  if(navigator.share){navigator.share(d).catch(()=>{});return}
  const fini=()=>{bt.textContent=L("Lien copié ✓","Link copied ✓");setTimeout(()=>{bt.textContent=L("Partager","Share")},2500)};
  try{navigator.clipboard.writeText(url).then(fini,()=>prompt(L("Copie ce lien :","Copy this link:"),url))}catch(x){prompt(L("Copie ce lien :","Copy this link:"),url)}
}
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
$("discTout").addEventListener("click",()=>{DISC.forEach(([k])=>st.on[k]=true);st.seul=null;if(st.view==="musee")st.view="week";render()});
$("discRien").addEventListener("click",()=>{DISC.forEach(([k])=>st.on[k]=false);st.seul=null;if(st.view==="musee")st.view="week";render()});
$("allOn").addEventListener("click",()=>{DISC.forEach(([k])=>st.on[k]=true);st.rayon=0;render()});
$("pt").addEventListener("change",e=>{st.pt=e.target.value;st.sort=st.pt?"dist":"time";render();if(st.pt==="addr"&&!st.custom)$("addr").focus()});
$("rayon").addEventListener("change",e=>{st.rayon=Number(e.target.value);render()});
// Carte du métro : décorative (une évocation), sans filtre

let dernierGeo=0;
async function findAddr(){
  const q=$("addr").value.trim();if(!q)return;
  const msg=$("nearMsg");msg.className="msg";
  if(Date.now()-dernierGeo<1500){msg.textContent=L("Un instant…","One moment…");return}
  dernierGeo=Date.now();msg.textContent=L("Recherche de l'adresse…","Looking up the address…");$("addrGo").disabled=true;
  try{
    const u=`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=ca&bounded=1&viewbox=-73.98,45.71,-73.47,45.40&accept-language=${L("fr","en")}&q=`+encodeURIComponent(/montr/i.test(q)?q:q+", Montréal");
    const r=await fetch(u,{headers:{"Accept":"application/json"}});if(!r.ok)throw new Error(r.status);
    const j=await r.json();
    if(j&&j[0]){const lat=+j[0].lat,lon=+j[0].lon;st.custom={lat,lon,libelle:j[0].display_name.split(",").slice(0,3).join(",")};st.sort="dist";render()}
    else{msg.className="msg err";msg.textContent=L("Adresse non trouvée sur l'île de Montréal. Essaie avec le numéro et la rue.","Address not found on the island of Montréal. Try with the street number and name.")}
  }catch(err){msg.className="msg err";msg.textContent=L("La recherche d'adresse ne répond pas. Choisis plutôt une station de métro.","Address search isn't responding. Pick a metro station instead.")}
  finally{$("addrGo").disabled=false}
}
$("addrGo").addEventListener("click",findAddr);
$("addr").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();findAddr()}});

fetch(BASE+"config.json",{cache:"no-store"}).then(r=>r.ok?r.json():{}).then(c=>{
  CFG=c||{};const form=EN&&c.formulaireEvenementEn?c.formulaireEvenementEn:c.formulaireEvenement;if(c&&form){const a=$("lienProposer");a.href=form;a.hidden=false}
  if(c&&(c.donInterac||c.don)){const bt=$("donBtn");const dt=EN?c.donTexteEn||"Donate $2 ♥":c.donTexte;if(dt)bt.textContent=dt;bt.hidden=false;
    bt.addEventListener("click",()=>{if(!c.donInterac&&c.don){window.open(c.don,"_blank","noopener");return}
      const p=$("donPop");p.hidden=!p.hidden;bt.setAttribute("aria-expanded",String(!p.hidden))});
    if(c.donInterac){$("donCourriel").textContent=c.donInterac;
      $("donCopier").addEventListener("click",()=>{const ok=()=>{$("donCopier").textContent=L("Copiée ✓","Copied ✓")};
        try{navigator.clipboard.writeText(c.donInterac).then(ok,()=>{})}catch(e){}})}}
  if(D)render();
}).catch(()=>{});
fetch(BASE+"festivals.json",{cache:"no-store"}).then(r=>r.ok?r.json():[]).catch(()=>[]).then(L=>{
  FEST=Array.isArray(L)?L:[];FEST.forEach(f=>{FESTID[f.id]=f;f.court=f.court||f.nom;f.disciplines=(f.disciplines||[]).filter(k=>DISC_LABEL[k]);if(!f.disciplines.length)f.disciplines=["autre"]});
  // Une couleur propre à chaque festival (dans l'ordre des dates : deux festivals simultanés n'ont pas la même)
  const PAL=[["#7048e8","#fff"],["#0ca678","#fff"],["#f76707","#fff"],["#e64980","#fff"],["#1971c2","#fff"],["#fab005","#121212"],
    ["#862e9c","#fff"],["#2b8a3e","#fff"],["#c92a2a","#fff"],["#15aabf","#121212"],["#8d6e63","#fff"],["#343a40","#fff"]];
  FEST.slice().sort((a,b)=>(a.debut||a.fin||"9").localeCompare(b.debut||b.fin||"9")).forEach((f,i)=>{const p=f.couleur?[f.couleur,"#fff"]:PAL[i%PAL.length];f.coul=p[0];f.coulTxt=p[1]});
  if(D)render()});
fetch(BASE+"data.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(j=>{
  D=j;
  if(EN)[...D.events,...D.expos].forEach(e=>{if(e.lieu==="Lieu à confirmer")e.lieu="Venue TBA"});
  // Pièces, danse et cirque « à l'affiche du X au Y » : une entrée par jour, pour qu'elles suivent les filtres
  const mot=t=>(t||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").split(/[^a-z0-9]+/).find(w=>w.length>2)||"";
  const deja=new Set(D.events.map(e=>e.date+"|"+e.lieu+"|"+mot(e.titre)));
  const cle=t=>(t||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g," ").trim().slice(0,25);
  const titres=new Set(D.events.map(e=>cle(e.titre))),pages=new Set();
  const series=[];D.expos=D.expos.filter(x=>{
    if(!x.discipline||x.discipline==="expo"||!DISC_LABEL[x.discipline])return true;
    // Dates précises déjà connues, période d'un festival, ou même page déjà vue : pas de répétition quotidienne
    if(x.festival||titres.has(cle(x.titre))||(x.url&&pages.has(x.url)))return false;
    if(x.url)pages.add(x.url);
    // Horaire lu sur la page du spectacle (x.horaire) : bonne heure chaque jour, et pas d'entrée les jours de relâche
    let H=x.horaire;const hj=H&&H.jours||{},hd=H&&H.dates||{},avecJours=Object.keys(hj).length>0,avecDates=Object.keys(hd).length>0;
    if(H&&!avecJours&&!Object.keys(hd).some(k=>k>=D.debut))H=null; // liste de dates périmée : on l'ignore
    // Après la dernière date listée (page qui ne montre que les premières représentations) : « voir horaire »
    const derniere=Object.keys(hd).sort().pop()||"";
    const heuresDu=s=>{if(!H)return[null];if(hd[s])return hd[s];if(avecDates&&!avecJours)return s>derniere?[null]:[];
      const h=hj[String((new Date(s+"T12:00").getDay()+6)%7)];return h?[h]:(avecJours?[]:[null])};
    for(let s=x.debut<D.debut?D.debut:x.debut;s<=x.fin&&s<=D.fin;s=addDays(s,1))
      if(!deja.has(s+"|"+x.lieu+"|"+mot(x.titre)))for(const hh of heuresDu(s))series.push({date:s,heure:hh,discipline:x.discipline,titre:x.titre,lieu:x.lieu,url:x.url,complet:false,jeunePublic:x.discipline==="jeune",sous:x.sous,aussi:x.aussi,festival:x.festival,resume:x.resume,resume_en:x.resume_en,prix:x.prix,billets:x.billets,source:x.source||"salles",serie:{debut:x.debut,fin:x.fin}});
    return false});
  D.events=D.events.concat(series).sort((a,b)=>(a.date+(a.heure||"99")).localeCompare(b.date+(b.heure||"99")));
  D.events.forEach((e,i)=>{if(e.jeunePublic&&e.discipline!=="jeune"){e.sous=e.discipline;e.discipline="jeune"}e._i=i;byId[i]=e});
  for(const n in D.lieux){const c=D.lieux[n];if(!c)continue;let best=null;
    for(const s in STN){const k=km(c,{lat:STN[s][0],lon:STN[s][1]});if(!best||k<best.km)best={nom:s,km:k}}
    if(best&&best.km<=1.3)c.metro=best}
  if(!D.debut&&D.semaine){D.debut=D.semaine[0];D.fin=D.semaine[D.semaine.length-1]}
  if(!D.completJusqua)D.completJusqua=D.fin;
  renderFooter();
  const P=new URLSearchParams(location.search),pe=P.get("e"),pd=P.get("d");let cible=null;
  if(pe)cible=D.events.find(x=>x.ics===pe)||null;
  if(cible){st.day=cible.date;st.view="day"}
  else if(pd&&/^\d{4}-\d{2}-\d{2}$/.test(pd)&&inRange(pd)){st.day=pd;st.view="day"}
  render();
  // (les autres fichiers peuvent redessiner la page : la fiche garde sa surbrillance quelques secondes)
  if(cible){st.cible=cible._i;render();setTimeout(()=>{const a=$("ev-"+cible._i);if(a)a.scrollIntoView({block:"start",behavior:"smooth"})},700)}
}).catch(()=>{$("view").innerHTML=`<div class="empty">${L("Les événements n'ont pas pu être chargés. Rechargez la page.","Events could not be loaded. Please reload the page.")}</div>`});
})();

// Le lien de langue garde l'événement ou le jour affiché (?e=…, ?d=…)
(()=>{const l=document.getElementById("langue");if(l)l.addEventListener("click",()=>{l.href=l.getAttribute("href").split("?")[0]+location.search;});})();
