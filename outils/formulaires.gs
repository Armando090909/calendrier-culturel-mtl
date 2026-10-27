/**
 * Crée les deux formulaires du Calendrier culturel MTL, avec leurs feuilles de réponses.
 *
 * Mode d'emploi (5 minutes) :
 *   1. Ouvrez https://script.google.com (connecté au compte Google du projet) → « Nouveau projet ».
 *   2. Effacez tout, collez ce fichier, cliquez sur 💾 (Enregistrer).
 *   3. En haut, choisissez la fonction « creerFormulaires », puis « Exécuter ».
 *      Google demande des autorisations : « Examiner les autorisations » → votre compte →
 *      « Paramètres avancés » → « Accéder à Projet sans titre (non sécurisé) » → « Autoriser ».
 *      (C'est votre propre script ; Google affiche cet avertissement pour tout script personnel.)
 *   4. Ouvrez « Journal d'exécution » en bas : il affiche les liens et les 3 dernières étapes à faire.
 *
 * Ce que le script fait pour chaque formulaire :
 *   - crée le formulaire avec les bonnes questions (les intitulés sont lus par le programme de collecte) ;
 *   - crée la feuille de réponses et y ajoute la colonne « Approuvé » (votre modération) ;
 *   - crée un onglet « publique » qui reprend les réponses SANS les courriels : c'est le seul onglet à publier.
 */

const DISCIPLINES = ["Théâtre", "Musique", "Danse", "Cirque", "Humour", "Cinéma",
  "Littérature et conférences", "Jeune public", "Exposition ou vernissage", "Autre"];

const CONFIDENTIALITE = "Votre courriel sert seulement à vous joindre au sujet de cette proposition. " +
  "Il n'est jamais publié ni partagé. Les propositions sont vérifiées avant d'apparaître sur le calendrier.";

function creerFormulaires() {
  const a = formulaireEvenement_();
  const b = formulaireCalendrier_();
  const lignes = [
    "",
    "=============== C'EST FAIT ===============",
    "",
    "FORMULAIRE A — Proposer un événement",
    "  Lien public (à mettre dans config.json → formulaireEvenement) : " + a.lienPublic,
    "  Feuille des réponses (votre modération) : " + a.feuille,
    "",
    "FORMULAIRE B — Ajouter mon calendrier",
    "  Lien public (à mettre dans config.json → formulaireCalendrier) : " + b.lienPublic,
    "  Feuille des réponses (votre modération) : " + b.feuille,
    "",
    "IL RESTE 3 ÉTAPES, pour CHAQUE feuille :",
    "  1. Ouvrez la feuille → Fichier → Partager → Publier sur le Web.",
    "  2. Choisissez l'onglet « publique » (PAS l'onglet des réponses) et le format « CSV »,",
    "     cliquez « Publier », puis copiez le lien.",
    "  3. Dans GitHub → Settings → Secrets and variables → Actions → Variables :",
    "     PROPOSITIONS_CSV_URL = lien CSV de la feuille A ; CALENDRIERS_CSV_URL = lien CSV de la feuille B.",
    "",
    "Modération : écrivez « oui » dans la colonne « Approuvé » d'une ligne pour la publier.",
  ];
  Logger.log(lignes.join("\n"));
}

function formulaireEvenement_() {
  const f = FormApp.create("Proposer un événement · Calendrier culturel MTL");
  f.setDescription("Un spectacle, un concert, un vernissage, une soirée sur l'île de Montréal ? " +
    "Ajoutez-le au calendrier. C'est gratuit.\n\n" + CONFIDENTIALITE);
  f.setCollectEmail(false);
  f.setConfirmationMessage("Merci ! Votre événement sera vérifié puis ajouté au calendrier (en général sous 48 h).");

  f.addTextItem().setTitle("Titre de l'événement").setRequired(true);
  f.addDateItem().setTitle("Date de l'événement").setRequired(true)
    .setHelpText("Plusieurs dates ? Envoyez le formulaire une fois par date, ou ajoutez plutôt votre calendrier (formulaire « Ajouter mon calendrier »).");
  f.addTextItem().setTitle("Heure (ex. 20 h)").setRequired(true);
  f.addTextItem().setTitle("Lieu (nom de la salle)").setRequired(true);
  f.addTextItem().setTitle("Adresse").setHelpText("ex. 4873 boul. Saint-Laurent");
  f.addMultipleChoiceItem().setTitle("Discipline").setChoiceValues(DISCIPLINES).setRequired(true);
  f.addTextItem().setTitle("Lien de la page de l'événement").setHelpText("Site, page Facebook, Instagram…");
  f.addMultipleChoiceItem().setTitle("Jeune public ?").setChoiceValues(["Oui", "Non"]);
  f.addParagraphTextItem().setTitle("Description courte (2 ou 3 phrases)");
  f.addTextItem().setTitle("Prix (ex. 15 $, Gratuit, Contribution volontaire)");
  f.addTextItem().setTitle("Lien pour acheter des billets (billetterie)");
  f.addTextItem().setTitle("Image : lien vers une photo du groupe ou du spectacle")
    .setHelpText("Seulement une photo que vous avez le droit de partager (la vôtre ou fournie par l'artiste).");
  f.addTextItem().setTitle("Courriel (pour vous joindre, non publié)").setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextIsEmail().build());

  return relier_(f, "Calendrier MTL · Événements proposés");
}

