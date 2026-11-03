# App Power Apps "Gestione ore formazione"

Questa cartella contiene il **sorgente dell'app Canvas**: le formule dell'app e le 11 schermate in formato YAML, da incollare in Power Apps Studio. Non serve saper programmare: basta seguire i passi nell'ordine, copiando e incollando.

| File | Contenuto |
|---|---|
| `src/App.pa.yaml` | Oggetto **App**: formule con nome (`Formulas`), `OnStart`, `StartScreen` (riferimento) |
| `src/scr*.pa.yaml` | Una schermata per file, pronta per **Incolla codice** |
| `formule/00-App.Formulas.fx` · `00-App.OnStart.fx` | Testo da incollare nelle proprietà dell'App se Studio è **in inglese** |
| `formule/00-App.Formulas.it.fx` · `00-App.OnStart.it.fx` | Stesso testo in **notazione italiana** (`;` e `;;`) se Studio è **in italiano** |
| `formule/01…06-*.fx` | Le formule principali commentate (profilo, invio con allegati, esito coordinatore, validazione HR, chiusura e file paghe, amministrazione). Sono identiche a quelle delle schermate: servono da documentazione |

> Le formule nei file `.pa.yaml` sono sempre in notazione inglese (`,` tra gli argomenti, `;` tra le azioni): è il formato standard dei sorgenti Power Apps e Studio lo converte da solo quando si incolla una schermata.

---

## 1. Prerequisiti

- **Licenza**: basta Power Apps incluso in Microsoft 365. L'app usa solo connettori **standard** (SharePoint e i flussi Power Automate): nessuna licenza premium, nessun pagamento a consumo.
- **Ambiente**: l'ambiente **predefinito** del tenant (quello in cui sono stati importati i flussi).
- **Sito SharePoint** già creato con lo script (`sharepoint/Installa-GestioneFormazione.ps1`): `https://societadolce.sharepoint.com/sites/GestioneFormazione`.
- **Flussi** `SDF_API01…SDF_API10` già importati (vedere `powerautomate/README.md`). Possono essere ancora spenti mentre si costruisce l'app, ma vanno accesi prima del collaudo.
- Chi crea l'app deve:
  - essere **proprietario del sito** (per collegare tutte le liste);
  - essere **comproprietario dei 10 flussi API** (in Power Automate: *flusso → Modifica → Proprietari → aggiungi*). Senza questo, i flussi non compaiono nell'elenco «Aggiungi flusso» di Studio.
- Browser consigliato: Microsoft Edge o Chrome aggiornati.

## 2. Creare l'app vuota

