# 6. Contratto tra app e flussi (API)

Questo documento è il **contratto** tra l'app Power Apps (`powerapps/`) e i flussi Power Automate (`powerautomate/`). Se si modifica un flusso o una formula dell'app, va mantenuto allineato.

## 6.1 Convenzioni comuni

- **Nome del flusso** = nome usato in Power Fx: `SDF_API03_SalvaRichiesta.Run(...)`. Nomi senza spazi né trattini, così Power Apps non li altera.
- **Trigger**: *Power Apps (V2)*. Tutti i parametri sono **obbligatori** e **posizionali**, nell'ordine indicato. Un parametro testo "vuoto" si passa come `""`, un numero assente come `0`.
- **Chi chiama**: `toLower(triggerOutputs()?['headers']?['x-ms-user-email'])`. È l'unica identità di cui il flusso si fida: nessun parametro indica l'utente.
- **Risposta**: azione *Rispondi a un'app o a un flusso di Power Apps* con 3 output di tipo testo:
  - `esito`: `"OK"` oppure `"ERRORE"`;
  - `messaggio`: testo per l'utente in italiano, chiaro e senza dettagli tecnici. Più errori di validazione sono separati da `" · "`;
  - `dati`: JSON serializzato in testo (`"{}"` se non serve).

  In Power Fx: `Set(varEsito, SDF_API02_MieRichieste.Run(0)); If(varEsito.esito = "OK", ParseJSON(varEsito.dati) ...)`.
- **Tempo massimo**: Power Apps attende la risposta per **120 secondi**. Le elaborazioni lunghe (API07 con molte richieste, API08, API09) rispondono **prima** di aggiornare gli elementi e completano il lavoro dopo la risposta.
- **Configurazione**: ogni flusso legge la lista *Configurazione* e costruisce un oggetto chiave/valore. *Seleziona* con chiave dinamica `@item()?['Title']` e valore `@item()?['Valore']`, poi `json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`. Uso: `outputs('Configurazione')?['EmailHR']`.
- **Errori**: la logica sta in un ambito *Prova*. Un ambito *Errore*, eseguito se *Prova* fallisce o va in timeout, risponde `esito = "ERRORE"`, `messaggio = "Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione."` e invia a `EmailHR` il link all'esecuzione: `concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])`.
- **Registro**: ogni azione che cambia dati crea un elemento in *Registro modifiche*: `Title` = azione, `RichiestaRif`, `IdRichiesta`, `Tabella`, `IdRecord`, `Campo`, `ValorePrecedente`, `ValoreNuovo`, `Ruolo`, `LoginAutore` = chi chiama, `Nota`.
- **Date**: la data della sessione viaggia come `yyyy-MM-dd`; date e ore di sistema in ISO 8601 UTC. Gli orari sono testo `HH:mm` e le ore sono numeri decimali con il punto nel JSON.
- **Numeri delle ore**: il flusso ricalcola sempre le durate a partire dagli orari e arrotonda a 2 decimali. I valori calcolati dall'app sono solo indicativi.
- **E-mail**: *Invia un messaggio di posta elettronica (V2)* di Office 365 Outlook. Il campo *Da (Invia come)* = `Configurazione.MittenteEmail`, se valorizzato. Destinatari:
  - lavoratore → **`EmailPersonale`** (se vuota non si invia nulla e si annota nel registro);
  - coordinatore → `CoordinatoreEmail`;
  - HR → `Configurazione.EmailHR`.

  Corpo HTML con intestazione "Gestione ore formazione – Società Dolce", tabella dei dati principali e pulsante **"Apri la richiesta"** che punta a `concat(Configurazione.AppUrl, '&richiesta=', ID)`.
- **Stati** (etichette esatte della colonna Scelta *Stato*): vedi `sharepoint/schema.yaml` → `choices.stato_richiesta`.

## 6.2 Oggetto "Richiesta" (JSON)

Usato in uscita da API02, API05, API10 e in parte in ingresso ad API03. Le chiavi corrispondono alla colonna `json` di `sharepoint/schema.yaml`.