function formulaireCalendrier_() {
  const f = FormApp.create("Ajouter mon calendrier · Calendrier culturel MTL");
  f.setDescription("Vous programmez une salle, un bar, un festival ou une galerie ? Donnez-nous le lien de votre calendrier : " +
    "il sera relu automatiquement chaque jour, vous n'aurez plus rien à faire.\n\n" +
    "Le meilleur lien : un calendrier iCal (.ics) ou Google Agenda public. Sinon, l'adresse de votre page « Programmation ».\n\n" +
    CONFIDENTIALITE);
  f.setCollectEmail(false);
  f.setConfirmationMessage("Merci ! Nous vérifions le lien, puis votre programmation apparaîtra au calendrier (en général sous 48 h).");

  f.addTextItem().setTitle("Nom de l'organisme").setRequired(true);
  f.addTextItem().setTitle("Adresse web du calendrier (lien iCal, Google Agenda ou page Programmation)").setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextIsUrl().build());
  f.addTextItem().setTitle("Nom de la salle").setRequired(true);
  f.addTextItem().setTitle("Adresse de la salle").setRequired(true);
  f.addMultipleChoiceItem().setTitle("Discipline principale").setChoiceValues(DISCIPLINES);
  f.addTextItem().setTitle("Courriel (non publié)").setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextIsEmail().build());

  return relier_(f, "Calendrier MTL · Calendriers proposés");
}

/** Feuille de réponses + colonne « Approuvé » + onglet « publique » sans courriels. */
function relier_(form, nomFeuille) {
  const ss = SpreadsheetApp.create(nomFeuille);
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush();
  Utilities.sleep(3000);

  // L'onglet des réponses est créé par Google (son nom dépend de la langue du compte).
  const reponses = ss.getSheets().find(s => s.getFormUrl()) || ss.getSheets()[0];
  const entetes = reponses.getRange(1, 1, 1, reponses.getLastColumn()).getValues()[0];
  const colApprouve = entetes.length + 1;
  reponses.getRange(1, colApprouve).setValue("Approuvé").setFontWeight("bold").setBackground("#ffe14d");
  reponses.getRange(2, colApprouve, 999, 1).setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(["oui", "non"], true).setAllowInvalid(true).build());
  reponses.setFrozenRows(1);

  // Onglet « publique » : toutes les colonnes sauf le courriel
  const lettres = [];
  for (let i = 0; i < colApprouve; i++) {
    const titre = i < entetes.length ? String(entetes[i]) : "Approuvé";
    if (/courriel|e-?mail/i.test(titre)) continue;
    lettres.push("Col" + (i + 1));
  }
  const publique = ss.getSheetByName("publique") || ss.insertSheet("publique");
  publique.clear();
  publique.getRange("A1").setFormula(
    "=QUERY({'" + reponses.getName().replace(/'/g, "''") + "'!A:" + colonne_(colApprouve) + "}, \"select " +
    lettres.join(", ") + "\", 1)");  // Apps Script écrit toujours les formules avec des virgules
  publique.getRange("A1").setNote("Onglet à publier en CSV (Fichier → Partager → Publier sur le Web). " +
    "Il ne contient pas les courriels. Ne modifiez rien ici : modérez dans l'onglet des réponses.");
  if (ss.getSheetByName("Sheet1") || ss.getSheetByName("Feuille 1")) {
    const vide = ss.getSheetByName("Sheet1") || ss.getSheetByName("Feuille 1");
    if (vide.getLastRow() === 0 && ss.getSheets().length > 2) ss.deleteSheet(vide);
  }
  return { lienPublic: form.shortenFormUrl(form.getPublishedUrl()), feuille: ss.getUrl() };
}

function colonne_(n) {
  let s = "";
  while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}