1. Aprire [make.powerapps.com](https://make.powerapps.com) e controllare in alto a destra di essere nell'**ambiente predefinito**.
2. **Crea → App vuota → App canvas vuota**.
3. Nome: `Gestione ore formazione`; formato: **Tablet**. Premere **Crea**.
4. In Studio aprire **Impostazioni** (ingranaggio):
   - **Schermo** (*Display*): **Adatta alla pagina** (*Scale to fit*) = **No**; **Blocca proporzioni** (*Lock aspect ratio*) = **No**; **Blocca orientamento** = **No**. Così l'app si adatta a PC, tablet e smartphone.
   - **Generale**: **Limite di righe di dati** (*Data row limit*) = **2000** (serve ai riepiloghi e ai conteggi HR).
   - **Aggiornamenti**: le **formule con nome** devono essere disponibili (sono attive di default nelle versioni attuali; se compaiono tra le funzionalità in anteprima, attivarle). Le **funzioni definite dall'utente** *non* servono: l'app non le usa.
5. Salvare subito (**File → Salva**) per dare un nome all'app.

## 3. Collegare le liste SharePoint

1. Nel riquadro **Dati** (icona del cilindro) → **Aggiungi dati** → cercare **SharePoint** → scegliere o creare la connessione con il proprio account.
2. Incollare l'indirizzo del sito: `https://societadolce.sharepoint.com/sites/GestioneFormazione` → **Connetti**.
3. Selezionare queste **8 liste** e premere **Connetti**:
   `Richieste formazione` · `Lavoratori` · `Strutture organizzative` · `Catalogo corsi` · `Chiusure mensili` · `Registro modifiche` · `Ruoli applicativi` · `Configurazione`.
   Le raccolte documenti (*Allegati formazione*, *File paghe*) **non** vanno aggiunte: le gestiscono i flussi.
4. Controllare che i nomi nel riquadro Dati siano esattamente quelli sopra (senza «1» o «_1» finali). Se Power Apps aggiunge un suffisso, eliminare la connessione doppia e ricollegare.

> Aggiungere le liste all'app **non** dà accesso ai dati: ognuno vede solo ciò che i permessi SharePoint gli consentono. Lavoratori e coordinatori possono leggere direttamente solo *Catalogo corsi* e *Chiusure mensili*; tutto il resto passa dai flussi. Per questo le schermate di lavoratori e coordinatori non leggono mai le liste riservate a HR.

## 4. Aggiungere i 10 flussi

1. Nel menu a sinistra di Studio aprire **Power Automate** (icona dei flussi) → **Aggiungi flusso**.
2. Aggiungere uno per uno: `SDF_API01_Profilo`, `SDF_API02_MieRichieste`, `SDF_API03_SalvaRichiesta`, `SDF_API04_AggiornaProfilo`, `SDF_API05_RichiesteTeam`, `SDF_API06_EsitoCoordinatore`, `SDF_API07_EsitoHR`, `SDF_API08_ChiusuraMensile`, `SDF_API09_FilePaghe`, `SDF_API10_DettaglioRichiesta`.
3. I nomi devono restare **identici** (le formule chiamano, per esempio, `SDF_API03_SalvaRichiesta.Run(...)`). Il contratto dei parametri è in [docs/06-api-flussi.md](../docs/06-api-flussi.md).

## 5. Incollare le formule dell'App

1. Nella **Visualizzazione struttura** (*Tree view*) selezionare **App**.
2. Nel menu a discesa delle proprietà (in alto a sinistra) scegliere **Formulas** e incollare **tutto** il contenuto di:
   - `formule/00-App.Formulas.it.fx` se la barra della formula separa gli argomenti con **`;`** (Studio in italiano);
   - `formule/00-App.Formulas.fx` se usa **`,`** (Studio in inglese).
3. Proprietà **OnStart**: incollare `00-App.OnStart.it.fx` oppure `00-App.OnStart.fx` con la stessa regola.
4. **Colori**: all'inizio di *Formulas* ci sono `colPrimario` e gli altri colori. Sostituire i valori `RGBA(...)` con i colori ufficiali di Società Dolce: tutta l'app si aggiorna.

La proprietà **StartScreen** si imposta alla fine (passo 7), quando le schermate esistono.

## 6. Incollare le schermate

Ripetere per ogni file `src/scr*.pa.yaml`, in quest'ordine: `scrAccesso`, `scrProfilo`, `scrHome`, `scrMieRichieste`, `scrRichiesta`, `scrTeam`, `scrDettaglio`, `scrValidazioneHR`, `scrRiepilogo`, `scrChiusura`, `scrAdmin`.

1. Aprire il file con un editor di testo (Blocco note va bene), **Seleziona tutto** e **Copia**. Le righe che iniziano con `#` sono commenti e possono restare.
2. In Studio, nella **Visualizzazione struttura**, fare clic con il tasto destro su una schermata qualsiasi → **Incolla codice** (oppure il menu **…** → *Incolla*). La schermata viene creata con il nome del file.
3. Alla fine eliminare la schermata vuota iniziale (`Screen1`).

**Se un controllo viene rifiutato per la versione** (messaggio sulla versione di `Label@2.5.1`, `Classic/Button@2.2.0` e simili):
1. inserire una volta quel controllo dalla barra multifunzione (*Inserisci*);
2. clic destro sul controllo → **Copia codice** e incollarlo nel Blocco note: la riga `Control: …@x.y.z` mostra la versione corretta;
3. nel file `.pa.yaml` sostituire (Trova e sostituisci) tutte le occorrenze della versione vecchia con quella nuova e incollare di nuovo; poi eliminare il controllo di prova.

**Errori temporanei**: finché non sono state incollate tutte le schermate, le formule che portano a un'altra schermata (es. `Navigate(scrDettaglio, …)`) risultano in errore. Spariscono quando la schermata esiste. Se una formula rimane rossa, aprirla e premere **Invio** per farla ricalcolare. In `scrRichiesta` le formule che citano `ric_attAttestato` e `ric_attAltraDoc` restano in errore fino al passo 8.

## 7. Schermata iniziale

Selezionare **App** → proprietà **StartScreen** → scrivere `scrAccesso`.

## 8. Controlli allegati (attestato e altra documentazione)

Il controllo «Allegati» esiste solo dentro un modulo collegato a una lista SharePoint: lo si prende da un modulo temporaneo e lo si sposta nella schermata.

1. Aggiungere una schermata vuota di appoggio (*Nuova schermata → Vuota*).
2. **Inserisci → Modulo di modifica** (*Edit form*); nel riquadro a destra impostare l'origine dati su **Richieste formazione**.
3. Nel riquadro *Campi* → **Modifica campi** → aggiungere il campo **Allegati** (*Attachments*) se non c'è già. Se il campo non compare, nella lista SharePoint *Richieste formazione* → *Impostazioni elenco → Impostazioni avanzate* → **Allegati: Abilitati** (è l'impostazione predefinita), poi aggiornare l'origine dati in Studio.
4. Selezionare la scheda dati *Allegati* → riquadro *Avanzate* → **Sblocca per modificare le proprietà**.
5. Selezionare il controllo allegati **dentro** la scheda (nome tipo `DataCardValue…`) → **Ctrl+X** (taglia).
6. Andare in `scrRichiesta`, nella struttura selezionare il contenitore **`ric_conAttestato`** (sezione Allegati) → **Ctrl+V**.
7. Rinominare il controllo incollato in **`ric_attAttestato`** e impostare queste proprietà (nella barra della formula; in italiano i separatori sono `;`):

   | Proprietà | Valore |
   |---|---|
   | Items | cancellare la formula (lasciare vuoto) oppure `Blank()` |
   | MaxAttachments | `1` |
   | MaxAttachmentSize | `10` (MB) |
   | DisplayMode | `If(locSolaLettura, DisplayMode.View, DisplayMode.Edit)` |
   | AddAttachmentText | `"Carica l’attestato (PDF o immagine)"` |
   | NoAttachmentsText | `"Nessun file selezionato"` |
   | MaxAttachmentsText | `"Un solo file: per sostituirlo elimina prima quello presente"` |
   | BorderColor | `colBordo` |
   | Height | `100` |
   | Tooltip, AccessibleLabel | `"Attestato"` |

   Se altre proprietà mostrano errori perché citano `Parent.…` (es. *BorderColor*, *Tooltip*), sostituirle con i valori sopra o con un testo semplice.