<!-- TABELLA_RICHIESTA_JSON_INIZIO -->
| Campo JSON | Colonna SharePoint (nome interno) | Nome visualizzato | Tipo JSON |
|---|---|---|---|
| `id` | `ID` | ID | numero intero |
| `idRichiesta` | `Title` | ID richiesta | testo |
| `lavoratoreLogin` | `LavoratoreLogin` | Login lavoratore | testo |
| `lavoratoreId` | `LavoratoreRif` | ID lavoratore | numero intero |
| `cognome` | `Cognome` | Cognome | testo |
| `nome` | `Nome` | Nome | testo |
| `emailPersonale` | `EmailPersonale` | E-mail personale | testo |
| `area` | `Area` | Area | testo (etichetta) |
| `servizio` | `Servizio` | Servizio | testo |
| `centroDiCosto` | `CentroDiCosto` | Centro di costo | testo |
| `strutturaId` | `StrutturaRif` | ID struttura | numero intero |
| `coordinatoreLogin` | `CoordinatoreLogin` | Login coordinatore | testo |
| `coordinatoreNome` | `CoordinatoreNome` | Coordinatore | testo |
| `coordinatoreEmail` | `CoordinatoreEmail` | E-mail coordinatore | testo |
| `corsoId` | `CorsoRif` | ID corso | numero intero |
| `codiceCorso` | `CodiceCorso` | Codice univoco corso | testo |
| `titoloCorso` | `TitoloCorsoCatalogo` | Titolo del corso a catalogo | testo |
| `titoloCorsoLibero` | `TitoloCorsoLibero` | Titolo corso libero | testo |
| `durataCorso` | `DurataCorso` | Durata complessiva corso | numero |
| `enteErogatore` | `EnteErogatore` | Ente erogatore | testo (etichetta) |
| `modalita` | `Modalita` | Modalità di svolgimento | testo (etichetta) |
| `piuGiornate` | `PiuGiornate` | Più giornate formative | booleano |
| `dataSessione` | `DataSessione` | Data sessione formativa | testo `yyyy-MM-dd` |
| `oraInizioSessione` | `OraInizioSessione` | Ora inizio sessione | testo |
| `oraFineSessione` | `OraFineSessione` | Ora fine sessione | testo |
| `durataSessione` | `DurataSessione` | Durata sessione | numero |
| `oraIngresso` | `OraIngresso` | Ora ingresso lavoratore | testo |
| `oraUscita` | `OraUscita` | Ora uscita lavoratore | testo |
| `oreFrequentate` | `OreFrequentate` | Ore frequentate dichiarate | numero |
| `oreRetribuiteRichieste` | `OreRetribuiteRichieste` | Ore retribuite richieste | numero |
| `oreGettoneRichieste` | `OreGettoneRichieste` | Ore gettone richieste | numero |
| `oreRetribuiteCoord` | `OreRetribuiteCoord` | Ore retribuite riconosciute coordinatore | numero |
| `oreGettoneCoord` | `OreGettoneCoord` | Ore gettone riconosciute coordinatore | numero |
| `oreRetribuiteHR` | `OreRetribuiteHR` | Ore retribuite approvate HR | numero |
| `oreGettoneHR` | `OreGettoneHR` | Ore gettone approvate HR | numero |
| `attestatoUrl` | `AttestatoUrl` | Attestato | testo (URL) |
| `altraDocUrl` | `AltraDocUrl` | Altra documentazione | testo (URL) |
| `attestatoPresente` | `AttestatoPresente` | Attestato presente | booleano |
| `noteLavoratore` | `NoteLavoratore` | Note del lavoratore | testo |
| `noteCoordinatore` | `NoteCoordinatore` | Note del coordinatore | testo |
| `noteHR` | `NoteHR` | Note HR | testo |
| `stato` | `Stato` | Stato richiesta | testo (etichetta) |
| `dataInvio` | `DataInvio` | Data invio | testo ISO 8601 UTC |
| `dataApprovazioneCoord` | `DataApprovazioneCoord` | Data approvazione coordinatore | testo ISO 8601 UTC |
| `dataValidazioneHR` | `DataValidazioneHR` | Data validazione HR | testo ISO 8601 UTC |
| `meseCompetenza` | `MeseCompetenza` | Mese di competenza | numero intero |
| `annoCompetenza` | `AnnoCompetenza` | Anno di competenza | numero intero |
| `periodoChiusura` | `PeriodoChiusura` | Periodo chiusura | testo |
| `confermaPartecipazione` | `ConfermaPartecipazione` | Conferma partecipazione | booleano |
| `confermaCorrettezza` | `ConfermaCorrettezza` | Conferma correttezza dati | booleano |
| `autorizzazioneInvio` | `AutorizzazioneInvio` | Autorizzazione all'invio | booleano |
| `possibileDuplicato` | `PossibileDuplicato` | Possibile duplicato | booleano |
| `anomalie` | `Anomalie` | Anomalie rilevate | testo |
| `giorniAttesa` | `GiorniAttesa` | Giorni lavorativi in attesa | numero intero |
| `segnalataHR` | `SegnalataHR` | Sollecito segnalato a HR | booleano |
| `ultimaModificaDa` | `UltimaModificaDa` | Utente ultima modifica | testo |
| `creato` | `Created` | Creato | testo ISO 8601 UTC |
| `modificato` | `Modified` | Modificato | testo ISO 8601 UTC |
<!-- TABELLA_RICHIESTA_JSON_FINE -->