8. Copiare `ric_attAttestato` (Ctrl+C), selezionare il contenitore **`ric_conAltraDoc`** e incollare (Ctrl+V); rinominare la copia in **`ric_attAltraDoc`** e cambiare `AddAttachmentText` in `"Carica altra documentazione"`.
9. Eliminare il modulo e la schermata di appoggio.
10. Controllare che in `scrRichiesta` non ci siano più errori (la formula del pulsante nascosto `ric_btnEsegui` usa i due controlli).

Come funziona: al salvataggio l'app trasforma il file in testo (*data URI*) con `JSON(..., JSONFormat.IncludeBinaryData)` e lo passa a `SDF_API03_SalvaRichiesta`, che lo salva nella cartella del coordinatore nella raccolta *Allegati formazione*. Il file **non** viene salvato nella lista: gli allegati della lista restano vuoti.

## 9. Verifica, salvataggio e pubblicazione

1. Aprire il **Verifica app** (icona dello stetoscopio): non devono restare errori rossi. Gli avvisi di **delega** (*delegation*) su alcune formule HR sono previsti e documentati (vedi §13).
2. **Salva**, poi **Pubblica → Pubblica questa versione**.
3. Aprire i **Dettagli** dell'app e copiare il **Collegamento web** (`https://apps.powerapps.com/play/e/…/a/…?tenantId=…`).
4. Nella lista SharePoint **Configurazione** → chiave **`AppUrl`** → incollare il collegamento. I flussi lo usano per il pulsante «Apri la richiesta» nelle e-mail (`…&richiesta=<ID>`), che l'app legge con `Param("richiesta")`.

## 10. Condivisione

1. **Condividi** l'app con **Tutti tranne gli utenti esterni** (*Everyone except external users*) oppure con un gruppo che comprenda tutti i lavoratori, coordinatori e HR. Ruolo: **Utente** (non comproprietario).
2. Al primo avvio ogni utente conferma la connessione SharePoint con il proprio account. I flussi invece girano con le connessioni dell'account di servizio (in Power Automate: *Dettagli del flusso → Utenti solo esecuzione → «Usa questa connessione»*).
3. La condivisione dà solo la possibilità di **aprire** l'app: ognuno continua a vedere soltanto ciò che i flussi e i permessi SharePoint gli consentono.

## 11. Pubblicazione nella intranet e in Teams