I valori nulli si restituiscono come `null` (testo) o `0` (numeri). Il flusso costruisce l'oggetto con un'azione *Seleziona* sugli elementi letti da SharePoint, la stessa mappatura in API02, API05 e API10.

---

## 6.3 SDF_API01_Profilo

| | |
|---|---|
| Parametri | nessuno |
| Chi può chiamarlo | qualunque utente |

**Logica**
1. *Lavoratori*: `Login eq '<chiamante>'` (top 1).
2. *Lavoratori*: `CoordinatoreLogin eq '<chiamante>' and StatoLavoratore eq 'Attivo'` (top 1) → coordinatore.
3. *Ruoli applicativi*: `Title eq '<chiamante>' and Attivo eq 1` → HR / amministratore.

**`dati`**
```json
{
  "login": "mario.rossi@societadolce.it",
  "nomeVisualizzato": "Mario Rossi",
  "ruoli": { "lavoratore": true, "coordinatore": false, "hr": false, "amministratore": false },
  "profiloCompleto": true,
  "lavoratore": {
    "id": 12, "cognome": "Rossi", "nome": "Mario",
    "emailAziendale": "", "emailPersonale": "mario.rossi@gmail.com",
    "cfRegistrato": true, "cfMascherato": "RSS**********12X",
    "area": "Area Centro", "servizio": "Nido Girasole", "centroDiCosto": "CEN-001", "strutturaId": 3,
    "coordinatoreLogin": "anna.bianchi@societadolce.it", "coordinatoreNome": "Anna Bianchi", "coordinatoreEmail": "anna.bianchi@societadolce.it",
    "stato": "Attivo", "segnalazioneAperta": false
  }
}
```
`lavoratore` è `null` se l'utente non è censito o non è attivo. `profiloCompleto` vale `lavoratore != null && emailPersonale != "" && cfRegistrato`. `ruoli.lavoratore` = lavoratore attivo.

---

## 6.4 SDF_API02_MieRichieste

| | |
|---|---|
| Parametri | 1. `anno` (numero; `0` = tutti gli anni) |
| Chi può chiamarlo | lavoratore |

Restituisce le richieste con `LavoratoreLogin eq '<chiamante>'` (e `AnnoCompetenza eq anno` se > 0), ordinate per `Modified` decrescente.
**`dati`**: `{ "richieste": [ Richiesta, ... ] }`

---

## 6.5 SDF_API03_SalvaRichiesta

| | |
|---|---|
| Parametri | 1. `dati` (testo JSON) · 2. `azione` (`"bozza"`, `"invia"` o `"annulla"`) · 3. `attestato` (testo: data URI `data:<tipo>;base64,...` oppure `""`) · 4. `nomeAttestato` (testo) · 5. `altraDoc` (testo: data URI o `""`) · 6. `nomeAltraDoc` (testo) |
| Chi può chiamarlo | lavoratore attivo, solo sulle proprie richieste |

**`dati` in ingresso**
```json
{
  "id": 0,
  "enteErogatore": "Datore di lavoro",
  "corsoId": 5,
  "nuovoCorso": null,
  "dataSessione": "2026-10-14",
  "oraInizioSessione": "09:00", "oraFineSessione": "13:00",
  "oraIngresso": "09:00", "oraUscita": "12:30",
  "oreRetribuiteRichieste": 3.5, "oreGettoneRichieste": 0,
  "noteLavoratore": "",
  "confermaPartecipazione": true, "confermaCorrettezza": true, "autorizzazioneInvio": true,
  "confermaDuplicato": false
}
```
- `id = 0` → nuova richiesta; altrimenti l'ID dell'elemento da modificare.
- Corso esterno **già in storico**: `enteErogatore = "Committente o altro soggetto"` e `corsoId` del corso.
- Corso esterno **nuovo**: `corsoId = 0` e `"nuovoCorso": { "titolo": "...", "modalita": "In presenza", "durata": 8, "piuGiornate": true, "nomeEnte": "ASL Bologna" }`.
- In caso di `azione = "annulla"` conta solo `id`.

**Logica**
1. Lavoratore chiamante attivo (*Lavoratori*). Se `id > 0`: l'elemento deve avere `LavoratoreLogin` = chiamante e uno stato modificabile, o annullabile per "annulla" (tabella §1.5 di [01-architettura.md](01-architettura.md)).
2. **annulla** → `Stato` = Annullata, registro. Se la richiesta era già stata inviata, e-mail al coordinatore. Risposta.
3. Corso:
   - a catalogo: legge *Catalogo corsi* (`EnteErogatore` = Datore di lavoro, attivo, validato) → codice, titolo, modalità, durata, gettone previsto; se *Gettone previsto* = No, ore gettone = 0;
   - esterno da storico: legge il corso (deve avere `LoginAutore` = chiamante);
   - esterno nuovo: crea l'elemento in *Catalogo corsi* (`Origine` = Inserito dal lavoratore, `StatoValidazione` = Da validare, `LoginAutore` = chiamante, `GettonePrevisto` = Sì, `CorsoAttivo` = Sì), poi imposta `CodiceCorso` = `EXT-` + ID a 6 cifre.
4. Ricalcolo e controlli **R1, R2, R3, R5, R9, R12**. Per **invia** anche **R6, R11**: R6 blocca se la somma delle sessioni supera la durata.
5. Dati organizzativi copiati da *Lavoratori*, non dal client: login, ID, cognome, nome, e-mail personale, area, servizio, centro di costo, struttura, coordinatore (login, nome, e-mail).
6. Crea o aggiorna l'elemento. Per i nuovi: `Title` = `RF-<anno corrente>-<ID a 6 cifre>`. `UltimaModificaDa` = chiamante.
7. **Allegati**: se presenti, cartella `Allegati formazione/<login coordinatore con @ e . sostituiti da _>`.
   - Se la cartella non esiste: *Crea nuova cartella*, poi *Concedi l'accesso a un elemento o una cartella* al coordinatore con ruolo *Può visualizzare*, senza notifica.
   - File: `<ID richiesta>_<Attestato|Altra documentazione>_<nome file>`, contenuto `dataUriToBinary(...)`. Proprietà: `RichiestaRif`, `IdRichiesta`, `TipoAllegato`, `LavoratoreLogin`.
   - Sull'elemento: `AttestatoUrl` / `AltraDocUrl` (URL completo del file) e `AttestatoPresente`.
8. **bozza** → `Stato` = Bozza.
   **invia** → *Inviata al coordinatore* (registro), poi:
   - controllo duplicati **R7**: se ce ne sono e `confermaDuplicato = false`, risponde `ERRORE` con messaggio "Esiste già una richiesta per lo stesso corso nella stessa data: confermi l'invio?" e `dati = {"richiestaConferma":"duplicato"}`, lasciando la richiesta in Bozza;
   - se confermato: `PossibileDuplicato` = Sì su tutte le richieste coinvolte e nota in *Anomalie*;
   - `Stato` = In attesa del coordinatore, `DataInvio` = adesso, `GiorniAttesa` = 0, `SegnalataHR` = No;
   - e-mail al coordinatore (con avviso di possibile duplicato, se presente) ed e-mail a HR in caso di duplicato.