- **Intranet**: modificare la pagina SharePoint → **+** → web part **Power Apps** → incollare il collegamento web o l'ID dell'app → impostare un'altezza adeguata (es. 900 px) → **Ripubblica** la pagina.
- **Teams** (facoltativo): dai *Dettagli* dell'app → **Aggiungi a Teams**, oppure in Teams *App → Power Apps* → aggiungere l'app.
- **Smartphone**: app *Power Apps* (iOS/Android) con l'account Microsoft 365, oppure il collegamento web nel browser.

## 12. Schermate, funzioni e ruoli

| Schermata | Funzioni | Ruoli | Dati |
|---|---|---|---|
| `scrAccesso` | Benvenuto, utente Microsoft 365 collegato, link «Hai dimenticato la password?», caricamento profilo, «Utente non censito», instradamento al profilo (primo accesso) o al dettaglio (link da e-mail) | tutti | API01 |
| `scrProfilo` | E-mail personale e codice fiscale obbligatori al primo accesso (CF mostrato mascherato), dati organizzativi in sola lettura, «Segnala variazione a HR» | lavoratore | API04, API01 |
| `scrHome` | Nome e ruolo; riquadri Inserisci formazione, Formazione approvata, In attesa / integrazioni, Riepilogo; per coordinatore e HR richieste aperte, da approvare, integrazioni e solleciti; collegamenti rapidi | tutti (contenuto per ruolo) | API02, API05; HR lettura diretta |
| `scrMieRichieste` | Elenco con filtri anno/mese/stato, stato a colori, visualizza / modifica / annulla, nuova richiesta | lavoratore | API02, API03 |
| `scrRichiesta` | Nuova richiesta o modifica: dati del lavoratore, corso a catalogo / esterno (storico o nuovo), orari, ore calcolate, allegati, dichiarazioni, controlli R1–R3, R5, R6, R7, R9, R11; Salva bozza, Invia, Annulla | lavoratore | API03; lettura *Catalogo corsi* e *Chiusure mensili* |
| `scrTeam` | Richieste dei propri collaboratori con filtri mese, anno, lavoratore, servizio, centro di costo, stato; ore svolte/richieste/riconosciute, stato lavoratore, duplicati | coordinatore | API05 |
| `scrDettaglio` | Tutti i dati, allegati, esito del coordinatore (approva / respingi / integrazione, ore riconosciute, R4), validazione HR, modifica / annulla del lavoratore, storico (HR) | lavoratore, coordinatore, HR, amministratore | API10, API06, API07, API03 |
| `scrValidazioneHR` | Richieste in attesa di validazione con filtri, segnali (duplicato, attestato mancante, anomalie, R4), ore HR riga per riga, azioni su selezione o su perimetro (coordinatore, centro di costo, servizio, area) | HR, amministratore | lettura diretta; API07 |
| `scrRiepilogo` | Indicatori del mese (lavoratori distinti, richieste, ore frequentate/richieste/approvate da coordinatori e HR), elenchi in attesa e respinte, tabella di dettaglio, filtri | lavoratore (proprie), coordinatore (gruppo), HR (tutto) | API02, API05, lettura diretta HR |
| `scrChiusura` | Verifica del mese (aperte, anomalie, segnalazioni, CF mancanti), chiusura, file paghe, riapertura (solo amministratore), storico chiusure | HR, amministratore | lettura diretta; API08, API09 |
| `scrAdmin` | Lavoratori, organigramma, catalogo corsi (con validazione dei corsi esterni), ruoli e utenti, configurazione; ogni modifica scrive il *Registro modifiche* | amministratore | modifica diretta |

Il menu laterale mostra solo le voci del proprio ruolo (formula `tblMenu`); su smartphone si apre con l'icona ☰.

## 13. Variabili, raccolte e formule con nome

**Variabili globali**

| Variabile | Contenuto |
|---|---|
| `varCaricamento`, `varMessaggioCaricamento` | Mostrano l'indicatore «Caricamento…» mentre un flusso lavora |
| `varMenuAperto` | Menu aperto su smartphone |
| `varJsonProfilo`, `varProfiloCaricato`, `varErroreProfilo` | Risposta di API01 (testo JSON), stato del caricamento, eventuale errore |
| `varParamGestito`, `varDaLinkDiretto` | Gestione del collegamento diretto `&richiesta=<ID>` |
| `varJsonMieRichieste`, `varMieCaricate` | Risposta di API02 (richieste del lavoratore) |
| `varJsonTeam`, `varTeamCaricato`, `varAnnoTeam`, `varMeseTeam` | Risposta di API05 e periodo richiesto |
| `varJsonDettaglio`, `varIdDettaglio` | Risposta di API10 e ID della richiesta aperta |
| `varIdModifica`, `varRicEdit` | Richiesta in modifica (0 = nuova) e suoi dati |
| `varFiltroGruppoMie`, `varPerimetroRiep` | Filtro preimpostato dalla Home per «Le mie richieste» e per il riepilogo |