9. Registro: una riga per l'azione e una per ogni campo modificato rispetto alla versione precedente.

**`dati` in uscita**: `{ "id": 123, "idRichiesta": "RF-2026-000123", "stato": "In attesa del coordinatore", "avvisi": ["..."] }`

---

## 6.6 SDF_API04_AggiornaProfilo

| | |
|---|---|
| Parametri | 1. `emailPersonale` · 2. `codiceFiscale` · 3. `segnalazione` (testo; `""` = non modificare) |
| Chi può chiamarlo | lavoratore (anche se il profilo non è completo) |

**Logica**
- `emailPersonale`: deve contenere `@` e `.`; aggiorna *Lavoratori* e le richieste del lavoratore ancora in Bozza o in integrazione.
- `codiceFiscale`: `toUpper(trim())`, lunghezza 16, caratteri alfanumerici. Salva `CodiceFiscale`, `CFMascherato` = prime 3 + `**********` + ultime 3, `CFRegistrato` = Sì.
- `segnalazione`: aggiunge in testa a `SegnalazioneVariazione` la riga `"[gg/MM/aaaa] testo"`, imposta `SegnalazioneAperta` = Sì e invia un'e-mail a HR.
- Registro: il CF viene annotato solo come "Codice fiscale aggiornato", **mai il valore**.

**`dati`**: `{ "emailPersonale": "...", "cfRegistrato": true, "cfMascherato": "RSS**********12X", "segnalazioneAperta": true }`

---

## 6.7 SDF_API05_RichiesteTeam

| | |
|---|---|
| Parametri | 1. `anno` (numero) · 2. `mese` (numero; `0` = tutti) |
| Chi può chiamarlo | coordinatore |

**`dati`**
```json
{
  "richieste": [ Richiesta, ... ],
  "lavoratori": [ { "id": 12, "login": "...", "nominativo": "Rossi Mario", "servizio": "...", "centroDiCosto": "...", "stato": "Attivo" } ]
}
```
`richieste`: `CoordinatoreLogin eq '<chiamante>' and AnnoCompetenza eq anno` (e mese se > 0), escluse le **Bozze**. `lavoratori`: tutti quelli con `CoordinatoreLogin = chiamante`. Il coordinatore apre gli allegati con l'URL: ha accesso in lettura alla propria cartella.

---

## 6.8 SDF_API06_EsitoCoordinatore

| | |
|---|---|
| Parametri | 1. `id` (numero) · 2. `azione` (`"approva"`, `"respingi"` o `"integrazione"`) · 3. `oreRetribuite` (numero) · 4. `oreGettone` (numero) · 5. `nota` (testo) |
| Chi può chiamarlo | il coordinatore della richiesta, diverso dal lavoratore |

**Logica**: controlli su stato (In attesa del coordinatore), chiamante (`CoordinatoreLogin` e diverso da `LavoratoreLogin`), mese non chiuso, **R4**, nota obbligatoria per respingi e integrazione.
- **approva**:
  - `OreRetribuiteCoord`, `OreGettoneCoord`, `NoteCoordinatore`, `DataApprovazioneCoord` = adesso;
  - stato *Approvata dal coordinatore* (registro), poi **In attesa di validazione HR**;
  - e-mail al lavoratore con le ore riconosciute.
- **respingi**: `Stato` = Respinta dal coordinatore, `NoteCoordinatore` = motivazione, e-mail al lavoratore.
- **integrazione**: `Stato` = Integrazione richiesta dal coordinatore, `NoteCoordinatore` = nota, e-mail al lavoratore con il collegamento.
- Registro: azione + variazioni delle ore rispetto alle ore richieste.

**`dati`**: `{ "id": 123, "stato": "In attesa di validazione HR" }`

---

## 6.9 SDF_API07_EsitoHR

| | |
|---|---|
| Parametri | 1. `dati` (testo JSON) |
| Chi può chiamarlo | ruolo Formazione HR o Amministratore |

```json
{ "azione": "valida", "nota": "", "richieste": [ { "id": 123, "oreRetribuite": 3.5, "oreGettone": 0 }, { "id": 124, "oreRetribuite": -1, "oreGettone": -1 } ] }
```
`azione`: `"valida"`, `"respingi"` o `"integrazione"`. Ore `-1` = usa le ore riconosciute dal coordinatore: serve alla validazione per perimetro.

**Logica**: verifica del ruolo del chiamante, nota obbligatoria per respingi e integrazione. Per ogni richiesta (ciclo con concorrenza 10):
- deve essere *In attesa di validazione HR*, con mese non chiuso, **R4** rispettata e lavoratore ≠ chiamante; altrimenti finisce in `scartate` con il motivo;
- **valida**: `OreRetribuiteHR`, `OreGettoneHR`, `NoteHR`, `DataValidazioneHR`, `Stato` = Validata da HR, e-mail a lavoratore e coordinatore;
- **respingi** / **integrazione**: `Stato` = Respinta da HR / Integrazione richiesta da HR, `NoteHR` = nota, e-mail a lavoratore e coordinatore;
- registro.

Se le richieste sono più di 25, il flusso risponde subito `esito = "OK"`, `messaggio = "Elaborazione avviata per N richieste: riceverai un'e-mail con l'esito."`, poi elabora e manda il riepilogo a `EmailHR` e al chiamante.

**`dati`**: `{ "elaborate": 10, "scartate": [ { "id": 124, "motivo": "Mese chiuso" } ] }`

---

## 6.10 SDF_API08_ChiusuraMensile

| | |
|---|---|
| Parametri | 1. `anno` · 2. `mese` (numeri) · 3. `azione` (`"chiudi"` o `"riapri"`) · 4. `nota` (testo; obbligatoria per riapri) |
| Chi può chiamarlo | chiudi: HR o Amministratore · riapri: solo Amministratore |

**chiudi**
1. Crea o aggiorna l'elemento *Chiusure mensili* con `Title` = `AAAA-MM`: `StatoPeriodo` = Chiuso, `DataChiusura`, `UtenteChiusura`, `NoteHR` = nota.
2. Risponde all'app.
3. Le richieste del periodo *Validata da HR* passano a **Inclusa nel riepilogo mensile** con `PeriodoChiusura` = `AAAA-MM`.
4. Aggiorna `NumeroRichieste`, `TotaleOreRiconosciute` (somma di `OreRetribuiteHR`) e `TotaleGettoni` (somma di `OreGettoneHR`). Registro.

**riapri**: `StatoPeriodo` = Riaperto, `DataRiapertura`, `UtenteRiapertura`, `MotivoRiapertura`, registro, e-mail a HR.

**`dati`**: `{ "periodo": "2026-10", "stato": "Chiuso", "richiesteIncluse": 0 }`. Il conteggio definitivo si legge poi dalla lista.

---

## 6.11 SDF_API09_FilePaghe

| | |
|---|---|
| Parametri | 1. `anno` · 2. `mese` (numeri) |
| Chi può chiamarlo | HR o Amministratore; il periodo deve essere **Chiuso** |

**Logica**
1. Richieste del periodo con `Stato` = Inclusa nel riepilogo mensile.
2. Codici fiscali: legge *Lavoratori* (tutti) e costruisce una mappa login → CF senza cicli: *Seleziona* che produce `"login":"CF"`, poi `json(concat('{', join(..., ','), '}'))`.
3. CSV con separatore `;`, codifica UTF-8 con BOM (`decodeUriComponent('%EF%BB%BF')`) e righe separate da `decodeUriComponent('%0D%0A')`. Intestazione:
   `Codice fiscale;Cognome;Nome;Area;Servizio;Centro di costo;Mese;Anno;Titolo corso;Data corso;Ore retribuite riconosciute HR;Ore gettone riconosciute HR;ID richiesta`
   - titolo corso = `TitoloCorsoCatalogo`, altrimenti `TitoloCorsoLibero`;
   - data `dd/MM/yyyy`; decimali con la virgola;
   - testi tra doppi apici, con i doppi apici interni raddoppiati.