**Raccolte** (create con `ClearCollect`)

| Raccolta | Contenuto |
|---|---|
| `colMesiChiusi` | Mesi chiusi (da *Chiusure mensili*), per bloccare modifica e annullamento |
| `colHomeHrValidare`, `colHomeHrCoord`, `colHomeHrIntegr`, `colHomeHrSolleciti` | Conteggi HR della Home (solo ID, massimo 2000: oltre si mostra «2000+») |
| `colSelezioneHR`, `colDaElaborareHR` | Righe spuntate in Validazione HR e richieste da inviare ad API07 |
| `colRiepSP`, `colRiepilogo`, `colRiepFiltrato` | Riepilogo: dati letti, uniformati e filtrati |
| `colChiAperte`, `colChiDaVerificare`, `colChiAnomalie`, `colChiSegnalazioni`, `colChiLavSenzaCF`, `colChiSenzaCF` | Controlli della chiusura mensile |

**Formule con nome principali** (App → Formulas): `colPrimario` e gli altri colori; `isMobile` (larghezza < 700); `tblStati` (stato → colore, gruppo, modificabile/annullabile dal lavoratore); `recProfilo`, `isLavoratore`, `isCoord`, `isHR` (vale anche per l'Amministratore), `isAdmin`, `ruoloApp` (ruolo più alto); `tblMenu`; `colMieRichieste`, `colRichiesteTeam`, `colLavoratoriTeam`, `recDettaglio`, `recPermessi`, `colStorico` (risposte JSON dei flussi convertite in tabelle). Le formule con nome si ricalcolano da sole quando cambia la variabile da cui dipendono.

## 14. Note e limiti

- **Colonne di sistema**: nei siti in italiano le colonne *Created*/*Modified* si chiamano **`Creato`**/**`Modificato`** in Power Apps (nei siti in inglese `Created`/`Modified`). L'app non le usa direttamente sulle liste: le date arrivano dai flussi (`creato`, `modificato`). Se si aggiungono formule, usare il nome che compare nel proprio sito.
- **Nomi delle colonne**: le formule usano i **nomi visualizzati** di `sharepoint/schema.yaml` (es. `'Stato richiesta'`, `'Login coordinatore'`). Rinominare una colonna in SharePoint rompe le formule.
- **Delega (2000 righe)**: gli elenchi HR usano filtri delegabili (uguaglianze su colonne indicizzate e «inizia con»). Restano non delegabili, e quindi limitati alle prime 2000 righe filtrate: i conteggi della Home, l'elenco dei valori del perimetro in Validazione HR, il riepilogo HR (per anno e mese), le verifiche di chiusura sul mese, l'elenco dei coordinatori in Amministrazione. Con i volumi previsti (un mese di richieste) è sufficiente; oltre, filtrare per mese e perimetro.
- **Velocità**: le schermate di lavoratori e coordinatori leggono tramite flussi (2–5 secondi). I dati restano in memoria durante la sessione; l'icona ↻ li aggiorna.
- **Formati numerici**: i formati di `Text()` sono scritti come `"[$-en-US]0.##"`: il punto indica sempre i decimali, mentre il risultato appare nella lingua dell'utente (es. `3,5`).
- **Lingua delle formule**: i file YAML e i `.fx` senza `.it` sono in notazione inglese; i file `.it.fx` sono già convertiti per Studio in italiano.

## 15. Problemi frequenti

| Sintomo | Soluzione |
|---|---|
| «Utente non censito» per un lavoratore | Verificare nella lista *Lavoratori* che `Login Microsoft 365` sia l'account dell'utente in minuscolo e *Stato lavoratore* = Attivo |
| Un flusso non compare in «Aggiungi flusso» | Chi crea l'app deve essere comproprietario del flusso e trovarsi nello stesso ambiente |
| Errore di permessi su una lista per un lavoratore | Qualche formula visibile al lavoratore legge una lista riservata: controllare di non aver modificato le condizioni `If(isHR, …)` |
| Gli allegati non vengono salvati | Controllare i nomi `ric_attAttestato` / `ric_attAltraDoc` e `MaxAttachmentSize` = 10 |
| Il link «Apri la richiesta» nelle e-mail apre la Home | Controllare la chiave `AppUrl` in *Configurazione* (deve essere il collegamento web dell'app) |