4. File `Formazione_Payroll_AAAA-MM_v<versione>.csv` nella raccolta **File paghe**, dove versione = `VersioneFile` + 1. Proprietà del file: `Periodo`, `NumeroRichieste`.
5. Risponde all'app con l'URL del file.
6. Ogni richiesta inclusa passa a **Inviata a Payroll**.
7. *Chiusure mensili*: `FilePagheGenerato` = Sì, `FilePagheUrl`, `VersioneFile`, totali.
8. E-mail con il collegamento a `Configurazione.DestinatariPayroll`. Registro.

Senza richieste incluse risponde `ERRORE` con "Nessuna richiesta da inviare per il periodo".
**`dati`**: `{ "url": "https://.../File paghe/Formazione_Payroll_2026-10_v1.csv", "richieste": 152 }`

---

## 6.12 SDF_API10_DettaglioRichiesta

| | |
|---|---|
| Parametri | 1. `id` (numero) |
| Chi può chiamarlo | il lavoratore della richiesta, il suo coordinatore, HR, Amministratore |

**`dati`**
```json
{
  "richiesta": Richiesta,
  "ruoloChiamante": "lavoratore | coordinatore | hr | amministratore",
  "permessi": { "modifica": false, "annulla": true, "esitoCoordinatore": false, "esitoHR": false },
  "meseChiuso": false,
  "storico": [ { "data": "2026-10-15T08:12:00Z", "azione": "Approvazione coordinatore", "campo": "", "valorePrecedente": "", "valoreNuovo": "", "ruolo": "Coordinatore", "autore": "anna.bianchi@..." , "nota": "" } ]
}
```
I permessi seguono la tabella §1.5. `storico` viene restituito solo a HR e Amministratore: per gli altri è una lista vuota. Chiamante non autorizzato → `ERRORE` "Richiesta non trovata o non autorizzata". Il messaggio è lo stesso nei due casi, per non rivelare l'esistenza della richiesta.

---

## 6.13 Flussi automatici (account di servizio)

| Flusso | Dettagli |
|---|---|
| **SDF_F4_Promemoria** | Ricorrenza settimanale lun–ven 08:00, fuso *W. Europe Standard Time*. Se oggi è in `Configurazione.Festivita` termina. Per ogni richiesta *In attesa del coordinatore* incrementa `GiorniAttesa`: a 3 e a 5 manda un promemoria al coordinatore; a 7 o più, se `SegnalataHR` = No, scrive al coordinatore e a HR e imposta `SegnalataHR` = Sì |
| **SDF_F5_RiepilogoMensile** | Ricorrenza mensile, giorno 2 alle 07:00. Prende le richieste del mese precedente, ricava i coordinatori distinti con `union()` e invia a ciascuno una tabella HTML con i totali. Evidenzia aperte (Inviata, In attesa del coordinatore, Integrazione), respinte e incomplete (anomalie o attestato mancante). Invia a HR il quadro completo e i totali per coordinatore |
| **SDF_F7_AllineaLavoratore** | *Quando un elemento viene creato o modificato* su Lavoratori + *Ottieni modifiche per un elemento*. Se manca `Login` lo ricava da `UtenteM365`; se mancano login, nome o e-mail del coordinatore li ricava da `Coordinatore`. Se è cambiato `CoordinatoreLogin`: aggiorna i dati del coordinatore sulle richieste aperte (Bozza, In attesa del coordinatore, Integrazione), sposta i loro allegati nella cartella del nuovo coordinatore (creandola e condividendola se manca), aggiorna gli URL, avvisa il nuovo coordinatore se ci sono richieste in attesa. Una condizione evita i cicli: aggiorna solo se i valori sono diversi |
| **SDF_F9_SincronizzaRuoli** | *Quando un elemento viene creato o modificato* su Ruoli applicativi: con *Invia una richiesta HTTP a SharePoint* esegue `ensureuser`, poi aggiunge o toglie l'utente dal gruppo *Formazione - HR* (`sitegroups/getbyname`) o dai Proprietari (`AssociatedOwnerGroup`), secondo Ruolo e Attivo. *Quando un elemento viene eliminato*: toglie l'utente indicato dal titolo da entrambi i gruppi. Non tocca mai l'account di servizio (`Configurazione.AccountServizio`) |
