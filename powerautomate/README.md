# Flussi Power Automate – Gestione ore formazione

Questa cartella contiene i **15 flussi cloud** della soluzione: 10 flussi **API**, chiamati dall'app Power Apps, e 5 flussi **automatici**. Il contratto tra app e flussi è in [docs/06-api-flussi.md](../docs/06-api-flussi.md); stati, regole R1–R12 e permessi sono in [docs/01-architettura.md](../docs/01-architettura.md).

Vincoli rispettati:
- solo connettori **standard**: SharePoint, Office 365 Outlook, Office 365 Utenti (solo F7) e azioni integrate. Niente Dataverse, niente HTTP premium;
- tutte le connessioni sono dell'**account di servizio** (es. `svc-formazione@societadolce.it`), proprietario del sito;
- l'URL del sito compare solo come segnaposto **`{{SITO_URL}}`**, che `crea_pacchetti.py` sostituisce. Si trova nella variabile `SitoUrl`, prima azione di ogni flusso, e nel trigger dei flussi F7, F9 e F9b. Va scritto senza barra finale, es. `https://societadolce.sharepoint.com/sites/GestioneFormazione`.

## Contenuto

| Percorso | Contenuto |
|---|---|
| `flows/<nome flusso>.json` | Definizione del flusso: `name`, `description`, `connectionReferences`, `definition` (formato Logic Apps 2016-06-01) |
| `crea_pacchetti.py` | Crea i pacchetti di importazione `.zip` (formato *Pacchetto legacy*) in `pacchetti/`, sostituendo `{{SITO_URL}}`: `python powerautomate/crea_pacchetti.py --sito https://<tenant>.sharepoint.com/sites/GestioneFormazione` |
| `verifica_flussi.py` | Controllo statico dei file, da rilanciare dopo ogni modifica (vedi [Verifica dei file](#verifica-dei-file)) |
| `README.md` | Questo documento |

## Elenco dei flussi

| Flusso | Trigger | Connessioni | Azioni | Funzione |
|---|---|---|---|---|
| [SDF_API01_Profilo](#sdf_api01_profilo) | Power Apps (V2) | SharePoint, Office 365 Outlook | 23 | Ruoli e dati del lavoratore che apre l'app |
| [SDF_API02_MieRichieste](#sdf_api02_mierichieste) | Power Apps (V2) | SharePoint, Office 365 Outlook | 18 | Richieste del lavoratore |
| [SDF_API03_SalvaRichiesta](#sdf_api03_salvarichiesta) | Power Apps (V2) | SharePoint, Office 365 Outlook | 137 | Bozza, invio al coordinatore (requisito *Flusso 1*), annullamento |
| [SDF_API04_AggiornaProfilo](#sdf_api04_aggiornaprofilo) | Power Apps (V2) | SharePoint, Office 365 Outlook | 39 | E-mail personale, codice fiscale, segnalazione a HR |
| [SDF_API05_RichiesteTeam](#sdf_api05_richiesteteam) | Power Apps (V2) | SharePoint, Office 365 Outlook | 20 | Richieste e lavoratori del team del coordinatore |
| [SDF_API06_EsitoCoordinatore](#sdf_api06_esitocoordinatore) | Power Apps (V2) | SharePoint, Office 365 Outlook | 58 | Esito del coordinatore (requisito *Flusso 2*) |
| [SDF_API07_EsitoHR](#sdf_api07_esitohr) | Power Apps (V2) | SharePoint, Office 365 Outlook | 60 | Esito HR su una o più richieste (requisito *Flusso 3*) |
| [SDF_API08_ChiusuraMensile](#sdf_api08_chiusuramensile) | Power Apps (V2) | SharePoint, Office 365 Outlook | 53 | Chiusura e riapertura del mese |
| [SDF_API09_FilePaghe](#sdf_api09_filepaghe) | Power Apps (V2) | SharePoint, Office 365 Outlook | 57 | File CSV per l'Ufficio Paghe (requisito *Flusso 6*) |
| [SDF_API10_DettaglioRichiesta](#sdf_api10_dettagliorichiesta) | Power Apps (V2) | SharePoint, Office 365 Outlook | 33 | Dettaglio, permessi e storico di una richiesta |
| [SDF_F4_Promemoria](#sdf_f4_promemoria) | Ricorrenza lun–ven 08:00 | SharePoint, Office 365 Outlook | 28 | Promemoria e solleciti (requisito *Flusso 4*) |
| [SDF_F5_RiepilogoMensile](#sdf_f5_riepilogomensile) | Ricorrenza giorno 2, 07:00 | SharePoint, Office 365 Outlook | 40 | Riepilogo mensile a coordinatori e HR (requisito *Flusso 5*) |
| [SDF_F7_AllineaLavoratore](#sdf_f7_allinealavoratore) | Lavoratori: creato o modificato | SharePoint, Office 365 Outlook, Office 365 Utenti | 51 | Completa i dati; gestisce il cambio di coordinatore |
| [SDF_F9_SincronizzaRuoli](#sdf_f9_sincronizzaruoli) | Ruoli applicativi: creato o modificato | SharePoint, Office 365 Outlook | 29 | Gruppo *Formazione - HR* e Proprietari del sito |
| [SDF_F9b_RuoloEliminato](#sdf_f9b_ruoloeliminato) | Ruoli applicativi: eliminato | SharePoint, Office 365 Outlook | 26 | Toglie dai gruppi chi non ha più ruoli |

F9 è diviso in due file perché un flusso ha un solo trigger. I due flussi insieme sono il "SDF_F9_SincronizzaRuoli" di [docs/06-api-flussi.md](../docs/06-api-flussi.md) §6.13.

---

## Struttura comune

### Inizio di ogni flusso (primo livello)

| Azione | Tipo | Contenuto |
|---|---|---|
| `Inizializza_SitoUrl` | Inizializza variabile (stringa) | `SitoUrl` = `{{SITO_URL}}`. Tutte le azioni SharePoint usano `@variables('SitoUrl')` come *Indirizzo del sito* |
| `Chiamante` (solo API) | Componi | `toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`. È l'**unica identità** di cui il flusso si fida; nessun parametro indica l'utente |
| `Chiamante_OData` (solo API) | Componi | Il chiamante con gli apici raddoppiati, da usare nei filtri OData |
| `Leggi_configurazione` | SharePoint – Ottieni elementi | Lista *Configurazione*, `$top` 500 |
| `Seleziona_configurazione` | Seleziona | Modalità mappa con **chiave calcolata** `@item()?['Title']` e valore `@item()?['Valore']` |
| `Configurazione` | Componi | `json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`. Si usa come `outputs('Configurazione')?['EmailHR']` |
| `Inizializza_<nome>` | Inizializza variabile | Variabili del flusso. Power Automate le accetta solo al primo livello, quindi sono tutte qui |

Chiavi di *Configurazione* usate: `AppUrl`, `EmailHR`, `MittenteEmail`, `DestinatariPayroll`, `AccountServizio`, `Festivita`. La colonna *Valore* è testo semplice (non RTF).

### Ambiti `Prova` ed `Errore`

- **`Prova`** (Ambito) contiene tutta la logica.
- **`Errore`** (Ambito) ha *Configura esecuzione dopo* = `Prova` **non riuscita** o **timeout**. Contiene:
  1. `Rispondi_errore_imprevisto` (solo API): `esito` = `ERRORE`, `messaggio` = "Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.", `dati` = `{}`. Se il flusso aveva già risposto (API07/08/09 rispondono prima di finire) questa azione non riesce: è previsto.
  2. `Link_esecuzione` (eseguita dopo la risposta in **tutti** gli esiti): `concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])`.
  3. `Azioni_non_riuscite` (Filtra matrice su `result('Prova')`, `status` = `Failed`) e `Dettaglio_azioni_non_riuscite` (Seleziona: nome e messaggio).
  4. `Avvisa_HR_errore`: e-mail ad alta importanza a `Configurazione.EmailHR` con nome del flusso, data, chiamante, azioni non riuscite e pulsante **"Apri l'esecuzione"**.
  5. `Termina_con_errore` (Termina, stato *Non riuscito*), così l'esecuzione resta rossa nella cronologia.

La lettura della configurazione è fuori da `Prova`, perché `Errore` deve poterla usare. Se manca la lista *Configurazione* il flusso fallisce senza risposta e Power Apps mostra l'errore generico del connettore.

### Risposte a Power Apps

Ogni flusso API ha una o più azioni **Rispondi a un'app o a un flusso di Power Apps** con lo **stesso** schema: tre output di tipo testo, `esito`, `messaggio`, `dati`. `dati` è sempre `string(<oggetto Componi>)`. Le risposte stanno in rami alternativi: un'esecuzione ne esegue una sola. Nessuna è dentro un ciclo.

Gli errori di validazione seguono sempre lo stesso schema:
1. un'azione **Componi** (`Controllo_accesso`, `Controlli_esito`, `Controlli_HR`, …) calcola il messaggio d'errore con `if()` annidati: stringa vuota = tutto bene. Per più errori insieme si usa `createArray(if(...,'msg',''), ...)`, poi **Filtra matrice** sugli elementi non vuoti e `join(..., ' · ')`;
2. una **Condizione** `Se_<…>` controlla se il messaggio non è vuoto e allora esegue `Rispondi_<…>` (`esito` = `ERRORE`) e `Termina_<…>` (stato *Riuscito*: non è un guasto).

### Registro modifiche

Ogni scrittura crea un elemento in *Registro modifiche* (SharePoint – Crea elemento) con `Title` = azione, `RichiestaRif`, `IdRichiesta`, `Tabella`, `IdRecord`, `Campo`, `ValorePrecedente`, `ValoreNuovo`, `Ruolo` (scelta), `LoginAutore` = chiamante (per i flussi automatici `Configurazione.AccountServizio`) e `Nota`.
- API03 scrive una riga per l'azione e una per ogni campo modificato (`Confronto_campi` → `Campi_modificati` → `Registra_campi_modificati`).
- API06 e API07 scrivono la variazione delle ore riconosciute rispetto alle ore richieste (coordinatore) o a quelle del coordinatore (HR).
- API08 e API09 aggiornano molte richieste insieme: scrivono **una riga riepilogativa** per operazione, con il numero di richieste e i totali, per non raddoppiare le azioni consumate. Lo stato e il *Periodo chiusura* restano comunque sulla richiesta.
- Il codice fiscale non viene **mai** scritto nel registro.

### Letture SharePoint

- Si usano i **titoli** delle liste (*Richieste formazione*, *Lavoratori*, …) e i **nomi interni** delle colonne nei filtri. Le colonne Scelta si scrivono come `item/Stato/Value` e si leggono come `item()?['Stato']?['Value']`.
- Ogni filtro sulle liste grandi parte da una colonna **indicizzata** (`LavoratoreLogin`, `CoordinatoreLogin`, `AnnoCompetenza`, `MeseCompetenza`, `Stato`, `CodiceCorso`, `RichiestaRif`, `ID`). Gli ordinamenti lato server usano solo `ID` o `DataSessione` (indicizzate). API02 ordina per data di modifica dentro il flusso con `sort()`/`reverse()`.
- Per leggere un elemento per ID si usa *Ottieni elementi* con `ID eq <n>` e `$top` 1, non *Ottieni elemento*: se l'ID non esiste il risultato è vuoto, non un errore.
- *Aggiorna elemento* riceve sempre anche le colonne obbligatorie (`Title`; in *Lavoratori* anche `Login`, `Cognome`, `Nome`; in *Chiusure mensili* `Mese` e `Anno`; in *Catalogo corsi* `EnteErogatore`), come richiede la finestra di progettazione.
- Le letture di *Lavoratori* e le azioni che trattano il codice fiscale hanno **input/output protetti** (*Impostazioni → Proteggi input/output*): il CF non compare nella cronologia delle esecuzioni.

### Calcoli senza cicli

| Esigenza | Tecnica | Dove |
|---|---|---|
| Oggetto chiave/valore della configurazione | Seleziona con chiave calcolata + `json(replace(...))` | tutti |
| Somma di una colonna | Seleziona → `xml(json(concat('{"r":{"x":', string(<matrice>), '}}')))` → `xpath(..., 'sum(/r/x/<campo>)')` | API03 (R6), API08, API09, F5 |
| Valori distinti | `union(<matrice>, <matrice>)` | F5 (coordinatori, lavoratori) |
| Mappa login → codice fiscale | Seleziona `"login":"CF"` → `json(concat('{', join(..., ','), '}'))` → `outputs('Mappa_cf')?[login]` | API09 |
| Durate | `"HH:mm"` → minuti `add(mul(int(substring(t,0,2)),60), int(substring(t,3,2)))`; ore = `float(formatNumber(div(float(minuti),60),'0.00','en-US'))` | API03 |
| ID a 6 cifre | `substring(concat('000000', string(ID)), sub(length(concat('000000', string(ID))), 6), 6)` | API03 (`RF-AAAA-000123`, `EXT-000045`) |

### E-mail

Tutte le e-mail usano **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** con *Da (Invia come)* = `Configurazione.MittenteEmail` (vuoto = account di servizio) e lo stesso modello HTML con stili in linea:
- intestazione blu petrolio `#005E7D` con "Gestione ore formazione – Società Dolce";
- titolo e testo introduttivo;
- eventuale riquadro di avviso (giallo `#FFF4CE` o rosso `#FDE7E9`);
- **tabella riepilogativa** (etichetta grigia | valore), con lo stato mostrato come etichetta colorata secondo `colori_stato` di `sharepoint/schema.yaml`;
- riquadro della nota (motivazione, nota del coordinatore o di HR, note del lavoratore);
- pulsante **"Apri la richiesta"** → `concat(Configurazione.AppUrl, '&richiesta=', ID)`. Per le e-mail non legate a una richiesta il pulsante è "Apri l'app", "Apri il file paghe" o "Apri l'esecuzione";
- piè di pagina "Messaggio automatico – non rispondere."

I testi inseriti dagli utenti (note, titoli dei corsi, nomi) passano da `replace(...)` di `&`, `<`, `>` prima di entrare nell'HTML.

Un invio non riuscito non blocca il flusso: e-mail al lavoratore (API06, API07), e-mail al coordinatore in API07, promemoria e solleciti di F4. Un'azione eseguita solo in caso di errore scrive nel registro "E-mail … non riuscita". In F5 i destinatari non raggiunti compaiono in un riquadro rosso nel quadro inviato a HR. Le altre e-mail partono dopo la risposta a Power Apps: se non riescono, interviene l'ambito `Errore` e HR riceve l'avviso.

Destinatari: lavoratore → **`EmailPersonale`** (se è vuota l'e-mail non parte e nel registro viene scritta la riga "E-mail al lavoratore non inviata"); coordinatore → `CoordinatoreEmail`, oppure `CoordinatoreLogin` se manca; HR → `Configurazione.EmailHR`.

| Flusso | Quando | Destinatari | Oggetto |
|---|---|---|---|
| API03 | annullamento di una richiesta già inviata | coordinatore | Richiesta di formazione annullata – RF-… |
| API03 | invio | coordinatore | Richiesta di formazione da approvare – RF-… – Cognome Nome (riquadro rosso se c'è un possibile duplicato confermato) |
| API03 | invio con duplicato confermato | HR | Possibile duplicato – RF-… – Cognome Nome |
| API04 | segnalazione di variazione | HR | Segnalazione variazione dati – Cognome Nome |
| API06 | approva / respingi / integrazione | lavoratore | Richiesta di formazione approvata dal coordinatore · …respinta dal coordinatore · Integrazione richiesta dal coordinatore – RF-… |
| API07 | per ogni richiesta elaborata | lavoratore e coordinatore | Richiesta di formazione validata · …respinta da HR · Integrazione richiesta da HR – RF-… |
| API07 | oltre 25 richieste, a fine elaborazione | chiamante e HR | Esito elaborazione HR – <stato>: N richieste elaborate |
| API08 | riapertura | HR | Riapertura del mese AAAA-MM |
| API09 | file generato | `Configurazione.DestinatariPayroll` | File paghe formazione – <mese> <anno> (versione N) |
| F4 | 3° e 5° giorno lavorativo di attesa | coordinatore | Promemoria: richiesta di formazione in attesa – RF-… |
| F4 | dal 7° giorno, una sola volta | coordinatore, in copia HR (importanza alta) | Sollecito: richiesta di formazione in attesa da N giorni – RF-… |
| F5 | giorno 2 del mese | ogni coordinatore | Riepilogo mensile formazione del tuo gruppo – <mese> <anno> |
| F5 | giorno 2 del mese | HR, con CSV allegato | Quadro mensile della formazione – <mese> <anno> |
| F7 | cambio coordinatore con richieste in attesa | nuovo coordinatore | Richieste di formazione assegnate a te – Cognome Nome |
| tutti | errore imprevisto | HR (importanza alta) | Errore nel flusso <nome> |

---

## Dettaglio dei flussi

Per ogni flusso: scopo, trigger, passaggi principali e, in fondo, l'**elenco completo delle azioni** generato dal file JSON, con nomi, tipi, parametri ed espressioni principali. Serve per ricostruire il flusso a mano se l'importazione non riesce. Le espressioni complete sono nel file JSON: si possono copiare da lì nella finestra di progettazione (*Espressione*).

### SDF_API01_Profilo

**Scopo.** Primo flusso chiamato dall'app: dice chi è l'utente, quali ruoli ha e se il profilo del lavoratore è completo (e-mail personale e codice fiscale).

**Trigger.** **Power Apps (V2)** (`manual`), nessun parametro.

**Passaggi**
1. In parallelo: `Leggi_lavoratore` (*Lavoratori*, `Login eq '<chiamante>'`, top 1); `Leggi_team_coordinatore` (*Lavoratori*, `CoordinatoreLogin eq '<chiamante>' and StatoLavoratore eq 'Attivo'`, top 1); `Leggi_ruoli_chiamante` (*Ruoli applicativi*, `Title eq '<chiamante>' and Attivo eq 1`).
2. `Ruoli_chiamante`: Seleziona i valori di *Ruolo* (es. `["Formazione HR"]`).
3. `Lavoratore` = primo elemento letto; `Lavoratore_attivo` = esiste e *Stato lavoratore* = Attivo.
4. `Oggetto_lavoratore`: i campi del contratto. Del codice fiscale escono solo `cfRegistrato` e `cfMascherato`.
5. `Dati_profilo`: `login`, `nomeVisualizzato` (nome e cognome del lavoratore, altrimenti il nome visualizzato in *Ruoli applicativi*, altrimenti il *CoordinatoreNome* di un lavoratore del team, altrimenti il login), `ruoli`, `profiloCompleto` = lavoratore attivo + e-mail personale + CF registrato, `lavoratore` (null se non censito o non attivo).
6. `Rispondi_profilo`: `OK`.

**E-mail.** Nessuna (solo l'avviso di errore a HR).

<details><summary>Elenco completo delle azioni di SDF_API01_Profilo</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Leggi_lavoratore` — **SharePoint – Ottieni elementi** · lista *Lavoratori* · $filter `Login eq '@{outputs('Chiamante_OData')}'` · $top 1
    <br>*Nota: Elemento Lavoratori del chiamante (Login = chiamante).*
  - `Leggi_team_coordinatore` — **SharePoint – Ottieni elementi** · lista *Lavoratori* · $filter `CoordinatoreLogin eq '@{outputs('Chiamante_OData')}' and StatoLavoratore eq 'Attivo'` · $top 1 — *in parallelo dall'inizio del blocco*
    <br>*Nota: Almeno un lavoratore attivo assegnato al chiamante = ruolo coordinatore.*
  - `Leggi_ruoli_chiamante` — **SharePoint – Ottieni elementi** · lista *Ruoli applicativi* · $filter `Title eq '@{outputs('Chiamante_OData')}' and Attivo eq 1` · $top 10 — *in parallelo dall'inizio del blocco*
    <br>*Nota: Ruoli applicativi attivi del chiamante (Formazione HR / Amministratore).*
  - `Ruoli_chiamante` — **Seleziona** da `@body('Leggi_ruoli_chiamante')?['value']` → `@item()?['Ruolo']?['Value']` — *esegui dopo: Leggi_lavoratore (Succeeded), Leggi_team_coordinatore (Succeeded), Leggi_ruoli_chiamante (Succeeded)*
  - `Lavoratore` — **Componi** `@first(body('Leggi_lavoratore')?['value'])`
  - `Lavoratore_attivo` — **Componi** `@and(not(empty(outputs('Lavoratore'))), equals(outputs('Lavoratore')?['StatoLavoratore']?['Value'], 'Attivo'))`
  - `Oggetto_lavoratore` — **Componi** oggetto con chiavi `id`, `cognome`, `nome`, `emailAziendale`, `emailPersonale`, `cfRegistrato`, `cfMascherato`, `area`, `servizio`, `centroDiCosto`, `strutturaId`, `coordinatoreLogin`, `coordinatoreNome`, `coordinatoreEmail`, `stato`, `segnalazioneAperta`
    <br>*Nota: Dati del lavoratore restituiti all'app (mai il codice fiscale in chiaro).*
  - `Dati_profilo` — **Componi** oggetto con chiavi `login`, `nomeVisualizzato`, `ruoli`, `profiloCompleto`, `lavoratore`
  - `Rispondi_profilo` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `` · dati `@string(outputs('Dati_profilo'))`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API02_MieRichieste

**Scopo.** Restituisce le richieste del lavoratore che chiama.

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | anno | Numero | `number` | Anno di competenza (0 = tutti gli anni) |

**Passaggi**
1. `Leggi_mie_richieste`: *Richieste formazione* con `LavoratoreLogin eq '<chiamante>'` e, se `anno` > 0, `and AnnoCompetenza eq <anno>`. Ordinate per `ID desc`, `$top` 5000.
2. `Mappa_richieste`: Seleziona con la **mappatura dell'oggetto Richiesta** (§6.2 del contratto): stessi nomi JSON, scelte come etichetta, numeri nulli = 0, booleani nulli = false, `dataSessione` come `yyyy-MM-dd`. La stessa mappatura c'è in API05 e API10.
3. `Dati_richieste`: `{ "richieste": reverse(sort(<mappa>, 'modificato')) }`, cioè per ultima modifica decrescente.
4. `Rispondi_richieste`: `OK`.

<details><summary>Elenco completo delle azioni di SDF_API02_MieRichieste</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Leggi_mie_richieste` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `LavoratoreLogin eq '@{outputs('Chiamante_OData')}'@{if(greater(int(triggerBody()?['number']), 0), concat(' and AnnoCompetenza eq ', string(int(triggerBody()?['number']))), '')}` · $orderby `ID desc` · $top 5000
    <br>*Nota: Richieste del chiamante (filtro e ordinamento su colonne indicizzate).*
  - `Mappa_richieste` — **Seleziona** da `@body('Leggi_mie_richieste')?['value']` → oggetto con chiavi `id`, `idRichiesta`, `lavoratoreLogin`, `lavoratoreId`, `cognome`, `nome`, `emailPersonale`, `area`, `servizio`, `centroDiCosto`, `strutturaId`, `coordinatoreLogin`, `coordinatoreNome`, `coordinatoreEmail`, `corsoId`, `codiceCorso`, `titoloCorso`, `titoloCorsoLibero`, `durataCorso`, `enteErogatore`, `modalita`, `piuGiornate`, `dataSessione`, `oraInizioSessione`, `oraFineSessione`, `durataSessione`, `oraIngresso`, `oraUscita`, `oreFrequentate`, `oreRetribuiteRichieste`, `oreGettoneRichieste`, `oreRetribuiteCoord`, `oreGettoneCoord`, `oreRetribuiteHR`, `oreGettoneHR`, `attestatoUrl`, `altraDocUrl`, `attestatoPresente`, `noteLavoratore`, `noteCoordinatore`, `noteHR`, `stato`, `dataInvio`, `dataApprovazioneCoord`, `dataValidazioneHR`, `meseCompetenza`, `annoCompetenza`, `periodoChiusura`, `confermaPartecipazione`, `confermaCorrettezza`, `autorizzazioneInvio`, `possibileDuplicato`, `anomalie`, `giorniAttesa`, `segnalataHR`, `ultimaModificaDa`, `creato`, `modificato`
    <br>*Nota: Oggetto Richiesta del contratto (§6.2).*
  - `Dati_richieste` — **Componi** oggetto con chiavi `richieste`
    <br>*Nota: Ordinate per ultima modifica decrescente (Modified non è indicizzata: si ordina qui).*
  - `Rispondi_richieste` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `` · dati `@string(outputs('Dati_richieste'))`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API03_SalvaRichiesta

**Scopo.** Il lavoratore salva in bozza, invia al coordinatore (requisito *Flusso 1*) o annulla una richiesta. È il flusso più complesso: applica le regole, crea il corso esterno, carica gli allegati, controlla duplicati e somma delle sessioni, scrive il registro e avvisa coordinatore e HR.

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | dati | Testo | `text` | Dati della richiesta in formato JSON (vedi contratto §6.5) |
| 2 | azione | Testo | `text_1` | bozza, invia oppure annulla |
| 3 | attestato | Testo | `text_2` | Attestato come data URI (data:<tipo>;base64,...) oppure "" |
| 4 | nomeAttestato | Testo | `text_3` | Nome del file dell'attestato |
| 5 | altraDoc | Testo | `text_4` | Altra documentazione come data URI oppure "" |
| 6 | nomeAltraDoc | Testo | `text_5` | Nome del file dell'altra documentazione |

**Variabili.** `IdElemento`, `IdRichiestaTesto`, `CorsoIdFinale`, `CodiceCorsoFinale`, `AttestatoUrl`, `AltraDocUrl`.

**Passaggi**
1. **Ingresso.** `Percorso_allegati` = `/AllegatiFormazione` (URL della raccolta *Allegati formazione*; da cambiare qui se il sito usa un altro URL). `Dati` = `json(dati)`, `Azione`, `Id_ingresso`, `Corso_id`.
2. **Letture in parallelo.** Lavoratore chiamante (*Lavoratori*, `Login`), richiesta esistente (`ID eq <id>`: con id 0 non trova nulla), corso (`Catalogo corsi`, `ID eq <corsoId>`) e mesi chiusi (`Chiusure mensili`, `StatoPeriodo eq 'Chiuso'` → `Elenco_mesi_chiusi` = titoli `AAAA-MM`).
3. **`Controllo_accesso`** (tabella §1.5): lavoratore attivo; azione `bozza`/`invia`/`annulla`; con id > 0 la richiesta deve essere del chiamante, altrimenti "Richiesta non trovata o non autorizzata."; stato annullabile per *annulla* (Bozza, In attesa del coordinatore, Integrazione…) o modificabile per bozza/invio (Bozza, Integrazione…); mese di competenza non chiuso. Se fallisce: `Rispondi_accesso_negato` + `Termina_accesso_negato`.
4. **Annulla** (`Se_annulla`): *Stato* = Annullata, registro, risposta `OK` con `{id, idRichiesta, stato, avvisi: []}`. Se lo stato precedente non era Bozza, e-mail al coordinatore. Termina.
5. **Corso.** `Tipo_corso` = `catalogo` (Datore di lavoro + corsoId), `storico` (Committente o altro soggetto + corsoId), `nuovo` (Committente + `nuovoCorso.titolo`) oppure `nessuno`. `Dati_corso` ricava codice, titoli, modalità, durata, più giornate e gettone previsto e lo valida: a catalogo = Datore di lavoro, attivo, *Validato*; storico = `LoginAutore` uguale al chiamante; nuovo = titolo, modalità ammessa, durata > 0. Le variabili `CorsoIdFinale` e `CodiceCorsoFinale` prendono i valori del corso.
6. **Orari e ore** (R1, R2, R12, R5). `Orari` (testo ripulito), `Validita_orari` (formato `HH:mm` 00:00–23:59, controllato carattere per carattere), `Minuti`, `Calcoli_orari` (durata sessione e ore frequentate a 2 decimali, ricalcolate sempre dal flusso). `Data_valida` controlla `AAAA-MM-GG`; `Competenza` = anno, mese e periodo dalla data. `Ore_richieste` arrotonda a 2 decimali e forza a 0 le ore gettone se il corso a catalogo non prevede il gettone (R5, con avviso).
7. **Stesso corso** (R6, R7). `Leggi_richieste_stesso_corso` (*Richieste formazione* con `LavoratoreLogin` e `CodiceCorso`) → `Altre_sessioni` (senza la richiesta stessa, le annullate e le respinte) → `Somma_altre_sessioni` (somma xpath delle durate) → `Duplicati` (stessa data) → `Titoli_duplicati`.
8. **`Elenco_controlli`**, sempre: ente valido, corso valido, data valida, mese non chiuso (R9), formato orari, fine > inizio e uscita > ingresso (R1), ore frequentate ≤ durata sessione (R2), ore non negative e retribuite + gettone ≤ frequentate (R3), allegati in formato data URI. **Solo per l'invio**: R11 (ente, corso, data, quattro orari, ore richieste > 0, tre dichiarazioni, coordinatore assegnato, e-mail personale) e R6 (somma delle sessioni + questa sessione ≤ durata del corso). Gli errori sono uniti con `" · "`: `ERRORE` con `dati = {"errori": [...]}` e fine.
9. **Corso esterno nuovo** (`Se_corso_nuovo`): crea l'elemento in *Catalogo corsi* (Origine = Inserito dal lavoratore, StatoValidazione = Da validare, LoginAutore = chiamante, GettonePrevisto = Sì, CorsoAttivo = Sì), poi assegna `CodiceCorso` = `EXT-` + ID a 6 cifre. Il corso si crea solo dopo che i controlli sono superati.
10. **`Nuovi_valori`**: tutti i campi da scrivere. Login, ID, cognome, nome, e-mail personale, area, servizio, centro di costo, struttura e coordinatore (login, nome, e-mail) arrivano da *Lavoratori*, **mai dal client**. `Stato_salvataggio` = *Inviata al coordinatore* per l'invio, *Bozza* altrimenti.
11. **Salvataggio** (`Se_nuova_richiesta`).
    - Nuova: `Crea_richiesta` (Title provvisorio `RF-in-assegnazione`), poi `Title` = `RF-<anno corrente>-<ID a 6 cifre>` e registro "Creazione richiesta".
    - Esistente: `Aggiorna_richiesta`, registro dell'azione e una riga per ogni campo cambiato (`Confronto_campi`).
12. **Allegati** (`Se_allegati`). Cartella = login del coordinatore con `@` e `.` sostituiti da `_` (`senza_coordinatore` se manca).
    - `Verifica_cartella` (HTTP GET `_api/web/GetFolderByServerRelativeUrl('<percorso>')/Exists`). Se la cartella manca: `Crea_cartella_coordinatore`, poi `Condividi_cartella_coordinatore` (*Concedi l'accesso*: ruolo `role:1073741826` = Può visualizzare, senza e-mail) e registro.
    - Per l'attestato e per l'altra documentazione: *Crea file* `<ID richiesta>_<Attestato|Altra documentazione>_<nome file>` con contenuto `dataUriToBinary(...)`. I caratteri non ammessi nel nome diventano `_`; se il nome manca si usa `documento.<estensione>`. Seguono *Aggiorna proprietà file* (`RichiestaRif`, `IdRichiesta`, `TipoAllegato`, `LavoratoreLogin`), l'URL completo (`SitoUrl` + `Path` del file, codificato) e il registro.
    - `Aggiorna_url_allegati`: `AttestatoUrl`, `AltraDocUrl`, `AttestatoPresente`.
13. **Avvisi** per l'app: gettone azzerato, corso esterno creato, possibile duplicato.
14. **Bozza**: `Rispondi_bozza` (`OK`, "Bozza salvata.").
15. **Invio** (`Se_invio`).
    - Registro "Invio al coordinatore" (stato *Inviata al coordinatore*).
    - **R7.** Se ci sono duplicati e `confermaDuplicato` ≠ true: la richiesta torna in *Bozza*, registro, risposta `ERRORE` "Esiste già una richiesta per lo stesso corso nella stessa data: confermi l'invio?" con `dati = {"richiestaConferma":"duplicato","id":…,"idRichiesta":…,"duplicati":[…]}`. L'app deve richiamare il flusso con lo **stesso `id`** e `confermaDuplicato = true`.
    - Se il duplicato è confermato: *Possibile duplicato* = Sì e nota datata in *Anomalie* su tutte le richieste coinvolte.
    - `Imposta_in_attesa`: *In attesa del coordinatore*, `DataInvio` = adesso, `GiorniAttesa` = 0, `SegnalataHR` = No, `PossibileDuplicato`, `Anomalie`. Registro.
    - `Rispondi_invio` (`OK`), poi e-mail al coordinatore e, se c'è un duplicato, e-mail a HR.

**Risposta.** `dati = { "id": 123, "idRichiesta": "RF-2026-000123", "stato": "...", "avvisi": [...] }`.

<details><summary>Elenco completo delle azioni di SDF_API03_SalvaRichiesta</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Inizializza_IdElemento` — **Inizializza variabile** `IdElemento` (integer) = `0`
- `Inizializza_IdRichiestaTesto` — **Inizializza variabile** `IdRichiestaTesto` (string) = `""`
- `Inizializza_CorsoIdFinale` — **Inizializza variabile** `CorsoIdFinale` (integer) = `0`
- `Inizializza_CodiceCorsoFinale` — **Inizializza variabile** `CodiceCorsoFinale` (string) = `""`
- `Inizializza_AttestatoUrl` — **Inizializza variabile** `AttestatoUrl` (string) = `""`
- `Inizializza_AltraDocUrl` — **Inizializza variabile** `AltraDocUrl` (string) = `""`
- `Prova` — **Ambito**
  - `Percorso_allegati` — **Componi** `/AllegatiFormazione`
    <br>*Nota: Cartella radice della raccolta 'Allegati formazione' (URL relativo al sito).*
  - `Dati` — **Componi** `@json(triggerBody()?['text'])`
    <br>*Nota: JSON inviato dall'app.*
  - `Azione` — **Componi** `@toLower(trim(coalesce(triggerBody()?['text_1'], '')))`
  - `Id_ingresso` — **Componi** `@int(coalesce(outputs('Dati')?['id'], 0))`
  - `Corso_id` — **Componi** `@int(coalesce(outputs('Dati')?['corsoId'], 0))`
  - `Leggi_lavoratore_chiamante` — **SharePoint – Ottieni elementi** · lista *Lavoratori* · $filter `Login eq '@{outputs('Chiamante_OData')}'` · $top 1
  - `Leggi_richiesta_esistente` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `ID eq @{outputs('Id_ingresso')}` · $top 1 — *esegui dopo: Corso_id (Succeeded)*
    <br>*Nota: Con id = 0 non restituisce nulla (nuova richiesta).*
  - `Leggi_corso` — **SharePoint – Ottieni elementi** · lista *Catalogo corsi* · $filter `ID eq @{outputs('Corso_id')}` · $top 1 — *esegui dopo: Corso_id (Succeeded)*
  - `Leggi_mesi_chiusi` — **SharePoint – Ottieni elementi** · lista *Chiusure mensili* · $filter `StatoPeriodo eq 'Chiuso'` · $top 1000 — *esegui dopo: Corso_id (Succeeded)*
  - `Lavoratore` — **Componi** `@first(body('Leggi_lavoratore_chiamante')?['value'])` — *esegui dopo: Leggi_lavoratore_chiamante (Succeeded), Leggi_richiesta_esistente (Succeeded), Leggi_corso (Succeeded), Leggi_mesi_chiusi (Succeeded)*
  - `Richiesta_precedente` — **Componi** `@first(body('Leggi_richiesta_esistente')?['value'])`
  - `Stato_precedente` — **Componi** `@coalesce(outputs('Richiesta_precedente')?['Stato']?['Value'], '')`
  - `Periodo_precedente` — **Componi** `@if(empty(outputs('Richiesta_precedente')?['AnnoCompetenza']), '', concat(string(outputs('Richiesta_precedente')?['AnnoCompetenza']), '-', formatNumber(coalesce(outputs('Richiesta_precedente')?['MeseCompetenza'], 0), '00')))`
  - `Elenco_mesi_chiusi` — **Seleziona** da `@body('Leggi_mesi_chiusi')?['value']` → `@item()?['Title']`
  - `Controllo_accesso` — **Componi** `@if(or(empty(outputs('Lavoratore')), not(equals(outputs('Lavoratore')?['StatoLavoratore']?['Value'], 'Attivo'))), 'Il tuo profilo di lavoratore non risulta attivo: contatta l''Ufficio HR/Formazione.', if(not(contains(createArray('bozza', 'invia', 'annulla'), o …`
    <br>*Nota: Lavoratore attivo, azione valida, proprietà della richiesta, stato e mese (tabella §1.5).*
  - `Se_accesso_negato` — **Condizione** `@not(empty(outputs('Controllo_accesso')))` è vero
    - **Se sì:**
      - `Rispondi_accesso_negato` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{outputs('Controllo_accesso')}` · dati `{}`
      - `Termina_accesso_negato` — **Termina** (stato Succeeded)
  - `Se_annulla` — **Condizione** `@equals(outputs('Azione'), 'annulla')` è vero
    <br>*Nota: Azione "annulla": conta solo l'id.*
    - **Se sì:**
      - `Annulla_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@outputs('Id_ingresso')` · colonne: Title = `@outputs('Richiesta_precedente')?['Title']`, Stato/Value = `Annullata`, UltimaModificaDa = `@outputs('Chiamante')`
      - `Registro_annullamento` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Annullamento richiesta`, RichiestaRif = `@outputs('Id_ingresso')`, IdRichiesta = `@{outputs('Richiesta_precedente')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_ingresso'))}`, Campo = `Stato`, ValorePrecedente = `@{outputs('Stato_precedente')}`, ValoreNuovo = `Annullata`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`
      - `Dati_risposta_annullamento` — **Componi** oggetto con chiavi `id`, `idRichiesta`, `stato`, `avvisi`
      - `Rispondi_annullata` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `Richiesta annullata.` · dati `@string(outputs('Dati_risposta_annullamento'))`
      - `Se_annullata_dopo_invio` — **Condizione** `@and(not(equals(outputs('Stato_precedente'), 'Bozza')), not(empty(coalesce(outputs('Richiesta_precedente')?['CoordinatoreLogin'], ''))))` è vero
        <br>*Nota: Il coordinatore viene avvisato solo se la richiesta gli era già stata inviata.*
        - **Se sì:**
          - `Email_annullamento_coordinatore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{if(empty(outputs('Richiesta_precedente')?['CoordinatoreEmail']), outputs('Richiesta_precedente')?['CoordinatoreLogin'], outputs('Richiesta_precedente')?['Coor …` · oggetto `Richiesta di formazione annullata – @{outputs('Richiesta_precedente')?['Title']}`
      - `Termina_annullata` — **Termina** (stato Succeeded)
  - `Ente` — **Componi** `@trim(string(coalesce(outputs('Dati')?['enteErogatore'], '')))`
  - `Corso` — **Componi** `@first(body('Leggi_corso')?['value'])`
  - `Tipo_corso` — **Componi** `@if(equals(outputs('Ente'), 'Datore di lavoro'), if(greater(outputs('Corso_id'), 0), 'catalogo', 'nessuno'), if(equals(outputs('Ente'), 'Committente o altro soggetto'), if(greater(outputs('Corso_id'), 0), 'storico', if(empty(trim(string(coalesce(outputs('Dati' …`
    <br>*Nota: catalogo | storico | nuovo | nessuno*
  - `Dati_corso` — **Componi** oggetto con chiavi `valido`, `corsoId`, `codiceCorso`, `titoloCatalogo`, `titoloLibero`, `modalita`, `durata`, `piuGiornate`, `gettonePrevisto`, `nomeEnte`
    <br>*Nota: Dati del corso letti dal catalogo o dal nuovo corso esterno.*
  - `Imposta_corso_id` — **Imposta variabile** `CorsoIdFinale` = `@outputs('Dati_corso')?['corsoId']`
  - `Imposta_codice_corso` — **Imposta variabile** `CodiceCorsoFinale` = `@outputs('Dati_corso')?['codiceCorso']`
  - `Orari` — **Componi** oggetto con chiavi `inizio`, `fine`, `ingresso`, `uscita`
  - `Validita_orari` — **Componi** oggetto con chiavi `inizio`, `fine`, `ingresso`, `uscita`
    <br>*Nota: Formato HH:mm (00:00–23:59).*
  - `Minuti` — **Componi** oggetto con chiavi `inizio`, `fine`, `ingresso`, `uscita`
  - `Calcoli_orari` — **Componi** oggetto con chiavi `sessioneValida`, `presenzaValida`, `durataSessione`, `oreFrequentate`
    <br>*Nota: R2: durata sessione = fine − inizio; ore frequentate = uscita − ingresso (2 decimali).*
  - `Data_sessione` — **Componi** `@trim(string(coalesce(outputs('Dati')?['dataSessione'], '')))`
  - `Data_valida` — **Componi** `@and(equals(length(outputs('Data_sessione')), 10), equals(substring(concat(outputs('Data_sessione'), '##########'), 4, 1), '-'), equals(substring(concat(outputs('Data_sessione'), '##########'), 7, 1), '-'), contains('0123456789', substring(concat(outputs('Data …`
  - `Competenza` — **Componi** oggetto con chiavi `anno`, `mese`, `periodo`
    <br>*Nota: R12: mese e anno di competenza dalla data della sessione.*
  - `Ore_richieste` — **Componi** oggetto con chiavi `retribuite`, `gettoneInserite`, `gettone`, `gettoneAzzerato`
    <br>*Nota: R5: corso a catalogo senza gettone previsto -> ore gettone = 0.*
  - `Leggi_richieste_stesso_corso` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `LavoratoreLogin eq '@{outputs('Chiamante_OData')}' and CodiceCorso eq '@{replace(string(outputs('Dati_corso')?['codiceCorso']), '''', '''''')}'` · $top 5000
    <br>*Nota: Altre richieste dello stesso lavoratore sullo stesso codice corso (R6 e R7).*
  - `Altre_sessioni` — **Filtra matrice** da `@body('Leggi_richieste_stesso_corso')?['value']` dove `@and(not(empty(outputs('Dati_corso')?['codiceCorso'])), not(equals(item()?['ID'], outputs('Id_ingresso'))), not(contains(createArray('Annullata', 'Respinta dal coordinatore', 'Respinta da HR'), item()?['Stato']?['Value'])))`
    <br>*Nota: Escluse la richiesta stessa, le annullate e le respinte.*
  - `Durate_altre_sessioni` — **Seleziona** da `@body('Altre_sessioni')` → `@float(coalesce(item()?['DurataSessione'], 0))`
  - `Somma_altre_sessioni` — **Componi** `@xpath(xml(json(concat('{"r":{"x":', string(body('Durate_altre_sessioni')), '}}'))), 'sum(/r/x)')`
    <br>*Nota: Somma senza cicli: JSON -> XML -> xpath sum().*
  - `Duplicati` — **Filtra matrice** da `@body('Altre_sessioni')` dove `@and(outputs('Data_valida'), equals(if(empty(item()?['DataSessione']), null, if(equals(length(string(item()?['DataSessione'])), 10), string(item()?['DataSessione']), convertFromUtc(string(item()?['DataSessione']), 'W. Europe Standard Time', 'yyyy-MM-dd'))), outputs('Data_sessione')))`
    <br>*Nota: R7: stesso lavoratore, stesso codice corso, stessa data.*
  - `Titoli_duplicati` — **Seleziona** da `@body('Duplicati')` → `@item()?['Title']`
  - `Elenco_controlli` — **Componi** `@createArray(if(and(not(empty(outputs('Ente'))), not(contains(createArray('Datore di lavoro', 'Committente o altro soggetto'), outputs('Ente')))), 'Ente erogatore non valido.', ''), if(and(not(equals(outputs('Tipo_corso'), 'nessuno')), not(outputs('Dati_corso' …`
    <br>*Nota: R1, R2, R3, R9 (sempre); R6, R11 (solo invio). Vuoto = superato.*
  - `Errori_validazione` — **Filtra matrice** da `@outputs('Elenco_controlli')` dove `@not(empty(item()))`
  - `Se_errori_validazione` — **Condizione** `@not(empty(join(body('Errori_validazione'), ' · ')))` è vero
    - **Se sì:**
      - `Rispondi_errori_validazione` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{join(body('Errori_validazione'), ' · ')}` · dati `@string(json(concat('{"errori":', string(body('Errori_validazione')), '}')))`
      - `Termina_errori_validazione` — **Termina** (stato Succeeded)
  - `Se_corso_nuovo` — **Condizione** `@equals(outputs('Tipo_corso'), 'nuovo')` è vero
    <br>*Nota: Corso esterno nuovo: creato solo dopo che i controlli sono superati.*
    - **Se sì:**
      - `Crea_corso_esterno` — **SharePoint – Crea elemento** · lista *Catalogo corsi* · colonne: Title = `@outputs('Dati_corso')?['titoloLibero']`, EnteErogatore/Value = `Committente o altro soggetto`, NomeEnte = `@outputs('Dati_corso')?['nomeEnte']`, Modalita/Value = `@outputs('Dati_corso')?['modalita']`, DurataCorso = `@outputs('Dati_corso')?['durata']`, PiuGiornate = `@outputs('Dati_corso')?['piuGiornate']`, GettonePrevisto = `True`, CorsoAttivo = `True`, Origine/Value = `Inserito dal lavoratore`, StatoValidazione/Value = `Da validare`, LoginAutore = `@outputs('Chiamante')`
      - `Imposta_corso_id_nuovo` — **Imposta variabile** `CorsoIdFinale` = `@body('Crea_corso_esterno')?['ID']`
      - `Imposta_codice_corso_nuovo` — **Imposta variabile** `CodiceCorsoFinale` = `@concat('EXT-', substring(concat('000000', string(body('Crea_corso_esterno')?['ID'])), sub(length(concat('000000', string(body('Crea_corso_esterno')?['ID']))), 6), 6))`
      - `Assegna_codice_corso_esterno` — **SharePoint – Aggiorna elemento** · lista *Catalogo corsi* · ID `@body('Crea_corso_esterno')?['ID']` · colonne: Title = `@outputs('Dati_corso')?['titoloLibero']`, EnteErogatore/Value = `Committente o altro soggetto`, CodiceCorso = `@variables('CodiceCorsoFinale')`
      - `Registro_corso_esterno` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Creazione corso esterno`, Tabella = `Catalogo corsi`, IdRecord = `@{string(variables('CorsoIdFinale'))}`, Campo = `CodiceCorso`, ValoreNuovo = `@{variables('CodiceCorsoFinale')}`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{outputs('Dati_corso')?['titoloLibero']}`
  - `Nuovi_valori` — **Componi** oggetto con chiavi `LavoratoreLogin`, `LavoratoreRif`, `Cognome`, `Nome`, `EmailPersonale`, `Area`, `Servizio`, `CentroDiCosto`, `StrutturaRif`, `CoordinatoreLogin`, `CoordinatoreNome`, `CoordinatoreEmail`, `CorsoRif`, `CodiceCorso`, `TitoloCorsoCatalogo`, `TitoloCorsoLibero`, `DurataCorso`, `EnteErogatore`, `NomeEnte`, `Modalita`, `PiuGiornate`, `DataSessione`, `OraInizioSessione`, `OraFineSessione`, `DurataSessione`, `OraIngresso`, `OraUscita`, `OreFrequentate`, `OreRetribuiteRichieste`, `OreGettoneRichieste`, `NoteLavoratore`, `MeseCompetenza`, `AnnoCompetenza`, `ConfermaPartecipazione`, `ConfermaCorrettezza`, `AutorizzazioneInvio`, `AttestatoPresente`, `UltimaModificaDa`
    <br>*Nota: Valori da scrivere: dati organizzativi copiati da Lavoratori, non dal client.*
  - `Stato_salvataggio` — **Componi** `@if(equals(outputs('Azione'), 'invia'), 'Inviata al coordinatore', 'Bozza')`
  - `Se_nuova_richiesta` — **Condizione** `@equals(outputs('Id_ingresso'), 0)` è vero
    <br>*Nota: Nuova: crea e assegna RF-<anno>-<ID a 6 cifre>. Esistente: aggiorna e registra i campi cambiati.*
    - **Se sì:**
      - `Crea_richiesta` — **SharePoint – Crea elemento** · lista *Richieste formazione* · colonne: Title = `RF-in-assegnazione`, LavoratoreLogin = `@outputs('Nuovi_valori')?['LavoratoreLogin']`, LavoratoreRif = `@outputs('Nuovi_valori')?['LavoratoreRif']`, Cognome = `@outputs('Nuovi_valori')?['Cognome']`, Nome = `@outputs('Nuovi_valori')?['Nome']`, EmailPersonale = `@outputs('Nuovi_valori')?['EmailPersonale']`, Area/Value = `@outputs('Nuovi_valori')?['Area']`, Servizio = `@outputs('Nuovi_valori')?['Servizio']`, CentroDiCosto = `@outputs('Nuovi_valori')?['CentroDiCosto']`, StrutturaRif = `@outputs('Nuovi_valori')?['StrutturaRif']`, CoordinatoreLogin = `@outputs('Nuovi_valori')?['CoordinatoreLogin']`, CoordinatoreNome = `@outputs('Nuovi_valori')?['CoordinatoreNome']`, CoordinatoreEmail = `@outputs('Nuovi_valori')?['CoordinatoreEmail']`, CorsoRif = `@outputs('Nuovi_valori')?['CorsoRif']`, CodiceCorso = `@outputs('Nuovi_valori')?['CodiceCorso']`, TitoloCorsoCatalogo = `@outputs('Nuovi_valori')?['TitoloCorsoCatalogo']`, TitoloCorsoLibero = `@outputs('Nuovi_valori')?['TitoloCorsoLibero']`, DurataCorso = `@outputs('Nuovi_valori')?['DurataCorso']`, EnteErogatore/Value = `@outputs('Nuovi_valori')?['EnteErogatore']`, Modalita/Value = `@outputs('Nuovi_valori')?['Modalita']`, PiuGiornate = `@outputs('Nuovi_valori')?['PiuGiornate']`, DataSessione = `@outputs('Nuovi_valori')?['DataSessione']`, OraInizioSessione = `@outputs('Nuovi_valori')?['OraInizioSessione']`, OraFineSessione = `@outputs('Nuovi_valori')?['OraFineSessione']`, DurataSessione = `@outputs('Nuovi_valori')?['DurataSessione']`, OraIngresso = `@outputs('Nuovi_valori')?['OraIngresso']`, OraUscita = `@outputs('Nuovi_valori')?['OraUscita']`, OreFrequentate = `@outputs('Nuovi_valori')?['OreFrequentate']`, OreRetribuiteRichieste = `@outputs('Nuovi_valori')?['OreRetribuiteRichieste']`, OreGettoneRichieste = `@outputs('Nuovi_valori')?['OreGettoneRichieste']`, NoteLavoratore = `@outputs('Nuovi_valori')?['NoteLavoratore']`, MeseCompetenza = `@outputs('Nuovi_valori')?['MeseCompetenza']`, AnnoCompetenza = `@outputs('Nuovi_valori')?['AnnoCompetenza']`, ConfermaPartecipazione = `@outputs('Nuovi_valori')?['ConfermaPartecipazione']`, ConfermaCorrettezza = `@outputs('Nuovi_valori')?['ConfermaCorrettezza']`, AutorizzazioneInvio = `@outputs('Nuovi_valori')?['AutorizzazioneInvio']`, AttestatoPresente = `@outputs('Nuovi_valori')?['AttestatoPresente']`, UltimaModificaDa = `@outputs('Nuovi_valori')?['UltimaModificaDa']`, Stato/Value = `@outputs('Stato_salvataggio')`
      - `Imposta_id_elemento` — **Imposta variabile** `IdElemento` = `@body('Crea_richiesta')?['ID']`
      - `Imposta_id_richiesta` — **Imposta variabile** `IdRichiestaTesto` = `@concat('RF-', formatDateTime(utcNow(), 'yyyy'), '-', substring(concat('000000', string(variables('IdElemento'))), sub(length(concat('000000', string(variables('IdElemento')))), 6), 6))`
      - `Assegna_id_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@variables('IdElemento')` · colonne: Title = `@variables('IdRichiestaTesto')`
      - `Registro_creazione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Creazione richiesta`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Campo = `Stato`, ValoreNuovo = `@outputs('Stato_salvataggio')`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`
    - **Se no:**
      - `Imposta_id_elemento_esistente` — **Imposta variabile** `IdElemento` = `@outputs('Id_ingresso')`
      - `Imposta_id_richiesta_esistente` — **Imposta variabile** `IdRichiestaTesto` = `@outputs('Richiesta_precedente')?['Title']`
      - `Aggiorna_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@variables('IdElemento')` · colonne: Title, LavoratoreLogin, LavoratoreRif, Cognome, Nome, EmailPersonale, Area/Value, Servizio, CentroDiCosto, StrutturaRif, CoordinatoreLogin, CoordinatoreNome, CoordinatoreEmail, CorsoRif, CodiceCorso, TitoloCorsoCatalogo, TitoloCorsoLibero, DurataCorso, EnteErogatore/Value, Modalita/Value, PiuGiornate, DataSessione, OraInizioSessione, OraFineSessione, DurataSessione, OraIngresso, OraUscita, OreFrequentate, OreRetribuiteRichieste, OreGettoneRichieste, NoteLavoratore, MeseCompetenza, AnnoCompetenza, ConfermaPartecipazione, ConfermaCorrettezza, AutorizzazioneInvio, AttestatoPresente, UltimaModificaDa, Stato/Value
      - `Registro_modifica` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `@{if(equals(outputs('Azione'), 'invia'), 'Modifica e invio richiesta', 'Modifica richiesta …`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`
      - `Confronto_campi` — **Componi** matrice
        <br>*Nota: Valori prima/dopo dei campi modificabili.*
      - `Campi_modificati` — **Filtra matrice** da `@outputs('Confronto_campi')` dove `@not(equals(item()?['prima'], item()?['dopo']))`
      - `Registra_campi_modificati` — **Applica a ogni** su `@body('Campi_modificati')` · concorrenza 5
        - `Registro_campo` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Modifica campo`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Campo = `@items('Registra_campi_modificati')?['campo']`, ValorePrecedente = `@items('Registra_campi_modificati')?['prima']`, ValoreNuovo = `@items('Registra_campi_modificati')?['dopo']`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`
  - `Se_allegati` — **Condizione** `@or(not(empty(trim(coalesce(triggerBody()?['text_2'], '')))), not(empty(trim(coalesce(triggerBody()?['text_4'], '')))))` è vero
    <br>*Nota: Allegati nella cartella del coordinatore (creata e condivisa in lettura se manca).*
    - **Se sì:**
      - `Cartella_coordinatore` — **Componi** `@if(empty(outputs('Nuovi_valori')?['CoordinatoreLogin']), 'senza_coordinatore', replace(replace(toLower(trim(outputs('Nuovi_valori')?['CoordinatoreLogin'])), '@', '_'), '.', '_'))`
        <br>*Nota: Login del coordinatore con @ e . sostituiti da _.*
      - `Percorso_cartella` — **Componi** `@concat(outputs('Percorso_allegati'), '/', outputs('Cartella_coordinatore'))`
      - `Verifica_cartella` — **SharePoint – Invia una richiesta HTTP a SharePoint** · GET `_api/web/GetFolderByServerRelativeUrl('@{replace(concat(uriPath(variables('SitoUrl')), outputs('Percorso_cartella')), '''', '''''')}')/Exists`
        <br>*Nota: Restituisce {"value": true} se la cartella del coordinatore esiste già.*
      - `Se_cartella_da_creare` — **Condizione** `@not(equals(body('Verifica_cartella')?['value'], true))` è vero — *esegui dopo: Verifica_cartella (Succeeded, Failed)*
        - **Se sì:**
          - `Crea_cartella_coordinatore` — **SharePoint – Crea nuova cartella** · lista *Allegati formazione* · percorso `@outputs('Cartella_coordinatore')`
          - `Se_coordinatore_da_abilitare` — **Condizione** `@not(empty(outputs('Nuovi_valori')?['CoordinatoreLogin']))` è vero
            - **Se sì:**
              - `Condividi_cartella_coordinatore` — **SharePoint – Concedi l'accesso a un elemento o una cartella** · lista *Allegati formazione* · ID `@body('Crea_cartella_coordinatore')?['ID']` · destinatari `@{if(empty(outputs('Nuovi_valori')?['CoordinatoreEmail']), outputs('Nuovi_valori')?['CoordinatoreLogin'], outputs('Nuovi_valori')?['CoordinatoreEmail' …`, ruolo `role:1073741826` (può visualizzare), notifica: no
                <br>*Nota: Sola lettura per il coordinatore, senza e-mail di notifica.*
          - `Registro_cartella_allegati` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Creazione cartella allegati`, Tabella = `Allegati formazione`, IdRecord = `@{string(body('Crea_cartella_coordinatore')?['ID'])}`, Ruolo/Value = `Sistema`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{concat('Cartella ', outputs('Cartella_coordinatore'), ' condivisa in lettura con ', if(e …`
      - `Se_attestato` — **Condizione** `@not(empty(trim(coalesce(triggerBody()?['text_2'], ''))))` è vero
        - **Se sì:**
          - `Crea_file_attestato` — **SharePoint – Crea file** · cartella `@outputs('Percorso_cartella')`, nome `@concat(variables('IdRichiestaTesto'), '_Attestato_', if(empty(trim(coalesce(triggerBody()?['text_3'], ''))), concat('documento.', last(split(first(split(trim(c …`
            <br>*Nota: Nome file: <ID richiesta>_Attestato_<nome file>.*
          - `Proprieta_file_attestato` — **SharePoint – Aggiorna proprietà file** · lista *Allegati formazione* · ID `@body('Crea_file_attestato')?['ItemId']` · colonne: RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@variables('IdRichiestaTesto')`, TipoAllegato/Value = `Attestato`, LavoratoreLogin = `@outputs('Chiamante')`
          - `Imposta_url_attestato` — **Imposta variabile** `AttestatoUrl` = `@concat(variables('SitoUrl'), replace(uriComponent(body('Crea_file_attestato')?['Path']), '%2F', '/'))`
          - `Registro_attestato` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Caricamento allegato`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Campo = `AttestatoUrl`, ValoreNuovo = `@{variables('AttestatoUrl')}`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`, Nota = `Attestato`
      - `Se_altra_documentazione` — **Condizione** `@not(empty(trim(coalesce(triggerBody()?['text_4'], ''))))` è vero
        - **Se sì:**
          - `Crea_file_altra_documentazione` — **SharePoint – Crea file** · cartella `@outputs('Percorso_cartella')`, nome `@concat(variables('IdRichiestaTesto'), '_Altra documentazione_', if(empty(trim(coalesce(triggerBody()?['text_5'], ''))), concat('documento.', last(split(first(s …`
            <br>*Nota: Nome file: <ID richiesta>_Altra documentazione_<nome file>.*
          - `Proprieta_file_altra_documentazione` — **SharePoint – Aggiorna proprietà file** · lista *Allegati formazione* · ID `@body('Crea_file_altra_documentazione')?['ItemId']` · colonne: RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@variables('IdRichiestaTesto')`, TipoAllegato/Value = `Altra documentazione`, LavoratoreLogin = `@outputs('Chiamante')`
          - `Imposta_url_altra_documentazione` — **Imposta variabile** `AltraDocUrl` = `@concat(variables('SitoUrl'), replace(uriComponent(body('Crea_file_altra_documentazione')?['Path']), '%2F', '/'))`
          - `Registro_altra_documentazione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Caricamento allegato`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Campo = `AltraDocUrl`, ValoreNuovo = `@{variables('AltraDocUrl')}`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`, Nota = `Altra documentazione`
      - `Aggiorna_url_allegati` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@variables('IdElemento')` · colonne: Title = `@variables('IdRichiestaTesto')`, AttestatoUrl = `@if(empty(variables('AttestatoUrl')), coalesce(outputs('Richiesta_precedente')?['Attestato …`, AltraDocUrl = `@if(empty(variables('AltraDocUrl')), coalesce(outputs('Richiesta_precedente')?['AltraDocUr …`, AttestatoPresente = `@not(empty(if(empty(variables('AttestatoUrl')), coalesce(outputs('Richiesta_precedente')?[ …`
  - `Elenco_avvisi` — **Componi** `@createArray(if(outputs('Ore_richieste')?['gettoneAzzerato'], 'Il corso non prevede il gettone: le ore gettone sono state impostate a 0.', ''), if(equals(outputs('Tipo_corso'), 'nuovo'), concat('È stato creato il corso esterno ', variables('CodiceCorsoFinale') …`
  - `Avvisi` — **Filtra matrice** da `@outputs('Elenco_avvisi')` dove `@not(empty(item()))`
  - `Se_invio` — **Condizione** `@equals(outputs('Azione'), 'invia')` è vero
    <br>*Nota: invia: stato transitorio, controllo duplicati (R7), attesa coordinatore, e-mail.*
    - **Se sì:**
      - `Registro_inviata` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Invio al coordinatore`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Campo = `Stato`, ValorePrecedente = `@{outputs('Stato_precedente')}`, ValoreNuovo = `Inviata al coordinatore`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`
      - `Se_duplicato_da_confermare` — **Condizione** `@and(greater(length(body('Duplicati')), 0), not(equals(outputs('Dati')?['confermaDuplicato'], true)))` è vero
        <br>*Nota: R7: senza conferma la richiesta resta in Bozza e l'app chiede conferma (dati.richiestaConferma = "duplicato").*
        - **Se sì:**
          - `Riporta_in_bozza` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@variables('IdElemento')` · colonne: Title = `@variables('IdRichiestaTesto')`, Stato/Value = `Bozza`, UltimaModificaDa = `@outputs('Chiamante')`
          - `Registro_invio_sospeso` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Invio sospeso: possibile duplicato da confermare`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Campo = `Stato`, ValorePrecedente = `Inviata al coordinatore`, ValoreNuovo = `Bozza`, Ruolo/Value = `Sistema`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{concat('Stesso corso e stessa data di: ', join(body('Titoli_duplicati'), ', '))}`
          - `Dati_conferma_duplicato` — **Componi** oggetto con chiavi `richiestaConferma`, `id`, `idRichiesta`, `duplicati`
          - `Rispondi_conferma_duplicato` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Esiste già una richiesta per lo stesso corso nella stessa data: confermi l'invio?` · dati `@string(outputs('Dati_conferma_duplicato'))`
          - `Termina_conferma_duplicato` — **Termina** (stato Succeeded)
      - `Nota_duplicato` — **Componi** `@concat('[', formatDateTime(convertFromUtc(utcNow(), 'W. Europe Standard Time'), 'dd/MM/yyyy'), '] Possibile duplicato (stesso corso e stessa data) di: ', join(body('Titoli_duplicati'), ', '))`
      - `Se_duplicati_confermati` — **Condizione** `@greater(length(body('Duplicati')), 0)` è vero
        <br>*Nota: R7 confermato: Possibile duplicato = Sì su tutte le richieste coinvolte e nota in Anomalie.*
        - **Se sì:**
          - `Segna_richieste_duplicate` — **Applica a ogni** su `@body('Duplicati')` · concorrenza 5
            - `Segna_duplicato` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@items('Segna_richieste_duplicate')?['ID']` · colonne: Title = `@items('Segna_richieste_duplicate')?['Title']`, PossibileDuplicato = `True`, Anomalie = `@concat('[', formatDateTime(convertFromUtc(utcNow(), 'W. Europe Standard Time'), 'dd/MM/yy …`
            - `Registro_duplicato` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Segnalazione possibile duplicato`, RichiestaRif = `@items('Segna_richieste_duplicate')?['ID']`, IdRichiesta = `@{items('Segna_richieste_duplicate')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(items('Segna_richieste_duplicate')?['ID'])}`, Campo = `PossibileDuplicato`, ValoreNuovo = `Sì`, Ruolo/Value = `Sistema`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{concat('Duplicato confermato dal lavoratore con la richiesta ', variables('IdRichiestaTe …`
      - `Imposta_in_attesa` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@variables('IdElemento')` · colonne: Title = `@variables('IdRichiestaTesto')`, Stato/Value = `In attesa del coordinatore`, DataInvio = `@utcNow()`, GiorniAttesa = `0`, SegnalataHR = `False`, PossibileDuplicato = `@greater(length(body('Duplicati')), 0)`, Anomalie = `@if(greater(length(body('Duplicati')), 0), concat(outputs('Nota_duplicato'), if(empty(outp …`, UltimaModificaDa = `@outputs('Chiamante')`
      - `Registro_in_attesa` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `In attesa del coordinatore`, RichiestaRif = `@variables('IdElemento')`, IdRichiesta = `@{variables('IdRichiestaTesto')}`, Tabella = `Richieste formazione`, IdRecord = `@{string(variables('IdElemento'))}`, Campo = `Stato`, ValorePrecedente = `Inviata al coordinatore`, ValoreNuovo = `In attesa del coordinatore`, Ruolo/Value = `Sistema`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{if(greater(length(body('Duplicati')), 0), 'Inviata con possibile duplicato confermato',  …`
      - `Dati_risposta_invio` — **Componi** oggetto con chiavi `id`, `idRichiesta`, `stato`, `avvisi`
      - `Rispondi_invio` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `Richiesta inviata al coordinatore.` · dati `@string(outputs('Dati_risposta_invio'))`
      - `Email_coordinatore_invio` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{if(empty(outputs('Nuovi_valori')?['CoordinatoreEmail']), outputs('Nuovi_valori')?['CoordinatoreLogin'], outputs('Nuovi_valori')?['CoordinatoreEmail'])}` · oggetto `Richiesta di formazione da approvare – @{variables('IdRichiestaTesto')} – @{concat(outputs('Nuovi_valori')?['Cognome'], ' ', outputs('Nuovi_valori')?['Nome'])}`
      - `Se_avvisa_HR_duplicato` — **Condizione** `@greater(length(body('Duplicati')), 0)` è vero
        - **Se sì:**
          - `Email_HR_duplicato` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Possibile duplicato – @{variables('IdRichiestaTesto')} – @{concat(outputs('Nuovi_valori')?['Cognome'], ' ', outputs('Nuovi_valori')?['Nome'])}`
    - **Se no:**
      - `Dati_risposta_bozza` — **Componi** oggetto con chiavi `id`, `idRichiesta`, `stato`, `avvisi`
      - `Rispondi_bozza` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `Bozza salvata.` · dati `@string(outputs('Dati_risposta_bozza'))`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API04_AggiornaProfilo

**Scopo.** Il lavoratore, anche con profilo incompleto, aggiorna e-mail personale e codice fiscale o segnala a HR che i suoi dati organizzativi sono cambiati.

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | emailPersonale | Testo | `text` | E-mail personale per le notifiche ("" = non modificare) |
| 2 | codiceFiscale | Testo | `text_1` | Codice fiscale ("" = non modificare) |
| 3 | segnalazione | Testo | `text_2` | Segnalazione di variazione dei dati a HR ("" = nessuna) |

Per l'e-mail e il codice fiscale `""` significa **non modificare**: un lavoratore che ha già registrato il CF lo vede solo mascherato e non deve reinserirlo.

**Passaggi**
1. `Leggi_lavoratore` (output protetti) → `Lavoratore`.
2. `Valori_profilo`: e-mail ripulita, CF in maiuscolo senza spazi, segnalazione.
3. `Caratteri_cf` / `Caratteri_cf_non_validi`: controllo carattere per carattere (A–Z, 0–9).
4. `Controlli_profilo`: lavoratore censito; e-mail con `@` e `.`, senza spazi; CF di 16 caratteri alfanumerici; segnalazione al massimo di 2000 caratteri. Errori → `ERRORE`.
5. `Nuovi_dati_profilo`: nuovi valori e indicatori di modifica. `CFMascherato` = prime 3 + `**********` + ultime 3; segnalazione = `"[gg/MM/aaaa] testo"` in testa al testo precedente.
6. `Se_profilo_da_aggiornare` → `Aggiorna_lavoratore` (input e output protetti): e-mail, `CodiceFiscale`, `CFMascherato`, `CFRegistrato` = Sì, `SegnalazioneVariazione`, `SegnalazioneAperta` = Sì.
7. Se l'e-mail è cambiata: registro, poi aggiornamento di `EmailPersonale` sulle richieste del lavoratore in Bozza o in integrazione.
8. Se il CF è cambiato: registro "Codice fiscale aggiornato" **senza valori**.
9. `Rispondi_profilo_aggiornato` (`OK`, `{emailPersonale, cfRegistrato, cfMascherato, segnalazioneAperta}`).
10. Se c'è una segnalazione: registro ed e-mail a HR con i dati organizzativi attuali e il testo.

<details><summary>Elenco completo delle azioni di SDF_API04_AggiornaProfilo</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Leggi_lavoratore` — **SharePoint – Ottieni elementi** · lista *Lavoratori* · $filter `Login eq '@{outputs('Chiamante_OData')}'` · $top 1
  - `Lavoratore` — **Componi** `@first(body('Leggi_lavoratore')?['value'])`
  - `Valori_profilo` — **Componi** oggetto con chiavi `email`, `cf`, `segnalazione`
  - `Caratteri_cf` — **Seleziona** da `@range(0, max(length(outputs('Valori_profilo')?['cf']), 1))` → `@contains('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', substring(concat(outputs('Valori_profilo')?['cf'], '#'), item(), 1))`
    <br>*Nota: Verifica carattere per carattere che il codice fiscale sia alfanumerico.*
  - `Caratteri_cf_non_validi` — **Filtra matrice** da `@body('Caratteri_cf')` dove `@equals(item(), false)`
  - `Controlli_profilo` — **Componi** `@createArray(if(empty(outputs('Lavoratore')), 'Utente non censito: contatta l''Ufficio HR/Formazione.', ''), if(and(not(empty(outputs('Valori_profilo')?['email'])), or(not(contains(outputs('Valori_profilo')?['email'], '@')), not(contains(outputs('Valori_profil …`
  - `Errori_profilo` — **Filtra matrice** da `@outputs('Controlli_profilo')` dove `@not(empty(item()))`
  - `Se_errori_profilo` — **Condizione** `@not(empty(join(body('Errori_profilo'), ' · ')))` è vero
    - **Se sì:**
      - `Rispondi_errori_profilo` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{join(body('Errori_profilo'), ' · ')}` · dati `@string(json(concat('{"errori":', string(body('Errori_profilo')), '}')))`
      - `Termina_errori_profilo` — **Termina** (stato Succeeded)
  - `Nuovi_dati_profilo` — **Componi** oggetto con chiavi `email`, `emailCambiata`, `cf`, `cfCambiato`, `cfMascherato`, `cfRegistrato`, `segnalazione`, `segnalazioneAperta`
  - `Se_profilo_da_aggiornare` — **Condizione** `@or(outputs('Nuovi_dati_profilo')?['emailCambiata'], outputs('Nuovi_dati_profilo')?['cfCambiato'], not(empty(outputs('Valori_profilo')?['segnalazione'])))` è vero
    <br>*Nota: Scrive solo se qualcosa è cambiato.*
    - **Se sì:**
      - `Aggiorna_lavoratore` — **SharePoint – Aggiorna elemento** · lista *Lavoratori* · ID `@outputs('Lavoratore')?['ID']` · colonne: Title = `@outputs('Lavoratore')?['Title']`, Login = `@outputs('Lavoratore')?['Login']`, Cognome = `@outputs('Lavoratore')?['Cognome']`, Nome = `@outputs('Lavoratore')?['Nome']`, EmailPersonale = `@outputs('Nuovi_dati_profilo')?['email']`, CodiceFiscale = `@outputs('Nuovi_dati_profilo')?['cf']`, CFMascherato = `@outputs('Nuovi_dati_profilo')?['cfMascherato']`, CFRegistrato = `@outputs('Nuovi_dati_profilo')?['cfRegistrato']`, SegnalazioneVariazione = `@outputs('Nuovi_dati_profilo')?['segnalazione']`, SegnalazioneAperta = `@outputs('Nuovi_dati_profilo')?['segnalazioneAperta']`
        <br>*Nota: Aggiorna solo la lista Lavoratori (il CF in chiaro resta solo qui).*
  - `Se_email_cambiata` — **Condizione** `@outputs('Nuovi_dati_profilo')?['emailCambiata']` è vero
    - **Se sì:**
      - `Registro_email_personale` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Aggiornamento e-mail personale`, Tabella = `Lavoratori`, IdRecord = `@{string(outputs('Lavoratore')?['ID'])}`, Campo = `EmailPersonale`, ValorePrecedente = `@{coalesce(outputs('Lavoratore')?['EmailPersonale'], '')}`, ValoreNuovo = `@{outputs('Nuovi_dati_profilo')?['email']}`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`
      - `Leggi_richieste_modificabili` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `LavoratoreLogin eq '@{outputs('Chiamante_OData')}' and (Stato eq 'Bozza' or Stato eq 'Integrazione richiesta dal coordinatore' or Stato eq 'Integrazione richiesta da HR')` · $top 5000
        <br>*Nota: Richieste ancora in Bozza o in integrazione: ricevono la nuova e-mail.*
      - `Per_ogni_richiesta_modificabile` — **Applica a ogni** su `@body('Leggi_richieste_modificabili')?['value']` · concorrenza 5
        - `Aggiorna_email_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@items('Per_ogni_richiesta_modificabile')?['ID']` · colonne: Title = `@items('Per_ogni_richiesta_modificabile')?['Title']`, EmailPersonale = `@outputs('Nuovi_dati_profilo')?['email']`
  - `Se_cf_cambiato` — **Condizione** `@outputs('Nuovi_dati_profilo')?['cfCambiato']` è vero
    <br>*Nota: Nel registro il codice fiscale non viene mai scritto.*
    - **Se sì:**
      - `Registro_codice_fiscale` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Codice fiscale aggiornato`, Tabella = `Lavoratori`, IdRecord = `@{string(outputs('Lavoratore')?['ID'])}`, Campo = `CodiceFiscale`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`, Nota = `Il valore non viene registrato per riservatezza.`
  - `Dati_risposta_profilo` — **Componi** oggetto con chiavi `emailPersonale`, `cfRegistrato`, `cfMascherato`, `segnalazioneAperta`
  - `Rispondi_profilo_aggiornato` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `Profilo aggiornato.` · dati `@string(outputs('Dati_risposta_profilo'))`
  - `Se_segnalazione` — **Condizione** `@not(empty(outputs('Valori_profilo')?['segnalazione']))` è vero
    - **Se sì:**
      - `Registro_segnalazione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Segnalazione variazione dati`, Tabella = `Lavoratori`, IdRecord = `@{string(outputs('Lavoratore')?['ID'])}`, Campo = `SegnalazioneVariazione`, ValoreNuovo = `@{outputs('Valori_profilo')?['segnalazione']}`, Ruolo/Value = `Lavoratore`, LoginAutore = `@outputs('Chiamante')`
      - `Email_segnalazione_HR` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Segnalazione variazione dati – @{concat(outputs('Lavoratore')?['Cognome'], ' ', outputs('Lavoratore')?['Nome'])}`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API05_RichiesteTeam

**Scopo.** Richieste e lavoratori del team del coordinatore che chiama.

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | anno | Numero | `number` | Anno di competenza |
| 2 | mese | Numero | `number_1` | Mese di competenza (0 = tutti) |

**Passaggi**
1. In parallelo:
   - `Leggi_richieste_team`: `CoordinatoreLogin eq '<chiamante>' and AnnoCompetenza eq <anno>`, più `and MeseCompetenza eq <mese>` se mese > 0, `and Stato ne 'Bozza'`. Ordinate per `DataSessione desc`;
   - `Leggi_lavoratori_team`: `CoordinatoreLogin eq '<chiamante>'`.
2. `Mappa_richieste` (oggetto Richiesta) e `Mappa_lavoratori` (`id`, `login`, `nominativo` "Cognome Nome", `servizio`, `centroDiCosto`, `stato`).
3. `Rispondi_team`: `OK`.

Se chi chiama non è coordinatore riceve due elenchi vuoti. Gli allegati si aprono con l'URL della richiesta: il coordinatore ha accesso in lettura alla sua cartella.

<details><summary>Elenco completo delle azioni di SDF_API05_RichiesteTeam</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Leggi_richieste_team` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `CoordinatoreLogin eq '@{outputs('Chiamante_OData')}' and AnnoCompetenza eq @{string(int(triggerBody()?['number']))}@{if(greater(int(triggerBody()?['number_1']), 0), concat(' and MeseCompetenza eq ', string(int(triggerBody()?['number_1']))), '')} and Stato ne 'Bozza'` · $orderby `DataSessione desc` · $top 5000
    <br>*Nota: Richieste del team del chiamante, escluse le bozze.*
  - `Leggi_lavoratori_team` — **SharePoint – Ottieni elementi** · lista *Lavoratori* · $filter `CoordinatoreLogin eq '@{outputs('Chiamante_OData')}'` · $top 5000 — *in parallelo dall'inizio del blocco*
    <br>*Nota: Tutti i lavoratori assegnati al chiamante.*
  - `Mappa_richieste` — **Seleziona** da `@body('Leggi_richieste_team')?['value']` → oggetto con chiavi `id`, `idRichiesta`, `lavoratoreLogin`, `lavoratoreId`, `cognome`, `nome`, `emailPersonale`, `area`, `servizio`, `centroDiCosto`, `strutturaId`, `coordinatoreLogin`, `coordinatoreNome`, `coordinatoreEmail`, `corsoId`, `codiceCorso`, `titoloCorso`, `titoloCorsoLibero`, `durataCorso`, `enteErogatore`, `modalita`, `piuGiornate`, `dataSessione`, `oraInizioSessione`, `oraFineSessione`, `durataSessione`, `oraIngresso`, `oraUscita`, `oreFrequentate`, `oreRetribuiteRichieste`, `oreGettoneRichieste`, `oreRetribuiteCoord`, `oreGettoneCoord`, `oreRetribuiteHR`, `oreGettoneHR`, `attestatoUrl`, `altraDocUrl`, `attestatoPresente`, `noteLavoratore`, `noteCoordinatore`, `noteHR`, `stato`, `dataInvio`, `dataApprovazioneCoord`, `dataValidazioneHR`, `meseCompetenza`, `annoCompetenza`, `periodoChiusura`, `confermaPartecipazione`, `confermaCorrettezza`, `autorizzazioneInvio`, `possibileDuplicato`, `anomalie`, `giorniAttesa`, `segnalataHR`, `ultimaModificaDa`, `creato`, `modificato` — *esegui dopo: Leggi_richieste_team (Succeeded), Leggi_lavoratori_team (Succeeded)*
  - `Mappa_lavoratori` — **Seleziona** da `@body('Leggi_lavoratori_team')?['value']` → oggetto con chiavi `id`, `login`, `nominativo`, `servizio`, `centroDiCosto`, `stato`
  - `Dati_team` — **Componi** oggetto con chiavi `richieste`, `lavoratori`
  - `Rispondi_team` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `` · dati `@string(outputs('Dati_team'))`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API06_EsitoCoordinatore

**Scopo.** Il coordinatore approva, respinge o chiede un'integrazione (requisito *Flusso 2*).

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | id | Numero | `number` | ID dell'elemento Richieste formazione |
| 2 | azione | Testo | `text` | approva, respingi oppure integrazione |
| 3 | oreRetribuite | Numero | `number_1` | Ore retribuite riconosciute dal coordinatore |
| 4 | oreGettone | Numero | `number_2` | Ore gettone riconosciute dal coordinatore |
| 5 | nota | Testo | `text_1` | Nota o motivazione (obbligatoria per respingi e integrazione) |

**Passaggi**
1. `Ore_riconosciute` (arrotondate a 2 decimali), `Leggi_richiesta` (`ID eq <id>`), `Periodo_richiesta`, `Leggi_mese_chiuso`.
2. `Controlli_esito`:
   - il chiamante è `CoordinatoreLogin` e **non** è il lavoratore (altrimenti "Richiesta non trovata o non autorizzata.");
   - azione valida;
   - stato *In attesa del coordinatore*;
   - mese non chiuso (R9);
   - nota obbligatoria per respingi e integrazione;
   - per approva, R4: ore ≥ 0 e retribuite + gettone ≤ ore frequentate.
3. `Esegui_azione` (Switch):
   - **approva**: `OreRetribuiteCoord`, `OreGettoneCoord`, `NoteCoordinatore`, `DataApprovazioneCoord` = adesso, *Approvata dal coordinatore*, registro, variazioni delle ore rispetto alle richieste (una riga per campo cambiato), poi *In attesa di validazione HR* e registro. Risposta `OK` `{id, stato}` ed e-mail al lavoratore con le ore riconosciute;
   - **respingi**: *Respinta dal coordinatore*, `NoteCoordinatore` = motivazione, registro, risposta, e-mail al lavoratore con la motivazione;
   - **integrazione**: *Integrazione richiesta dal coordinatore*, `NoteCoordinatore` = nota, registro, risposta, e-mail al lavoratore con il collegamento per correggere.

<details><summary>Elenco completo delle azioni di SDF_API06_EsitoCoordinatore</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Id_richiesta` — **Componi** `@int(triggerBody()?['number'])`
  - `Azione` — **Componi** `@toLower(trim(coalesce(triggerBody()?['text'], '')))`
  - `Nota` — **Componi** `@trim(coalesce(triggerBody()?['text_1'], ''))`
  - `Ore_riconosciute` — **Componi** oggetto con chiavi `retribuite`, `gettone`
  - `Leggi_richiesta` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `ID eq @{outputs('Id_richiesta')}` · $top 1
  - `Richiesta` — **Componi** `@first(body('Leggi_richiesta')?['value'])`
  - `Periodo_richiesta` — **Componi** `@if(empty(outputs('Richiesta')?['AnnoCompetenza']), '', concat(string(outputs('Richiesta')?['AnnoCompetenza']), '-', formatNumber(coalesce(outputs('Richiesta')?['MeseCompetenza'], 0), '00')))`
  - `Leggi_mese_chiuso` — **SharePoint – Ottieni elementi** · lista *Chiusure mensili* · $filter `Title eq '@{outputs('Periodo_richiesta')}' and StatoPeriodo eq 'Chiuso'` · $top 1
  - `Mese_chiuso` — **Componi** `@not(empty(body('Leggi_mese_chiuso')?['value']))`
  - `Controlli_esito` — **Componi** `@if(or(empty(outputs('Richiesta')), not(equals(toLower(coalesce(outputs('Richiesta')?['CoordinatoreLogin'], '')), outputs('Chiamante'))), equals(toLower(coalesce(outputs('Richiesta')?['LavoratoreLogin'], '')), outputs('Chiamante'))), 'Richiesta non trovata o n …`
    <br>*Nota: Chiamante = coordinatore e ≠ lavoratore, stato, mese non chiuso, nota, R4.*
  - `Se_controlli_non_superati` — **Condizione** `@not(empty(outputs('Controlli_esito')))` è vero
    - **Se sì:**
      - `Rispondi_controlli_non_superati` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{outputs('Controlli_esito')}` · dati `{}`
      - `Termina_controlli_non_superati` — **Termina** (stato Succeeded)
  - `Esegui_azione` — **Switch** su `@outputs('Azione')`
    - **Caso `approva`:**
      - `Approva_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@outputs('Id_richiesta')` · colonne: Title = `@outputs('Richiesta')?['Title']`, OreRetribuiteCoord = `@outputs('Ore_riconosciute')?['retribuite']`, OreGettoneCoord = `@outputs('Ore_riconosciute')?['gettone']`, NoteCoordinatore = `@outputs('Nota')`, DataApprovazioneCoord = `@utcNow()`, Stato/Value = `Approvata dal coordinatore`, UltimaModificaDa = `@outputs('Chiamante')`
      - `Registro_approvazione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Approvazione coordinatore`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Campo = `Stato`, ValorePrecedente = `In attesa del coordinatore`, ValoreNuovo = `Approvata dal coordinatore`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{outputs('Nota')}`
      - `Variazioni_ore_coordinatore` — **Componi** matrice
        <br>*Nota: Ore riconosciute rispetto alle ore richieste dal lavoratore.*
      - `Variazioni_ore_effettive` — **Filtra matrice** da `@outputs('Variazioni_ore_coordinatore')` dove `@not(equals(item()?['prima'], item()?['dopo']))`
      - `Registra_variazioni_ore` — **Applica a ogni** su `@body('Variazioni_ore_effettive')` · concorrenza predefinita
        - `Registro_variazione_ore` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Variazione ore riconosciute dal coordinatore`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Campo = `@items('Registra_variazioni_ore')?['campo']`, ValorePrecedente = `@items('Registra_variazioni_ore')?['prima']`, ValoreNuovo = `@items('Registra_variazioni_ore')?['dopo']`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `Valore precedente = ore richieste dal lavoratore`
      - `Passa_a_validazione_HR` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@outputs('Id_richiesta')` · colonne: Title = `@outputs('Richiesta')?['Title']`, Stato/Value = `In attesa di validazione HR`
      - `Registro_attesa_HR` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `In attesa di validazione HR`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Campo = `Stato`, ValorePrecedente = `Approvata dal coordinatore`, ValoreNuovo = `In attesa di validazione HR`, Ruolo/Value = `Sistema`, LoginAutore = `@outputs('Chiamante')`
      - `Dati_risposta_approvata` — **Componi** oggetto con chiavi `id`, `stato`
      - `Rispondi_approvata` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `Richiesta approvata: ora è in attesa di validazione da parte dell'Ufficio HR/Formazione.` · dati `@string(outputs('Dati_risposta_approvata'))`
      - `Se_email_lavoratore_approvata` — **Condizione** `@not(empty(trim(coalesce(outputs('Richiesta')?['EmailPersonale'], ''))))` è vero
        - **Se sì:**
          - `Email_lavoratore_approvata` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Richiesta')?['EmailPersonale']}` · oggetto `Richiesta di formazione approvata dal coordinatore – @{outputs('Richiesta')?['Title']}`
          - `Registro_email_non_riuscita_approvata` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non riuscita`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `Invio non riuscito a @{outputs('Richiesta')?['EmailPersonale']}: notifica «Richiesta di fo …` — *esegui dopo: Email_lavoratore_approvata (Failed, TimedOut)*
        - **Se no:**
          - `Registro_email_mancante_approvata` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non inviata`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `E-mail personale mancante: notifica «Richiesta di formazione approvata dal coordinatore –  …`
    - **Caso `respingi`:**
      - `Respingi_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@outputs('Id_richiesta')` · colonne: Title = `@outputs('Richiesta')?['Title']`, Stato/Value = `Respinta dal coordinatore`, NoteCoordinatore = `@outputs('Nota')`, UltimaModificaDa = `@outputs('Chiamante')`
      - `Registro_respinta` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Respinta dal coordinatore`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Campo = `Stato`, ValorePrecedente = `In attesa del coordinatore`, ValoreNuovo = `Respinta dal coordinatore`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{outputs('Nota')}`
      - `Dati_risposta_respinta` — **Componi** oggetto con chiavi `id`, `stato`
      - `Rispondi_respinta` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `Richiesta respinta.` · dati `@string(outputs('Dati_risposta_respinta'))`
      - `Se_email_lavoratore_respinta` — **Condizione** `@not(empty(trim(coalesce(outputs('Richiesta')?['EmailPersonale'], ''))))` è vero
        - **Se sì:**
          - `Email_lavoratore_respinta` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Richiesta')?['EmailPersonale']}` · oggetto `Richiesta di formazione respinta dal coordinatore – @{outputs('Richiesta')?['Title']}`
          - `Registro_email_non_riuscita_respinta` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non riuscita`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `Invio non riuscito a @{outputs('Richiesta')?['EmailPersonale']}: notifica «Richiesta di fo …` — *esegui dopo: Email_lavoratore_respinta (Failed, TimedOut)*
        - **Se no:**
          - `Registro_email_mancante_respinta` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non inviata`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `E-mail personale mancante: notifica «Richiesta di formazione respinta dal coordinatore – @ …`
    - **Caso `integrazione`:**
      - `Chiedi_integrazione` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@outputs('Id_richiesta')` · colonne: Title = `@outputs('Richiesta')?['Title']`, Stato/Value = `Integrazione richiesta dal coordinatore`, NoteCoordinatore = `@outputs('Nota')`, UltimaModificaDa = `@outputs('Chiamante')`
      - `Registro_integrazione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Integrazione richiesta dal coordinatore`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Campo = `Stato`, ValorePrecedente = `In attesa del coordinatore`, ValoreNuovo = `Integrazione richiesta dal coordinatore`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{outputs('Nota')}`
      - `Dati_risposta_integrazione` — **Componi** oggetto con chiavi `id`, `stato`
      - `Rispondi_integrazione` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `Integrazione richiesta al lavoratore.` · dati `@string(outputs('Dati_risposta_integrazione'))`
      - `Se_email_lavoratore_integrazione` — **Condizione** `@not(empty(trim(coalesce(outputs('Richiesta')?['EmailPersonale'], ''))))` è vero
        - **Se sì:**
          - `Email_lavoratore_integrazione` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Richiesta')?['EmailPersonale']}` · oggetto `Integrazione richiesta dal coordinatore – @{outputs('Richiesta')?['Title']}`
          - `Registro_email_non_riuscita_integrazione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non riuscita`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `Invio non riuscito a @{outputs('Richiesta')?['EmailPersonale']}: notifica «Integrazione ri …` — *esegui dopo: Email_lavoratore_integrazione (Failed, TimedOut)*
        - **Se no:**
          - `Registro_email_mancante_integrazione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non inviata`, RichiestaRif = `@outputs('Id_richiesta')`, IdRichiesta = `@{outputs('Richiesta')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_richiesta'))}`, Ruolo/Value = `Coordinatore`, LoginAutore = `@outputs('Chiamante')`, Nota = `E-mail personale mancante: notifica «Integrazione richiesta dal coordinatore – @{outputs(' …`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API07_EsitoHR

**Scopo.** HR o Amministratore valida, respinge o chiede un'integrazione su una richiesta o su un intero perimetro (requisito *Flusso 3*).

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | dati | Testo | `text` | JSON: {"azione":"valida\|respingi\|integrazione","nota":"","richieste":[{"id":123,"oreRetribuite":-1,"oreGettone":-1}]} |

**Variabili.** `Elaborate` (matrice di ID), `Scartate` (matrice di `{id, idRichiesta, motivo}`).

**Passaggi**
1. `Dati`, `Azione`, `Nota`, `Richieste_da_elaborare`. In parallelo: ruoli del chiamante e mesi chiusi.
2. `Controlli_HR`: ruolo *Formazione HR* o *Amministratore*, azione valida, nota obbligatoria per respingi/integrazione, almeno una richiesta.
3. `Testi_esito`: stato di arrivo, colore, voce del registro, oggetto e testi delle e-mail secondo l'azione.
4. Se le richieste sono **più di 25**: risponde subito `OK` "Elaborazione avviata per N richieste: riceverai un'e-mail con l'esito." (limite di 120 secondi di Power Apps).
5. `Per_ogni_richiesta` (concorrenza 10):
   1. lettura per ID;
   2. `Ore_HR`: `-1` = ore del coordinatore;
   3. `Motivo_scarto`: richiesta non trovata, stato diverso da *In attesa di validazione HR*, lavoratore = chiamante, mese chiuso, ore negative, R4. Se c'è un motivo la richiesta va in `Scartate`;
   4. altrimenti `Aggiorna_esito_HR`. Per *valida*: `OreRetribuiteHR`, `OreGettoneHR`, `DataValidazioneHR`. Per tutte le azioni: stato e `NoteHR` (se la nota è vuota resta quella precedente). Seguono registro, variazioni delle ore rispetto al coordinatore (solo *valida*), e-mail al lavoratore e al coordinatore, `Elaborate`.
6. Fino a 25 richieste: `Rispondi_esito_HR`, `OK` con `{elaborate, scartate}`. Se tutte sono scartate risponde `ERRORE` con i motivi. Oltre 25: e-mail di riepilogo al chiamante e a HR.

<details><summary>Elenco completo delle azioni di SDF_API07_EsitoHR</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Inizializza_Elaborate` — **Inizializza variabile** `Elaborate` (array) = `[]`
- `Inizializza_Scartate` — **Inizializza variabile** `Scartate` (array) = `[]`
- `Prova` — **Ambito**
  - `Dati` — **Componi** `@json(triggerBody()?['text'])`
  - `Azione` — **Componi** `@toLower(trim(string(coalesce(outputs('Dati')?['azione'], ''))))`
  - `Nota` — **Componi** `@trim(string(coalesce(outputs('Dati')?['nota'], '')))`
  - `Richieste_da_elaborare` — **Componi** `@coalesce(outputs('Dati')?['richieste'], json('[]'))`
  - `Leggi_ruoli_chiamante` — **SharePoint – Ottieni elementi** · lista *Ruoli applicativi* · $filter `Title eq '@{outputs('Chiamante_OData')}' and Attivo eq 1` · $top 10
    <br>*Nota: Ruoli applicativi attivi del chiamante.*
  - `Leggi_mesi_chiusi` — **SharePoint – Ottieni elementi** · lista *Chiusure mensili* · $filter `StatoPeriodo eq 'Chiuso'` · $top 1000 — *esegui dopo: Richieste_da_elaborare (Succeeded)*
  - `Ruoli_chiamante` — **Seleziona** da `@body('Leggi_ruoli_chiamante')?['value']` → `@item()?['Ruolo']?['Value']` — *esegui dopo: Leggi_ruoli_chiamante (Succeeded), Leggi_mesi_chiusi (Succeeded)*
  - `Elenco_mesi_chiusi` — **Seleziona** da `@body('Leggi_mesi_chiusi')?['value']` → `@item()?['Title']`
  - `Ruolo_registro` — **Componi** `@if(contains(body('Ruoli_chiamante'), 'Formazione HR'), 'Formazione HR', 'Amministratore')`
  - `Controlli_HR` — **Componi** `@if(not(or(contains(body('Ruoli_chiamante'), 'Formazione HR'), contains(body('Ruoli_chiamante'), 'Amministratore'))), 'Operazione riservata all''Ufficio HR/Formazione e agli amministratori.', if(not(contains(createArray('valida', 'respingi', 'integrazione'), o …`
  - `Se_controlli_HR_non_superati` — **Condizione** `@not(empty(outputs('Controlli_HR')))` è vero
    - **Se sì:**
      - `Rispondi_controlli_HR_non_superati` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{outputs('Controlli_HR')}` · dati `{}`
      - `Termina_controlli_HR_non_superati` — **Termina** (stato Succeeded)
  - `Testi_esito` — **Componi** oggetto con chiavi `stato`, `colore`, `azioneRegistro`, `oggetto`, `titoloLavoratore`, `introLavoratore`, `titoloCoordinatore`, `introCoordinatore`, `notaTitolo`
    <br>*Nota: Testi e stato di arrivo secondo l'azione.*
  - `Se_elaborazione_lunga` — **Condizione** `@greater(length(outputs('Richieste_da_elaborare')), 25)` è vero
    <br>*Nota: Oltre 25 richieste: risponde subito (limite di 120 secondi di Power Apps) e prosegue.*
    - **Se sì:**
      - `Dati_avvio_elaborazione` — **Componi** oggetto con chiavi `elaborate`, `scartate`, `inElaborazione`
      - `Rispondi_avvio_elaborazione` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `@{concat('Elaborazione avviata per ', string(length(outputs('Richieste_da_elaborare'))), ' richieste: riceverai un''e-mail con l''esito.')}` · dati `@string(outputs('Dati_avvio_elaborazione'))`
  - `Per_ogni_richiesta` — **Applica a ogni** su `@outputs('Richieste_da_elaborare')` · concorrenza 10
    <br>*Nota: Ogni richiesta: controlli, aggiornamento, registro, e-mail a lavoratore e coordinatore.*
    - `Id_corrente` — **Componi** `@int(coalesce(items('Per_ogni_richiesta')?['id'], 0))`
    - `Leggi_richiesta_corrente` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `ID eq @{outputs('Id_corrente')}` · $top 1
    - `Richiesta_corrente` — **Componi** `@first(body('Leggi_richiesta_corrente')?['value'])`
    - `Ore_HR` — **Componi** oggetto con chiavi `retribuite`, `gettone`
      <br>*Nota: -1 = usa le ore riconosciute dal coordinatore.*
    - `Motivo_scarto` — **Componi** `@if(empty(outputs('Richiesta_corrente')), 'Richiesta non trovata', if(not(equals(coalesce(outputs('Richiesta_corrente')?['Stato']?['Value'], ''), 'In attesa di validazione HR')), concat('Stato non valido: ', coalesce(outputs('Richiesta_corrente')?['Stato']?['V …`
      <br>*Nota: Vuoto = la richiesta può essere elaborata.*
    - `Se_scartata` — **Condizione** `@not(empty(outputs('Motivo_scarto')))` è vero
      - **Se sì:**
        - `Aggiungi_scartata` — **Aggiungi a variabile di matrice** `Scartate` = `{"id": "@outputs('Id_corrente')", "idRichiesta": "@coalesce(outputs('Richiesta_corrente')?['Title'], '')", "motivo": "@outputs('Motivo_scarto')"}`
      - **Se no:**
        - `Aggiorna_esito_HR` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@outputs('Id_corrente')` · colonne: Title = `@outputs('Richiesta_corrente')?['Title']`, Stato/Value = `@outputs('Testi_esito')?['stato']`, NoteHR = `@if(empty(outputs('Nota')), outputs('Richiesta_corrente')?['NoteHR'], outputs('Nota'))`, OreRetribuiteHR = `@if(equals(outputs('Azione'), 'valida'), outputs('Ore_HR')?['retribuite'], outputs('Richie …`, OreGettoneHR = `@if(equals(outputs('Azione'), 'valida'), outputs('Ore_HR')?['gettone'], outputs('Richiesta …`, DataValidazioneHR = `@if(equals(outputs('Azione'), 'valida'), utcNow(), outputs('Richiesta_corrente')?['DataVal …`, UltimaModificaDa = `@outputs('Chiamante')`
        - `Registro_esito_HR` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `@{outputs('Testi_esito')?['azioneRegistro']}`, RichiestaRif = `@outputs('Id_corrente')`, IdRichiesta = `@{outputs('Richiesta_corrente')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_corrente'))}`, Campo = `Stato`, ValorePrecedente = `In attesa di validazione HR`, ValoreNuovo = `@{outputs('Testi_esito')?['stato']}`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{outputs('Nota')}`
        - `Variazioni_ore_HR` — **Componi** matrice
        - `Variazioni_ore_HR_effettive` — **Filtra matrice** da `@outputs('Variazioni_ore_HR')` dove `@and(equals(outputs('Azione'), 'valida'), not(equals(item()?['prima'], item()?['dopo'])))`
        - `Registra_variazioni_ore_HR` — **Applica a ogni** su `@body('Variazioni_ore_HR_effettive')` · concorrenza predefinita
          - `Registro_variazione_ore_HR` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Variazione ore riconosciute da HR`, RichiestaRif = `@outputs('Id_corrente')`, IdRichiesta = `@{outputs('Richiesta_corrente')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_corrente'))}`, Campo = `@items('Registra_variazioni_ore_HR')?['campo']`, ValorePrecedente = `@items('Registra_variazioni_ore_HR')?['prima']`, ValoreNuovo = `@items('Registra_variazioni_ore_HR')?['dopo']`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `Valore precedente = ore riconosciute dal coordinatore`
        - `Se_email_lavoratore_esito_HR` — **Condizione** `@not(empty(trim(coalesce(outputs('Richiesta_corrente')?['EmailPersonale'], ''))))` è vero
          - **Se sì:**
            - `Email_lavoratore_esito_HR` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Richiesta_corrente')?['EmailPersonale']}` · oggetto `@{outputs('Testi_esito')?['oggetto']} – @{outputs('Richiesta_corrente')?['Title']}`
            - `Registro_email_non_riuscita_esito_HR` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non riuscita`, RichiestaRif = `@outputs('Id_corrente')`, IdRichiesta = `@{outputs('Richiesta_corrente')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_corrente'))}`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `Invio non riuscito a @{outputs('Richiesta_corrente')?['EmailPersonale']}: notifica «@{outp …` — *esegui dopo: Email_lavoratore_esito_HR (Failed, TimedOut)*
          - **Se no:**
            - `Registro_email_mancante_esito_HR` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al lavoratore non inviata`, RichiestaRif = `@outputs('Id_corrente')`, IdRichiesta = `@{outputs('Richiesta_corrente')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_corrente'))}`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `E-mail personale mancante: notifica «@{outputs('Testi_esito')?['oggetto']} – @{outputs('Ri …`
        - `Se_email_coordinatore_esito_HR` — **Condizione** `@not(empty(if(empty(outputs('Richiesta_corrente')?['CoordinatoreEmail']), outputs('Richiesta_corrente')?['CoordinatoreLogin'], outputs('Richiesta_corrente')?['CoordinatoreEmail'])))` è vero
          - **Se sì:**
            - `Email_coordinatore_esito_HR` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{if(empty(outputs('Richiesta_corrente')?['CoordinatoreEmail']), outputs('Richiesta_corrente')?['CoordinatoreLogin'], outputs('Richiesta_corrente')?['Coordinato …` · oggetto `@{outputs('Testi_esito')?['oggetto']} – @{outputs('Richiesta_corrente')?['Title']} – @{concat(outputs('Richiesta_corrente')?['Cognome'], ' ', outputs('Richiesta_corrente')?['Nome'])}`
            - `Registro_email_coordinatore_non_riuscita` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `E-mail al coordinatore non riuscita`, RichiestaRif = `@outputs('Id_corrente')`, IdRichiesta = `@{outputs('Richiesta_corrente')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(outputs('Id_corrente'))}`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `Invio non riuscito a @{if(empty(outputs('Richiesta_corrente')?['CoordinatoreEmail']), outp …` — *esegui dopo: Email_coordinatore_esito_HR (Failed, TimedOut)*
        - `Aggiungi_elaborata` — **Aggiungi a variabile di matrice** `Elaborate` = `@outputs('Id_corrente')`
  - `Motivi_scarto` — **Seleziona** da `@variables('Scartate')` → `@concat(if(empty(item()?['idRichiesta']), string(item()?['id']), item()?['idRichiesta']), ': ', item()?['motivo'])`
  - `Dati_esito_HR` — **Componi** oggetto con chiavi `elaborate`, `scartate`
  - `Se_risposta_finale` — **Condizione** `@lessOrEquals(length(outputs('Richieste_da_elaborare')), 25)` è vero
    - **Se sì:**
      - `Rispondi_esito_HR` — **Rispondi a un'app o a un flusso di Power Apps** esito `@{if(and(equals(length(variables('Elaborate')), 0), greater(length(variables('Scartate')), 0)), 'ERRORE', 'OK')}` · messaggio `@{if(equals(length(variables('Elaborate')), 0), concat('Nessuna richiesta elaborata: ', join(body('Motivi_scarto'), ' · ')), concat('Richieste elaborate: ', str …` · dati `@string(outputs('Dati_esito_HR'))`
    - **Se no:**
      - `Email_riepilogo_esito_HR` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{concat(outputs('Chiamante'), ';', outputs('Configurazione')?['EmailHR'])}` · oggetto `Esito elaborazione HR – @{outputs('Testi_esito')?['stato']}: @{string(length(variables('Elaborate')))} richieste elaborate`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API08_ChiusuraMensile

**Scopo.** HR chiude il mese: le richieste *Validata da HR* diventano *Inclusa nel riepilogo mensile*. L'Amministratore può riaprirlo.

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | anno | Numero | `number` | Anno del periodo |
| 2 | mese | Numero | `number_1` | Mese del periodo (1-12) |
| 3 | azione | Testo | `text` | chiudi oppure riapri |
| 4 | nota | Testo | `text_1` | Nota HR (obbligatoria per riapri: motivo della riapertura) |

**Passaggi**
1. `Periodo` = `AAAA-MM`. In parallelo: ruoli del chiamante ed elemento di *Chiusure mensili* con `Title eq 'AAAA-MM'`.
2. `Controlli_chiusura`:
   - azione e periodo validi;
   - *chiudi* solo HR o Amministratore, *riapri* solo Amministratore;
   - non si chiude un periodo già chiuso, si riapre solo un periodo chiuso;
   - la motivazione è obbligatoria per riapri.
3. **chiudi**:
   1. crea o aggiorna l'elemento: `StatoPeriodo` = Chiuso, `DataChiusura`, `UtenteChiusura`, `NoteHR`;
   2. registro;
   3. legge le richieste *Validata da HR* del periodo e **risponde** `OK` `{periodo, stato: "Chiuso", richiesteIncluse: N}`;
   4. poi `Includi_richieste` (concorrenza 10): *Inclusa nel riepilogo mensile* e `PeriodoChiusura`;
   5. infine i totali del periodo (*Inclusa* + *Inviata a Payroll*: `NumeroRichieste`, `TotaleOreRiconosciute` = somma `OreRetribuiteHR`, `TotaleGettoni` = somma `OreGettoneHR`) e una riga di registro riepilogativa.
4. **riapri**: `StatoPeriodo` = Riaperto, `DataRiapertura`, `UtenteRiapertura`, `MotivoRiapertura`, registro, risposta, e-mail a HR. Le richieste già incluse restano incluse. Alla chiusura successiva il file paghe esce in una nuova versione con le sole richieste non ancora inviate.

<details><summary>Elenco completo delle azioni di SDF_API08_ChiusuraMensile</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Inizializza_IdChiusura` — **Inizializza variabile** `IdChiusura` (integer) = `0`
- `Prova` — **Ambito**
  - `Anno` — **Componi** `@int(triggerBody()?['number'])`
  - `Mese` — **Componi** `@int(triggerBody()?['number_1'])`
  - `Azione` — **Componi** `@toLower(trim(coalesce(triggerBody()?['text'], '')))`
  - `Nota` — **Componi** `@trim(coalesce(triggerBody()?['text_1'], ''))`
  - `Periodo` — **Componi** `@concat(string(outputs('Anno')), '-', formatNumber(outputs('Mese'), '00'))`
  - `Leggi_ruoli_chiamante` — **SharePoint – Ottieni elementi** · lista *Ruoli applicativi* · $filter `Title eq '@{outputs('Chiamante_OData')}' and Attivo eq 1` · $top 10
    <br>*Nota: Ruoli applicativi attivi del chiamante.*
  - `Leggi_chiusura` — **SharePoint – Ottieni elementi** · lista *Chiusure mensili* · $filter `Title eq '@{outputs('Periodo')}'` · $top 1 — *esegui dopo: Periodo (Succeeded)*
  - `Ruoli_chiamante` — **Seleziona** da `@body('Leggi_ruoli_chiamante')?['value']` → `@item()?['Ruolo']?['Value']` — *esegui dopo: Leggi_ruoli_chiamante (Succeeded), Leggi_chiusura (Succeeded)*
  - `Chiusura` — **Componi** `@first(body('Leggi_chiusura')?['value'])`
  - `Stato_periodo` — **Componi** `@coalesce(outputs('Chiusura')?['StatoPeriodo']?['Value'], 'Aperto')`
  - `Controlli_chiusura` — **Componi** `@if(not(contains(createArray('chiudi', 'riapri'), outputs('Azione'))), 'Azione non valida.', if(or(less(outputs('Mese'), 1), greater(outputs('Mese'), 12), less(outputs('Anno'), 2000), greater(outputs('Anno'), 2100)), 'Periodo non valido.', if(and(equals(output …`
  - `Se_controlli_non_superati` — **Condizione** `@not(empty(outputs('Controlli_chiusura')))` è vero
    - **Se sì:**
      - `Rispondi_controlli_non_superati` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{outputs('Controlli_chiusura')}` · dati `{}`
      - `Termina_controlli_non_superati` — **Termina** (stato Succeeded)
  - `Ruolo_registro` — **Componi** `@if(and(equals(outputs('Azione'), 'chiudi'), contains(body('Ruoli_chiamante'), 'Formazione HR')), 'Formazione HR', 'Amministratore')`
  - `Se_chiudi` — **Condizione** `@equals(outputs('Azione'), 'chiudi')` è vero
    <br>*Nota: chiudi: HR o Amministratore · riapri: solo Amministratore.*
    - **Se sì:**
      - `Se_chiusura_esistente` — **Condizione** `@not(empty(outputs('Chiusura')))` è vero
        <br>*Nota: Crea o aggiorna l'elemento Chiusure mensili con Title = AAAA-MM.*
        - **Se sì:**
          - `Aggiorna_chiusura` — **SharePoint – Aggiorna elemento** · lista *Chiusure mensili* · ID `@outputs('Chiusura')?['ID']` · colonne: Title = `@outputs('Periodo')`, Mese = `@outputs('Mese')`, Anno = `@outputs('Anno')`, StatoPeriodo/Value = `Chiuso`, DataChiusura = `@utcNow()`, UtenteChiusura = `@outputs('Chiamante')`, NoteHR = `@outputs('Nota')`
          - `Imposta_id_chiusura` — **Imposta variabile** `IdChiusura` = `@outputs('Chiusura')?['ID']`
        - **Se no:**
          - `Crea_chiusura` — **SharePoint – Crea elemento** · lista *Chiusure mensili* · colonne: Title = `@outputs('Periodo')`, Mese = `@outputs('Mese')`, Anno = `@outputs('Anno')`, StatoPeriodo/Value = `Chiuso`, DataChiusura = `@utcNow()`, UtenteChiusura = `@outputs('Chiamante')`, NoteHR = `@outputs('Nota')`
          - `Imposta_id_chiusura_nuova` — **Imposta variabile** `IdChiusura` = `@body('Crea_chiusura')?['ID']`
      - `Registro_chiusura` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Chiusura mensile`, Tabella = `Chiusure mensili`, IdRecord = `@{string(variables('IdChiusura'))}`, Campo = `StatoPeriodo`, ValorePrecedente = `@{outputs('Stato_periodo')}`, ValoreNuovo = `Chiuso`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{outputs('Nota')}`
      - `Leggi_richieste_validate` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `AnnoCompetenza eq @{string(outputs('Anno'))} and MeseCompetenza eq @{string(outputs('Mese'))} and Stato eq 'Validata da HR'` · $top 5000
      - `Dati_chiusura` — **Componi** oggetto con chiavi `periodo`, `stato`, `richiesteIncluse`
      - `Rispondi_chiusura` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `@{concat('Mese ', outputs('Periodo'), ' chiuso: ', string(length(body('Leggi_richieste_validate')?['value'])), ' richieste validate incluse nel riepilogo mensil …` · dati `@string(outputs('Dati_chiusura'))`
      - `Includi_richieste` — **Applica a ogni** su `@body('Leggi_richieste_validate')?['value']` · concorrenza 10
        <br>*Nota: Dopo la risposta: Validata da HR -> Inclusa nel riepilogo mensile.*
        - `Includi_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@items('Includi_richieste')?['ID']` · colonne: Title = `@items('Includi_richieste')?['Title']`, Stato/Value = `Inclusa nel riepilogo mensile`, PeriodoChiusura = `@outputs('Periodo')`, UltimaModificaDa = `@outputs('Chiamante')`
      - `Leggi_richieste_incluse` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `AnnoCompetenza eq @{string(outputs('Anno'))} and MeseCompetenza eq @{string(outputs('Mese'))} and (Stato eq 'Inclusa nel riepilogo mensile' or Stato eq 'Inviata a Payroll')` · $top 5000
      - `Ore_incluse` — **Seleziona** da `@body('Leggi_richieste_incluse')?['value']` → oggetto con chiavi `ore`, `gettoni`
      - `Xml_ore_incluse` — **Componi** `@xml(json(concat('{"r":{"x":', string(body('Ore_incluse')), '}}')))`
      - `Totali_chiusura` — **Componi** oggetto con chiavi `numero`, `ore`, `gettoni`
        <br>*Nota: Totali del periodo (incluse + già inviate a Payroll).*
      - `Aggiorna_totali_chiusura` — **SharePoint – Aggiorna elemento** · lista *Chiusure mensili* · ID `@variables('IdChiusura')` · colonne: Title = `@outputs('Periodo')`, Mese = `@outputs('Mese')`, Anno = `@outputs('Anno')`, NumeroRichieste = `@outputs('Totali_chiusura')?['numero']`, TotaleOreRiconosciute = `@outputs('Totali_chiusura')?['ore']`, TotaleGettoni = `@outputs('Totali_chiusura')?['gettoni']`
      - `Registro_inclusione` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Richieste incluse nel riepilogo mensile`, Tabella = `Chiusure mensili`, IdRecord = `@{string(variables('IdChiusura'))}`, Campo = `NumeroRichieste`, ValoreNuovo = `@{string(outputs('Totali_chiusura')?['numero'])}`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{concat(string(length(body('Leggi_richieste_validate')?['value'])), ' richieste da Valida …`
    - **Se no:**
      - `Riapri_periodo` — **SharePoint – Aggiorna elemento** · lista *Chiusure mensili* · ID `@outputs('Chiusura')?['ID']` · colonne: Title = `@outputs('Periodo')`, Mese = `@outputs('Mese')`, Anno = `@outputs('Anno')`, StatoPeriodo/Value = `Riaperto`, DataRiapertura = `@utcNow()`, UtenteRiapertura = `@outputs('Chiamante')`, MotivoRiapertura = `@outputs('Nota')`
      - `Registro_riapertura` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Riapertura mensile`, Tabella = `Chiusure mensili`, IdRecord = `@{string(outputs('Chiusura')?['ID'])}`, Campo = `StatoPeriodo`, ValorePrecedente = `Chiuso`, ValoreNuovo = `Riaperto`, Ruolo/Value = `Amministratore`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{outputs('Nota')}`
      - `Dati_riapertura` — **Componi** oggetto con chiavi `periodo`, `stato`, `richiesteIncluse`
      - `Rispondi_riapertura` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `@{concat('Mese ', outputs('Periodo'), ' riaperto.')}` · dati `@string(outputs('Dati_riapertura'))`
      - `Email_riapertura_HR` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Riapertura del mese @{outputs('Periodo')}`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API09_FilePaghe

**Scopo.** Genera il CSV per l'Ufficio Paghe (requisito *Flusso 6*).

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | anno | Numero | `number` | Anno del periodo |
| 2 | mese | Numero | `number_1` | Mese del periodo (1-12) |

**Passaggi**
1. `Percorso_file_paghe` = `/FilePaghe` (URL della raccolta *File paghe*). In parallelo: ruoli, chiusura del periodo, richieste del periodo con stato *Inclusa nel riepilogo mensile*.
2. Controlli: HR o Amministratore; periodo **Chiuso**. Senza richieste: `ERRORE` "Nessuna richiesta da inviare per il periodo.".
3. Codici fiscali (output protetti): `Leggi_lavoratori` nell'intervallo di ID `LavoratoreRif` delle richieste, `Coppie_login_cf`, `Mappa_cf`.
4. `Righe_csv` (Seleziona). Ogni riga contiene:
   - CF, Cognome, Nome, Area, Servizio e Centro di costo, tra doppi apici con gli apici interni raddoppiati;
   - Mese e Anno;
   - Titolo corso (catalogo, altrimenti libero);
   - Data `gg/MM/aaaa`;
   - ore retribuite e gettone HR con la virgola;
   - ID richiesta.

   `Righe_senza_cf` conta le righe senza codice fiscale.
5. `Contenuto_csv`: BOM UTF-8 + intestazione `Codice fiscale;Cognome;Nome;Area;Servizio;Centro di costo;Mese;Anno;Titolo corso;Data corso;Ore retribuite riconosciute HR;Ore gettone riconosciute HR;ID richiesta` + righe separate da CRLF.
6. `Crea_file_paghe`: `Formazione_Payroll_AAAA-MM_v<VersioneFile + 1>.csv` nella raccolta *File paghe*. Poi `Proprieta_file_paghe` (`Periodo`, `NumeroRichieste`) e l'URL completo.
7. **Risposta** `OK` con `{url, richieste, senzaCodiceFiscale}`.
8. Dopo la risposta:
   - le richieste passano a *Inviata a Payroll* (concorrenza 10);
   - totali del periodo;
   - *Chiusure mensili*: `FilePagheGenerato`, `FilePagheUrl`, `VersioneFile`, totali;
   - registro;
   - e-mail con il collegamento a `DestinatariPayroll`, con un avviso se mancano codici fiscali.

<details><summary>Elenco completo delle azioni di SDF_API09_FilePaghe</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Percorso_file_paghe` — **Componi** `/FilePaghe`
    <br>*Nota: Cartella radice della raccolta 'File paghe' (URL relativo al sito).*
  - `Anno` — **Componi** `@int(triggerBody()?['number'])`
  - `Mese` — **Componi** `@int(triggerBody()?['number_1'])`
  - `Periodo` — **Componi** `@concat(string(outputs('Anno')), '-', formatNumber(outputs('Mese'), '00'))`
  - `Leggi_ruoli_chiamante` — **SharePoint – Ottieni elementi** · lista *Ruoli applicativi* · $filter `Title eq '@{outputs('Chiamante_OData')}' and Attivo eq 1` · $top 10
    <br>*Nota: Ruoli applicativi attivi del chiamante.*
  - `Leggi_chiusura` — **SharePoint – Ottieni elementi** · lista *Chiusure mensili* · $filter `Title eq '@{outputs('Periodo')}'` · $top 1 — *esegui dopo: Periodo (Succeeded)*
  - `Leggi_richieste_da_inviare` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `AnnoCompetenza eq @{string(outputs('Anno'))} and MeseCompetenza eq @{string(outputs('Mese'))} and Stato eq 'Inclusa nel riepilogo mensile'` · $top 5000 — *esegui dopo: Periodo (Succeeded)*
    <br>*Nota: Richieste del periodo Incluse nel riepilogo mensile (non ancora inviate).*
  - `Ruoli_chiamante` — **Seleziona** da `@body('Leggi_ruoli_chiamante')?['value']` → `@item()?['Ruolo']?['Value']` — *esegui dopo: Leggi_ruoli_chiamante (Succeeded), Leggi_chiusura (Succeeded), Leggi_richieste_da_inviare (Succeeded)*
  - `Chiusura` — **Componi** `@first(body('Leggi_chiusura')?['value'])`
  - `Controlli_file_paghe` — **Componi** `@if(not(or(contains(body('Ruoli_chiamante'), 'Formazione HR'), contains(body('Ruoli_chiamante'), 'Amministratore'))), 'Operazione riservata all''Ufficio HR/Formazione e agli amministratori.', if(or(less(outputs('Mese'), 1), greater(outputs('Mese'), 12)), 'Peri …`
  - `Se_controlli_non_superati` — **Condizione** `@not(empty(outputs('Controlli_file_paghe')))` è vero
    - **Se sì:**
      - `Rispondi_controlli_non_superati` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{outputs('Controlli_file_paghe')}` · dati `{}`
      - `Termina_controlli_non_superati` — **Termina** (stato Succeeded)
  - `Se_nessuna_richiesta` — **Condizione** `@not(empty(if(equals(length(body('Leggi_richieste_da_inviare')?['value']), 0), 'Nessuna richiesta da inviare per il periodo.', '')))` è vero
    - **Se sì:**
      - `Rispondi_nessuna_richiesta` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{if(equals(length(body('Leggi_richieste_da_inviare')?['value']), 0), 'Nessuna richiesta da inviare per il periodo.', '')}` · dati `{}`
      - `Termina_nessuna_richiesta` — **Termina** (stato Succeeded)
  - `Ruolo_registro` — **Componi** `@if(contains(body('Ruoli_chiamante'), 'Formazione HR'), 'Formazione HR', 'Amministratore')`
  - `Riferimenti_lavoratori` — **Seleziona** da `@body('Leggi_richieste_da_inviare')?['value']` → `@coalesce(item()?['LavoratoreRif'], 0)`
  - `Leggi_lavoratori` — **SharePoint – Ottieni elementi** · lista *Lavoratori* · $filter `ID ge @{formatNumber(min(body('Riferimenti_lavoratori')), '0', 'en-US')} and ID le @{formatNumber(max(body('Riferimenti_lavoratori')), '0', 'en-US')}` · $top 5000
    <br>*Nota: Lavoratori nell'intervallo di ID delle richieste (ID è sempre indicizzato).*
  - `Coppie_login_cf` — **Seleziona** da `@body('Leggi_lavoratori')?['value']` → `@concat('"', toLower(coalesce(item()?['Login'], '')), '":"', coalesce(item()?['CodiceFiscale'], ''), '"')`
    <br>*Nota: Coppie "login":"CF".*
  - `Mappa_cf` — **Componi** `@json(concat('{', join(body('Coppie_login_cf'), ','), '}'))`
    <br>*Nota: Mappa login -> codice fiscale senza cicli: outputs('Mappa_cf')?['<login>'].*
  - `Righe_csv` — **Seleziona** da `@body('Leggi_richieste_da_inviare')?['value']` → `@concat(concat('"', replace(string(coalesce(outputs('Mappa_cf')?[toLower(coalesce(item()?['LavoratoreLogin'], ''))], '')), '"', '""'), '"'), ';', concat('"', replace(string(coalesce(item()?['Cognome'] …`
    <br>*Nota: Una riga per richiesta; testi tra doppi apici, decimali con la virgola, data gg/MM/aaaa.*
  - `Righe_senza_cf` — **Filtra matrice** da `@body('Leggi_richieste_da_inviare')?['value']` dove `@empty(outputs('Mappa_cf')?[toLower(coalesce(item()?['LavoratoreLogin'], ''))])`
  - `Versione_file` — **Componi** `@add(coalesce(outputs('Chiusura')?['VersioneFile'], 0), 1)`
  - `Nome_file` — **Componi** `@concat('Formazione_Payroll_', outputs('Periodo'), '_v', string(outputs('Versione_file')), '.csv')`
  - `Contenuto_csv` — **Componi** `@concat(decodeUriComponent('%EF%BB%BF'), 'Codice fiscale;Cognome;Nome;Area;Servizio;Centro di costo;Mese;Anno;Titolo corso;Data corso;Ore retribuite riconosciute HR;Ore gettone riconosciute HR;ID richiesta', decodeUriComponent('%0D%0A'), join(body('Righe_csv') …`
    <br>*Nota: UTF-8 con BOM, separatore ;, righe CRLF.*
  - `Crea_file_paghe` — **SharePoint – Crea file** · cartella `@outputs('Percorso_file_paghe')`, nome `@outputs('Nome_file')`
  - `Proprieta_file_paghe` — **SharePoint – Aggiorna proprietà file** · lista *File paghe* · ID `@body('Crea_file_paghe')?['ItemId']` · colonne: Periodo = `@outputs('Periodo')`, NumeroRichieste = `@length(body('Leggi_richieste_da_inviare')?['value'])`
  - `Url_file_paghe` — **Componi** `@concat(variables('SitoUrl'), replace(uriComponent(body('Crea_file_paghe')?['Path']), '%2F', '/'))`
  - `Ore_file` — **Seleziona** da `@body('Leggi_richieste_da_inviare')?['value']` → oggetto con chiavi `ore`, `gettoni`
  - `Xml_ore_file` — **Componi** `@xml(json(concat('{"r":{"x":', string(body('Ore_file')), '}}')))`
  - `Totali_file` — **Componi** oggetto con chiavi `ore`, `gettoni`
  - `Dati_file_paghe` — **Componi** oggetto con chiavi `url`, `richieste`, `senzaCodiceFiscale`
  - `Rispondi_file_paghe` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `@{concat('File paghe generato: ', string(length(body('Leggi_richieste_da_inviare')?['value'])), ' richieste.', if(greater(length(body('Righe_senza_cf')), 0), co …` · dati `@string(outputs('Dati_file_paghe'))`
  - `Segna_inviate_payroll` — **Applica a ogni** su `@body('Leggi_richieste_da_inviare')?['value']` · concorrenza 10
    <br>*Nota: Dopo la risposta: Inclusa nel riepilogo mensile -> Inviata a Payroll.*
    - `Segna_inviata_payroll` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@items('Segna_inviate_payroll')?['ID']` · colonne: Title = `@items('Segna_inviate_payroll')?['Title']`, Stato/Value = `Inviata a Payroll`, UltimaModificaDa = `@outputs('Chiamante')`
  - `Leggi_richieste_periodo` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `AnnoCompetenza eq @{string(outputs('Anno'))} and MeseCompetenza eq @{string(outputs('Mese'))} and (Stato eq 'Inclusa nel riepilogo mensile' or Stato eq 'Inviata a Payroll')` · $top 5000
  - `Ore_periodo` — **Seleziona** da `@body('Leggi_richieste_periodo')?['value']` → oggetto con chiavi `ore`, `gettoni`
  - `Xml_ore_periodo` — **Componi** `@xml(json(concat('{"r":{"x":', string(body('Ore_periodo')), '}}')))`
  - `Totali_periodo` — **Componi** oggetto con chiavi `numero`, `ore`, `gettoni`
  - `Aggiorna_chiusura_file` — **SharePoint – Aggiorna elemento** · lista *Chiusure mensili* · ID `@outputs('Chiusura')?['ID']` · colonne: Title = `@outputs('Periodo')`, Mese = `@outputs('Mese')`, Anno = `@outputs('Anno')`, FilePagheGenerato = `True`, FilePagheUrl = `@outputs('Url_file_paghe')`, VersioneFile = `@outputs('Versione_file')`, NumeroRichieste = `@outputs('Totali_periodo')?['numero']`, TotaleOreRiconosciute = `@outputs('Totali_periodo')?['ore']`, TotaleGettoni = `@outputs('Totali_periodo')?['gettoni']`
  - `Registro_file_paghe` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Generazione file paghe`, Tabella = `File paghe`, IdRecord = `@{string(body('Crea_file_paghe')?['ItemId'])}`, Campo = `VersioneFile`, ValorePrecedente = `@{string(coalesce(outputs('Chiusura')?['VersioneFile'], 0))}`, ValoreNuovo = `@{string(outputs('Versione_file'))}`, Ruolo/Value = `@outputs('Ruolo_registro')`, LoginAutore = `@outputs('Chiamante')`, Nota = `@{concat(outputs('Nome_file'), ': ', string(length(body('Leggi_richieste_da_inviare')?['va …`
  - `Email_file_paghe` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['DestinatariPayroll']}` · oggetto `File paghe formazione – @{concat(createArray('gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre')[sub(outputs('Mese'), 1)], ' ', strin …`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_API10_DettaglioRichiesta

**Scopo.** Dettaglio di una richiesta con i permessi calcolati per chi chiama e, solo per HR e Amministratore, lo storico.

**Trigger.** **Power Apps (V2)** (`manual`), parametri obbligatori nell'ordine:

| # | Nome | Tipo | Chiave | Descrizione |
|---|---|---|---|---|
| 1 | id | Numero | `number` | ID dell'elemento Richieste formazione |

**Variabili.** `Storico` (matrice, vuota).

**Passaggi**
1. In parallelo: richiesta (`ID eq <id>`) e ruoli del chiamante.
2. `Profilo_accesso`: è il lavoratore; è il coordinatore (diverso dal lavoratore; le bozze non sono visibili al coordinatore); è HR; è amministratore. Se nessuna condizione vale o la richiesta non esiste: `ERRORE` "Richiesta non trovata o non autorizzata." (stesso messaggio nei due casi).
3. `Mese_chiuso` dal periodo della richiesta.
4. Solo HR/Amministratore: `Leggi_storico` (*Registro modifiche*, `RichiestaRif eq <id>`, ordine `ID asc`) → `Storico`.
5. `Dati_dettaglio`:
   - `richiesta` (stessa mappatura di API02);
   - `ruoloChiamante`: amministratore > hr > coordinatore > lavoratore;
   - `permessi`, secondo §1.5, tutti falsi se il mese è chiuso:
     - `modifica`: lavoratore, stato Bozza o Integrazione…;
     - `annulla`: lavoratore, stato Bozza, In attesa del coordinatore o Integrazione…;
     - `esitoCoordinatore`: coordinatore, stato In attesa del coordinatore;
     - `esitoHR`: HR o Amministratore che non è il lavoratore, stato In attesa di validazione HR;
   - `meseChiuso`;
   - `storico`.

<details><summary>Elenco completo delle azioni di SDF_API10_DettaglioRichiesta</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Chiamante` — **Componi** `@toLower(trim(coalesce(triggerOutputs()?['headers']?['x-ms-user-email'], '')))`
  <br>*Nota: Identità di chi chiama, dall'intestazione della chiamata di Power Apps.*
- `Chiamante_OData` — **Componi** `@replace(outputs('Chiamante'), '''', '''''')`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Inizializza_Storico` — **Inizializza variabile** `Storico` (array) = `[]`
- `Prova` — **Ambito**
  - `Leggi_richiesta` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `ID eq @{int(triggerBody()?['number'])}` · $top 1
  - `Leggi_ruoli_chiamante` — **SharePoint – Ottieni elementi** · lista *Ruoli applicativi* · $filter `Title eq '@{outputs('Chiamante_OData')}' and Attivo eq 1` · $top 10 — *in parallelo dall'inizio del blocco*
  - `Ruoli_chiamante` — **Seleziona** da `@body('Leggi_ruoli_chiamante')?['value']` → `@item()?['Ruolo']?['Value']` — *esegui dopo: Leggi_richiesta (Succeeded), Leggi_ruoli_chiamante (Succeeded)*
  - `Richiesta` — **Componi** `@first(body('Leggi_richiesta')?['value'])`
  - `Profilo_accesso` — **Componi** oggetto con chiavi `lavoratore`, `coordinatore`, `hr`, `amministratore`
    <br>*Nota: Relazione del chiamante con la richiesta. Il coordinatore non vede le bozze.*
  - `Se_non_autorizzato` — **Condizione** `@not(empty(if(or(empty(outputs('Richiesta')), not(or(outputs('Profilo_accesso')?['lavoratore'], outputs('Profilo_accesso')?['coordinatore'], outputs('Profilo_accesso')?['hr'], outputs('Profilo_accesso')?['amministratore']))), 'Richiesta non trovata o non autorizzata.', '')))` è vero
    - **Se sì:**
      - `Rispondi_non_autorizzato` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `@{if(or(empty(outputs('Richiesta')), not(or(outputs('Profilo_accesso')?['lavoratore'], outputs('Profilo_accesso')?['coordinatore'], outputs('Profilo_accesso')?[ …` · dati `{}`
      - `Termina_non_autorizzato` — **Termina** (stato Succeeded)
  - `Periodo_richiesta` — **Componi** `@if(empty(outputs('Richiesta')?['AnnoCompetenza']), '', concat(string(outputs('Richiesta')?['AnnoCompetenza']), '-', formatNumber(coalesce(outputs('Richiesta')?['MeseCompetenza'], 0), '00')))`
  - `Leggi_mese_chiuso` — **SharePoint – Ottieni elementi** · lista *Chiusure mensili* · $filter `Title eq '@{outputs('Periodo_richiesta')}' and StatoPeriodo eq 'Chiuso'` · $top 1
  - `Mese_chiuso` — **Componi** `@not(empty(body('Leggi_mese_chiuso')?['value']))`
  - `Se_storico_visibile` — **Condizione** `@or(outputs('Profilo_accesso')?['hr'], outputs('Profilo_accesso')?['amministratore'])` è vero
    - **Se sì:**
      - `Leggi_storico` — **SharePoint – Ottieni elementi** · lista *Registro modifiche* · $filter `RichiestaRif eq @{outputs('Richiesta')?['ID']}` · $orderby `ID asc` · $top 5000
        <br>*Nota: Storico delle azioni sulla richiesta (solo HR e Amministratore).*
      - `Mappa_storico` — **Seleziona** da `@body('Leggi_storico')?['value']` → oggetto con chiavi `data`, `azione`, `campo`, `valorePrecedente`, `valoreNuovo`, `ruolo`, `autore`, `nota`
      - `Imposta_storico` — **Imposta variabile** `Storico` = `@body('Mappa_storico')`
  - `Mappa_richiesta` — **Seleziona** da `@createArray(outputs('Richiesta'))` → oggetto con chiavi `id`, `idRichiesta`, `lavoratoreLogin`, `lavoratoreId`, `cognome`, `nome`, `emailPersonale`, `area`, `servizio`, `centroDiCosto`, `strutturaId`, `coordinatoreLogin`, `coordinatoreNome`, `coordinatoreEmail`, `corsoId`, `codiceCorso`, `titoloCorso`, `titoloCorsoLibero`, `durataCorso`, `enteErogatore`, `modalita`, `piuGiornate`, `dataSessione`, `oraInizioSessione`, `oraFineSessione`, `durataSessione`, `oraIngresso`, `oraUscita`, `oreFrequentate`, `oreRetribuiteRichieste`, `oreGettoneRichieste`, `oreRetribuiteCoord`, `oreGettoneCoord`, `oreRetribuiteHR`, `oreGettoneHR`, `attestatoUrl`, `altraDocUrl`, `attestatoPresente`, `noteLavoratore`, `noteCoordinatore`, `noteHR`, `stato`, `dataInvio`, `dataApprovazioneCoord`, `dataValidazioneHR`, `meseCompetenza`, `annoCompetenza`, `periodoChiusura`, `confermaPartecipazione`, `confermaCorrettezza`, `autorizzazioneInvio`, `possibileDuplicato`, `anomalie`, `giorniAttesa`, `segnalataHR`, `ultimaModificaDa`, `creato`, `modificato`
  - `Dati_dettaglio` — **Componi** oggetto con chiavi `richiesta`, `ruoloChiamante`, `permessi`, `meseChiuso`, `storico`
  - `Rispondi_dettaglio` — **Rispondi a un'app o a un flusso di Power Apps** esito `OK` · messaggio `` · dati `@string(outputs('Dati_dettaglio'))`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Rispondi_errore_imprevisto` — **Rispondi a un'app o a un flusso di Power Apps** esito `ERRORE` · messaggio `Si è verificato un errore imprevisto. Riprova più tardi o contatta l'Ufficio HR/Formazione.` · dati `{}`
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])` — *esegui dopo: Rispondi_errore_imprevisto (Succeeded, Failed, Skipped, TimedOut)*
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_F4_Promemoria

**Scopo.** Requisito *Flusso 4*: promemoria al coordinatore dopo 3 e 5 giorni lavorativi senza esito, segnalazione a HR dopo 7.

**Trigger.** **Ricorrenza** (`Ricorrenza_giorni_lavorativi`): `{"frequency": "Week", "interval": 1, "schedule": {"weekDays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "hours": ["8"], "minutes": [0]}, "timeZone": "W. Europe Standard Time"}`

**Passaggi**
1. `Oggi` (`yyyy-MM-dd` nel fuso W. Europe) e `Festivita` = `json(Configurazione.Festivita)`. Se oggi è festivo: `Termina_giorno_festivo` (sabato e domenica sono già esclusi dalla ricorrenza).
2. `Leggi_richieste_in_attesa`: `Stato eq 'In attesa del coordinatore'`.
3. `Per_ogni_richiesta_in_attesa` (concorrenza 10). Le richieste inviate oggi non contano. Per le altre:
   1. `Nuovi_giorni_attesa` = `GiorniAttesa` + 1;
   2. aggiornamento di `GiorniAttesa`;
   3. a **3** e a **5** giorni: e-mail di promemoria al coordinatore e registro;
   4. da **7** giorni in poi, se `SegnalataHR` = No: e-mail al coordinatore con HR in copia (importanza alta), `SegnalataHR` = Sì e registro.

<details><summary>Elenco completo delle azioni di SDF_F4_Promemoria</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Oggi` — **Componi** `@formatDateTime(convertFromUtc(utcNow(), 'W. Europe Standard Time'), 'yyyy-MM-dd')`
  - `Festivita` — **Componi** `@json(coalesce(outputs('Configurazione')?['Festivita'], '[]'))`
  - `Se_giorno_festivo` — **Condizione** `@contains(outputs('Festivita'), outputs('Oggi'))` è vero
    <br>*Nota: Oggi è in Configurazione.Festivita: nessun conteggio.*
    - **Se sì:**
      - `Termina_giorno_festivo` — **Termina** (stato Succeeded)
  - `Leggi_richieste_in_attesa` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `Stato eq 'In attesa del coordinatore'` · $top 5000
  - `Per_ogni_richiesta_in_attesa` — **Applica a ogni** su `@body('Leggi_richieste_in_attesa')?['value']` · concorrenza 10
    - `Se_da_conteggiare` — **Condizione** `@if(empty(items('Per_ogni_richiesta_in_attesa')?['DataInvio']), true, less(convertFromUtc(items('Per_ogni_richiesta_in_attesa')?['DataInvio'], 'W. Europe Standard Time', 'yyyy-MM-dd'), outputs('Oggi')))` è vero
      <br>*Nota: Le richieste inviate oggi non vengono conteggiate.*
      - **Se sì:**
        - `Nuovi_giorni_attesa` — **Componi** `@add(coalesce(items('Per_ogni_richiesta_in_attesa')?['GiorniAttesa'], 0), 1)`
        - `Da_segnalare_HR` — **Componi** `@and(greaterOrEquals(outputs('Nuovi_giorni_attesa'), 7), not(equals(items('Per_ogni_richiesta_in_attesa')?['SegnalataHR'], true)))`
        - `Aggiorna_giorni_attesa` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@items('Per_ogni_richiesta_in_attesa')?['ID']` · colonne: Title = `@items('Per_ogni_richiesta_in_attesa')?['Title']`, GiorniAttesa = `@outputs('Nuovi_giorni_attesa')`, SegnalataHR = `@or(equals(items('Per_ogni_richiesta_in_attesa')?['SegnalataHR'], true), outputs('Da_segna …`
        - `Se_promemoria` — **Condizione** `@and(or(equals(outputs('Nuovi_giorni_attesa'), 3), equals(outputs('Nuovi_giorni_attesa'), 5)), not(empty(if(empty(items('Per_ogni_richiesta_in_attesa')?['CoordinatoreEmail']), items('Per_ogni_richiesta_in_attesa')?['CoordinatoreLogin'], items('Per_ogni_richiesta_in_attesa')?['CoordinatoreEmail']))))` è vero
          <br>*Nota: Promemoria al 3° e al 5° giorno lavorativo.*
          - **Se sì:**
            - `Email_promemoria_coordinatore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{if(empty(items('Per_ogni_richiesta_in_attesa')?['CoordinatoreEmail']), items('Per_ogni_richiesta_in_attesa')?['CoordinatoreLogin'], items('Per_ogni_richiesta_ …` · oggetto `Promemoria: richiesta di formazione in attesa – @{items('Per_ogni_richiesta_in_attesa')?['Title']}`
            - `Registro_promemoria_non_riuscito` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Promemoria al coordinatore non riuscito`, RichiestaRif = `@items('Per_ogni_richiesta_in_attesa')?['ID']`, IdRichiesta = `@{items('Per_ogni_richiesta_in_attesa')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(items('Per_ogni_richiesta_in_attesa')?['ID'])}`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`, Nota = `Invio non riuscito a @{if(empty(items('Per_ogni_richiesta_in_attesa')?['CoordinatoreEmail' …` — *esegui dopo: Email_promemoria_coordinatore (Failed, TimedOut)*
            - `Registro_promemoria` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `@{concat('Promemoria al coordinatore (', string(outputs('Nuovi_giorni_attesa')), ' giorni) …`, RichiestaRif = `@items('Per_ogni_richiesta_in_attesa')?['ID']`, IdRichiesta = `@{items('Per_ogni_richiesta_in_attesa')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(items('Per_ogni_richiesta_in_attesa')?['ID'])}`, Campo = `GiorniAttesa`, ValoreNuovo = `@{string(outputs('Nuovi_giorni_attesa'))}`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')` — *esegui dopo: Email_promemoria_coordinatore (Succeeded)*
        - `Se_sollecito_HR` — **Condizione** `@outputs('Da_segnalare_HR')` è vero
          <br>*Nota: Dal 7° giorno: coordinatore + HR, una sola volta (Sollecito segnalato a HR = Sì).*
          - **Se sì:**
            - `Email_sollecito_HR` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{if(empty(if(empty(items('Per_ogni_richiesta_in_attesa')?['CoordinatoreEmail']), items('Per_ogni_richiesta_in_attesa')?['CoordinatoreLogin'], items('Per_ogni_r …` · Cc `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Sollecito: richiesta di formazione in attesa da @{string(outputs('Nuovi_giorni_attesa'))} giorni – @{items('Per_ogni_richiesta_in_attesa')?['Title']}`
            - `Registro_sollecito` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Sollecito segnalato a HR`, RichiestaRif = `@items('Per_ogni_richiesta_in_attesa')?['ID']`, IdRichiesta = `@{items('Per_ogni_richiesta_in_attesa')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(items('Per_ogni_richiesta_in_attesa')?['ID'])}`, Campo = `SegnalataHR`, ValorePrecedente = `No`, ValoreNuovo = `Sì`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`, Nota = `@{concat(string(outputs('Nuovi_giorni_attesa')), ' giorni lavorativi in attesa', if(equals …` — *esegui dopo: Email_sollecito_HR (Succeeded, Failed, TimedOut)*
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])`
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_F5_RiepilogoMensile

**Scopo.** Requisito *Flusso 5*: il giorno 2 di ogni mese, riepilogo del mese precedente a ogni coordinatore e quadro completo a HR.

**Trigger.** **Ricorrenza** (`Ricorrenza_mensile`): `{"frequency": "Month", "interval": 1, "startTime": "2026-12-02T07:00:00", "timeZone": "W. Europe Standard Time"}`

La data di inizio fissa il giorno (2) e l'ora (07:00) delle esecuzioni mensili. Se si importa il flusso dopo quella data va bene lo stesso: le esecuzioni successive seguono lo stesso schema.

**Variabili.** `TotaliCoordinatori` (matrice).

**Passaggi**
1. `Mese_precedente`, `Anno_riferimento`, `Mese_riferimento`.
2. `Leggi_richieste_mese` (`AnnoCompetenza` e `MeseCompetenza`) → `Richieste_riepilogo`, senza Bozza e Annullata.
3. `Righe_riepilogo` (Seleziona), una riga per richiesta con:
   - coordinatore, lavoratore, corso, data, stato;
   - le sette colonne di ore;
   - gli indicatori `aperta` (Inviata, In attesa del coordinatore, Integrazione…), `respinta`, `incompleta` (attestato mancante, anomalie o possibile duplicato);
   - le etichette e il colore della riga.
4. `Coordinatori_distinti` = `union(elenco, elenco)`.
5. `Per_ogni_coordinatore` (concorrenza 5):
   1. righe del coordinatore;
   2. totali (somme xpath, lavoratori distinti, aperte, respinte, incomplete);
   3. righe HTML colorate;
   4. e-mail al coordinatore, se ha un login;
   5. aggiunta dei totali a `TotaliCoordinatori`.
6. Totali generali, righe evidenziate (al massimo 300 nel corpo), tabella HTML dei totali per coordinatore (*Crea tabella HTML* + stili in linea), CSV completo.
7. `Email_riepilogo_HR` con il CSV allegato `Riepilogo_formazione_AAAA-MM.csv`.

<details><summary>Elenco completo delle azioni di SDF_F5_RiepilogoMensile</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Inizializza_TotaliCoordinatori` — **Inizializza variabile** `TotaliCoordinatori` (array) = `[]`
- `Inizializza_EmailNonInviate` — **Inizializza variabile** `EmailNonInviate` (array) = `[]`
- `Prova` — **Ambito**
  - `Mese_precedente` — **Componi** `@addToTime(startOfMonth(convertFromUtc(utcNow(), 'W. Europe Standard Time')), -1, 'Month')`
  - `Anno_riferimento` — **Componi** `@int(formatDateTime(outputs('Mese_precedente'), 'yyyy'))`
  - `Mese_riferimento` — **Componi** `@int(formatDateTime(outputs('Mese_precedente'), 'MM'))`
  - `Leggi_richieste_mese` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `AnnoCompetenza eq @{string(outputs('Anno_riferimento'))} and MeseCompetenza eq @{string(outputs('Mese_riferimento'))}` · $top 5000
  - `Richieste_riepilogo` — **Filtra matrice** da `@body('Leggi_richieste_mese')?['value']` dove `@not(contains(createArray('Bozza', 'Annullata'), item()?['Stato']?['Value']))`
    <br>*Nota: Escluse bozze e annullate.*
  - `Righe_riepilogo` — **Seleziona** da `@body('Richieste_riepilogo')` → oggetto con chiavi `coord`, `coordNome`, `coordEmail`, `login`, `id`, `richiesta`, `lavoratore`, `area`, `servizio`, `centroDiCosto`, `corso`, `codiceCorso`, `data`, `stato`, `f`, `rr`, `gr`, `rc`, `gc`, `rh`, `gh`, `aperta`, `respinta`, `incompleta`, `etichette`, `colore`
    <br>*Nota: Una riga per richiesta con ore e indicatori (aperta, respinta, incompleta).*
  - `Elenco_coordinatori` — **Seleziona** da `@body('Righe_riepilogo')` → `@item()?['coord']`
  - `Coordinatori_distinti` — **Componi** `@union(body('Elenco_coordinatori'), body('Elenco_coordinatori'))`
    <br>*Nota: union() di un elenco con se stesso = valori distinti.*
  - `Per_ogni_coordinatore` — **Applica a ogni** su `@outputs('Coordinatori_distinti')` · concorrenza 5
    - `Righe_coordinatore` — **Filtra matrice** da `@body('Righe_riepilogo')` dove `@equals(item()?['coord'], items('Per_ogni_coordinatore'))`
    - `Xml_coordinatore` — **Componi** `@xml(json(concat('{"r":{"x":', string(body('Righe_coordinatore')), '}}')))`
    - `Lavoratori_coordinatore` — **Seleziona** da `@body('Righe_coordinatore')` → `@item()?['login']`
    - `Totali_coordinatore` — **Componi** oggetto con chiavi `richieste`, `lavoratori`, `f`, `rr`, `gr`, `rc`, `gc`, `rh`, `gh`, `aperte`, `respinte`, `incomplete`
    - `Html_righe_coordinatore` — **Seleziona** da `@body('Righe_coordinatore')` → `@concat('<tr style="background:', item()?['colore'], '">', '<td style="padding:6px 8px;border:1px solid #E1DFDD;vertical-align:top">', item()?['richiesta'], '</td>', '<td style="padding:6px 8px;border …`
    - `Se_coordinatore_presente` — **Condizione** `@not(empty(items('Per_ogni_coordinatore')))` è vero
      - **Se sì:**
        - `Email_riepilogo_coordinatore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{first(body('Righe_coordinatore'))?['coordEmail']}` · oggetto `Riepilogo mensile formazione del tuo gruppo – @{concat(createArray('gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre')[sub(outputs('M …`
        - `Annota_email_non_inviata` — **Aggiungi a variabile di matrice** `EmailNonInviate` = `@first(body('Righe_coordinatore'))?['coordEmail']` — *esegui dopo: Email_riepilogo_coordinatore (Failed, TimedOut)*
    - `Aggiungi_totali_coordinatore` — **Aggiungi a variabile di matrice** `TotaliCoordinatori` = `{"coordinatore": "@first(body('Righe_coordinatore'))?['coordNome']", "richieste": "@outputs('Totali_coordinatore')?['richieste']", "lavoratori": "@outputs('Totali_coordinatore')?['lavoratori']", "oreF …`
  - `Xml_generale` — **Componi** `@xml(json(concat('{"r":{"x":', string(body('Righe_riepilogo')), '}}')))`
  - `Lavoratori_mese` — **Seleziona** da `@body('Righe_riepilogo')` → `@item()?['login']`
  - `Totali_generali` — **Componi** oggetto con chiavi `richieste`, `lavoratori`, `f`, `rr`, `gr`, `rc`, `gc`, `rh`, `gh`, `aperte`, `respinte`, `incomplete`
  - `Righe_evidenziate` — **Filtra matrice** da `@body('Righe_riepilogo')` dove `@not(empty(item()?['etichette']))`
  - `Html_righe_evidenziate` — **Seleziona** da `@take(body('Righe_evidenziate'), 300)` → `@concat('<tr style="background:', item()?['colore'], '">', '<td style="padding:6px 8px;border:1px solid #E1DFDD;vertical-align:top">', item()?['richiesta'], '</td>', '<td style="padding:6px 8px;border …`
    <br>*Nota: Al massimo 300 righe nel corpo: l'elenco completo è nel CSV allegato.*
  - `Tabella_totali_coordinatori` — **Crea tabella HTML** da `@variables('TotaliCoordinatori')` · colonne Coordinatore, Richieste, Lavoratori, Ore freq., Retr. rich., Gett. rich., Retr. coord., Gett. coord., Retr. HR, Gett. HR, Aperte, Respinte, Incomplete
  - `Righe_csv_quadro` — **Seleziona** da `@body('Righe_riepilogo')` → `@concat(concat('"', replace(string(coalesce(item()?['richiesta'], '')), '"', '""'), '"'), ';', concat('"', replace(string(coalesce(item()?['lavoratore'], '')), '"', '""'), '"'), ';', concat('"', repla …`
  - `Csv_quadro_completo` — **Componi** `@concat(decodeUriComponent('%EF%BB%BF'), 'ID richiesta;Lavoratore;Area;Servizio;Centro di costo;Coordinatore;Codice corso;Titolo corso;Data;Stato;Ore frequentate;Ore retribuite richieste;Ore gettone richieste;Ore retribuite coordinatore;Ore gettone coordinator …`
  - `Email_riepilogo_HR` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Quadro mensile della formazione – @{concat(createArray('gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre')[sub(outputs('Mese_riferime …`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])`
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_F7_AllineaLavoratore

**Scopo.** Tiene allineati i dati di *Lavoratori* e gestisce il cambio di coordinatore.

**Trigger.** **SharePoint – Quando un elemento viene creato o modificato** (`Quando_un_lavoratore_viene_creato_o_modificato`) sulla lista *Lavoratori*, controllo ogni 2 minuti, *Dividi in* attivo · concorrenza del trigger = 1 (esecuzioni una alla volta) · output protetti.

La concorrenza del trigger è 1: l'aggiornamento fatto dal flusso stesso riattiva il trigger, e la seconda esecuzione parte solo quando la prima ha finito. In quel momento trova tutto già allineato e non fa nulla.

**Variabili.** `CoordNomeProfilo`, `CoordEmailProfilo`.

**Passaggi**
1. `Ottieni_modifiche_lavoratore` (*Ottieni modifiche per un elemento*, dal *Token di inizio della finestra del trigger*) → `Colonne_modificate` (`ColumnHasChanged`).
2. `Valori_attuali`: login, login della persona *Utente Microsoft 365*, login/nome/e-mail del coordinatore (testo), login/nome/e-mail della persona *Coordinatore assegnato*, quali colonne sono cambiate.
3. `Login_desiderato`: se `Login` è vuoto, si ricava da *Utente Microsoft 365*.
4. `Login_coordinatore_desiderato`: dalla persona *Coordinatore* se il login testo è vuoto o se è cambiata solo la persona; altrimenti resta il login testo (es. aggiornato da un'importazione).
5. Nome ed e-mail del coordinatore:
   - dalla persona, se coincide con il login;
   - altrimenti, quando il login è cambiato o nome/e-mail mancano, da **Office 365 Utenti – Ottieni profilo utente (V2)**;
   - se il profilo non si trova, si usa il login.
6. `Se_lavoratore_da_aggiornare`: aggiorna *Lavoratori* **solo se i valori sono diversi** (evita i cicli) e scrive il registro.
7. `Se_coordinatore_cambiato`:
   1. richieste aperte del lavoratore (Bozza, In attesa del coordinatore, Integrazione…) con un coordinatore diverso;
   2. cartella del nuovo coordinatore: verifica e, se manca, creazione e condivisione in lettura;
   3. per ogni richiesta:
      - sposta gli allegati con HTTP `POST _api/web/GetFileByServerRelativeUrl(@f)/moveto(newurl=@n,flags=1)`;
      - aggiorna coordinatore e URL degli allegati (cambia il segmento della cartella);
      - scrive il registro;
   4. e-mail al nuovo coordinatore con l'elenco delle richieste in attesa.

<details><summary>Elenco completo delle azioni di SDF_F7_AllineaLavoratore</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Inizializza_CoordNomeProfilo` — **Inizializza variabile** `CoordNomeProfilo` (string) = `""`
- `Inizializza_CoordEmailProfilo` — **Inizializza variabile** `CoordEmailProfilo` (string) = `""`
- `Prova` — **Ambito**
  - `Percorso_allegati` — **Componi** `/AllegatiFormazione`
    <br>*Nota: Cartella radice della raccolta 'Allegati formazione'.*
  - `Ottieni_modifiche_lavoratore` — **SharePoint – Ottieni modifiche per un elemento o un file (solo proprietà)** · lista *Lavoratori* · ID `@triggerBody()?['ID']` · dal `@triggerOutputs()?['body/{TriggerWindowStartToken}']`
    <br>*Nota: Colonne cambiate dall'inizio della finestra del trigger (ColumnHasChanged).*
  - `Colonne_modificate` — **Componi** `@coalesce(body('Ottieni_modifiche_lavoratore')?['ColumnHasChanged'], json('{}'))`
  - `Valori_attuali` — **Componi** oggetto con chiavi `login`, `loginUtente`, `coordLogin`, `coordNome`, `coordEmail`, `coordPersonaLogin`, `coordPersonaNome`, `coordPersonaEmail`, `personaCambiata`, `loginTestoCambiato`
  - `Login_desiderato` — **Componi** `@if(empty(outputs('Valori_attuali')?['login']), outputs('Valori_attuali')?['loginUtente'], outputs('Valori_attuali')?['login'])`
    <br>*Nota: Se manca Login lo ricava da Utente Microsoft 365.*
  - `Login_coordinatore_desiderato` — **Componi** `@if(and(not(empty(outputs('Valori_attuali')?['coordPersonaLogin'])), or(empty(outputs('Valori_attuali')?['coordLogin']), and(outputs('Valori_attuali')?['personaCambiata'], not(outputs('Valori_attuali')?['loginTestoCambiato'])))), outputs('Valori_attuali')?['co …`
    <br>*Nota: Dalla colonna persona Coordinatore se il login manca o se è cambiata solo la persona.*
  - `Coordinatore_cambiato` — **Componi** `@or(not(equals(outputs('Login_coordinatore_desiderato'), outputs('Valori_attuali')?['coordLogin'])), outputs('Valori_attuali')?['loginTestoCambiato'])`
  - `Coordinatore_da_persona` — **Componi** `@and(not(empty(outputs('Valori_attuali')?['coordPersonaLogin'])), equals(outputs('Login_coordinatore_desiderato'), outputs('Valori_attuali')?['coordPersonaLogin']))`
  - `Se_serve_profilo_coordinatore` — **Condizione** `@and(not(empty(outputs('Login_coordinatore_desiderato'))), not(outputs('Coordinatore_da_persona')), or(outputs('Coordinatore_cambiato'), empty(outputs('Valori_attuali')?['coordNome']), empty(outputs('Valori_attuali')?['coordEmail'])))` è vero
    <br>*Nota: Login coordinatore cambiato come testo (non dalla persona) o nome/e-mail mancanti.*
    - **Se sì:**
      - `Profilo_coordinatore` — **Office 365 Utenti – Ottieni profilo utente (V2)** · ID `@outputs('Login_coordinatore_desiderato')` · utente `@outputs('Login_coordinatore_desiderato')`
        <br>*Nota: Nome ed e-mail del coordinatore da Office 365 Utenti.*
      - `Imposta_nome_da_profilo` — **Imposta variabile** `CoordNomeProfilo` = `@if(equals(actions('Profilo_coordinatore')?['status'], 'Succeeded'), coalesce(body('Profilo_coordinatore')?['displayName'], outputs('Login_coordinatore_desiderato')), outputs('Login_coordinatore_desid …` — *esegui dopo: Profilo_coordinatore (Succeeded, Failed)*
      - `Imposta_email_da_profilo` — **Imposta variabile** `CoordEmailProfilo` = `@if(equals(actions('Profilo_coordinatore')?['status'], 'Succeeded'), toLower(coalesce(body('Profilo_coordinatore')?['mail'], outputs('Login_coordinatore_desiderato'))), outputs('Login_coordinatore_des …`
  - `Coordinatore_desiderato` — **Componi** oggetto con chiavi `login`, `nome`, `email`
  - `Se_lavoratore_da_aggiornare` — **Condizione** `@or(not(equals(outputs('Login_desiderato'), coalesce(triggerBody()?['Login'], ''))), not(equals(outputs('Coordinatore_desiderato')?['login'], coalesce(triggerBody()?['CoordinatoreLogin'], ''))), not(equals(outputs('Coordinatore_desiderato')?['nome'], outputs('Valori_attuali')?['coordNome'])), not(equals(outputs('Coordinatore_desiderato')?['email'], outputs('Valori_attuali')?['coordEmail'])))` è vero
    <br>*Nota: Aggiorna solo se i valori sono diversi: evita i cicli del trigger.*
    - **Se sì:**
      - `Aggiorna_lavoratore` — **SharePoint – Aggiorna elemento** · lista *Lavoratori* · ID `@triggerBody()?['ID']` · colonne: Title = `@triggerBody()?['Title']`, Login = `@outputs('Login_desiderato')`, Cognome = `@triggerBody()?['Cognome']`, Nome = `@triggerBody()?['Nome']`, CoordinatoreLogin = `@outputs('Coordinatore_desiderato')?['login']`, CoordinatoreNome = `@outputs('Coordinatore_desiderato')?['nome']`, CoordinatoreEmail = `@outputs('Coordinatore_desiderato')?['email']`
      - `Registro_allineamento_lavoratore` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Allineamento dati lavoratore`, Tabella = `Lavoratori`, IdRecord = `@{string(triggerBody()?['ID'])}`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`, Nota = `@{concat('Login: ', outputs('Login_desiderato'), ' · coordinatore: ', outputs('Coordinator …`
  - `Se_coordinatore_cambiato` — **Condizione** `@and(outputs('Coordinatore_cambiato'), not(empty(outputs('Login_desiderato'))), not(empty(outputs('Coordinatore_desiderato')?['login'])))` è vero
    <br>*Nota: Riassegna le richieste aperte, sposta gli allegati, avvisa il nuovo coordinatore.*
    - **Se sì:**
      - `Leggi_richieste_aperte` — **SharePoint – Ottieni elementi** · lista *Richieste formazione* · $filter `LavoratoreLogin eq '@{replace(string(outputs('Login_desiderato')), '''', '''''')}' and (Stato eq 'Bozza' or Stato eq 'In attesa del coordinatore' or Stato eq 'Integrazione richiesta dal coordinatore' or Stato eq 'Integrazione richiesta da HR')` · $top 5000
      - `Richieste_da_riassegnare` — **Filtra matrice** da `@body('Leggi_richieste_aperte')?['value']` dove `@not(equals(toLower(coalesce(item()?['CoordinatoreLogin'], '')), outputs('Coordinatore_desiderato')?['login']))`
        <br>*Nota: Solo quelle con un coordinatore diverso: evita i cicli.*
      - `Se_richieste_da_riassegnare` — **Condizione** `@greater(length(body('Richieste_da_riassegnare')), 0)` è vero
        - **Se sì:**
          - `Cartella_nuovo_coordinatore` — **Componi** `@if(empty(outputs('Coordinatore_desiderato')?['login']), 'senza_coordinatore', replace(replace(toLower(trim(outputs('Coordinatore_desiderato')?['login'])), '@', '_'), '.', '_'))`
          - `Percorso_cartella_nuovo_coordinatore` — **Componi** `@concat(outputs('Percorso_allegati'), '/', outputs('Cartella_nuovo_coordinatore'))`
          - `Verifica_cartella_nuovo_coordinatore` — **SharePoint – Invia una richiesta HTTP a SharePoint** · GET `_api/web/GetFolderByServerRelativeUrl('@{replace(concat(uriPath(variables('SitoUrl')), outputs('Percorso_cartella_nuovo_coordinatore')), '''', '''''')}')/Exists`
          - `Se_cartella_nuovo_coordinatore_da_creare` — **Condizione** `@not(equals(body('Verifica_cartella_nuovo_coordinatore')?['value'], true))` è vero — *esegui dopo: Verifica_cartella_nuovo_coordinatore (Succeeded, Failed)*
            - **Se sì:**
              - `Crea_cartella_nuovo_coordinatore` — **SharePoint – Crea nuova cartella** · lista *Allegati formazione* · percorso `@outputs('Cartella_nuovo_coordinatore')`
              - `Condividi_cartella_nuovo_coordinatore` — **SharePoint – Concedi l'accesso a un elemento o una cartella** · lista *Allegati formazione* · ID `@body('Crea_cartella_nuovo_coordinatore')?['ID']` · destinatari `@{if(empty(outputs('Coordinatore_desiderato')?['email']), outputs('Coordinatore_desiderato')?['login'], outputs('Coordinatore_desiderato')?['email'])}`, ruolo `role:1073741826` (può visualizzare), notifica: no
              - `Registro_cartella_nuovo_coordinatore` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Creazione cartella allegati`, Tabella = `Allegati formazione`, IdRecord = `@{string(body('Crea_cartella_nuovo_coordinatore')?['ID'])}`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`, Nota = `@{concat('Cartella ', outputs('Cartella_nuovo_coordinatore'), ' condivisa in lettura con ' …`
          - `Per_ogni_richiesta_da_riassegnare` — **Applica a ogni** su `@body('Richieste_da_riassegnare')` · concorrenza 5
            - `Cartella_precedente` — **Componi** `@if(empty(items('Per_ogni_richiesta_da_riassegnare')?['CoordinatoreLogin']), 'senza_coordinatore', replace(replace(toLower(trim(items('Per_ogni_richiesta_da_riassegnare')?['CoordinatoreLogin'])), '@', '_'), '.', '_'))`
            - `Leggi_allegati_richiesta` — **SharePoint – Ottieni elementi** · lista *Allegati formazione* · $filter `RichiestaRif eq @{items('Per_ogni_richiesta_da_riassegnare')?['ID']}` · $top 100
            - `Per_ogni_allegato` — **Applica a ogni** su `@body('Leggi_allegati_richiesta')?['value']` · concorrenza 1
              - `Sposta_allegato` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/GetFileByServerRelativeUrl(@f)/moveto(newurl=@n,flags=1)?@f='@{encodeUriComponent(replace(concat(uriPath(variables('SitoUrl')), '/', items('Per_ogni_allegato')?['{FullPath}']), '''', ''''''))}'&@n='@{encodeUriComponent(replace(concat(uriPath(variables('SitoUrl')), outputs('Percorso_cartella_nuovo_coordinatore'), '/', items('Per_ogni_allegato')?['{FilenameWithExtension}']), '''', ''''''))} …`
                <br>*Nota: Sposta il file nella cartella del nuovo coordinatore (sovrascrive).*
            - `Riassegna_richiesta` — **SharePoint – Aggiorna elemento** · lista *Richieste formazione* · ID `@items('Per_ogni_richiesta_da_riassegnare')?['ID']` · colonne: Title = `@items('Per_ogni_richiesta_da_riassegnare')?['Title']`, CoordinatoreLogin = `@outputs('Coordinatore_desiderato')?['login']`, CoordinatoreNome = `@outputs('Coordinatore_desiderato')?['nome']`, CoordinatoreEmail = `@outputs('Coordinatore_desiderato')?['email']`, AttestatoUrl = `@replace(coalesce(items('Per_ogni_richiesta_da_riassegnare')?['AttestatoUrl'], ''), concat …`, AltraDocUrl = `@replace(coalesce(items('Per_ogni_richiesta_da_riassegnare')?['AltraDocUrl'], ''), concat( …`, UltimaModificaDa = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`
            - `Registro_cambio_coordinatore` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Cambio coordinatore`, RichiestaRif = `@items('Per_ogni_richiesta_da_riassegnare')?['ID']`, IdRichiesta = `@{items('Per_ogni_richiesta_da_riassegnare')?['Title']}`, Tabella = `Richieste formazione`, IdRecord = `@{string(items('Per_ogni_richiesta_da_riassegnare')?['ID'])}`, Campo = `CoordinatoreLogin`, ValorePrecedente = `@{coalesce(items('Per_ogni_richiesta_da_riassegnare')?['CoordinatoreLogin'], '')}`, ValoreNuovo = `@{outputs('Coordinatore_desiderato')?['login']}`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`, Nota = `Richiesta aperta riassegnata; allegati spostati nella cartella del nuovo coordinatore.`
          - `Richieste_riassegnate_in_attesa` — **Filtra matrice** da `@body('Richieste_da_riassegnare')` dove `@equals(item()?['Stato']?['Value'], 'In attesa del coordinatore')`
          - `Se_avvisare_nuovo_coordinatore` — **Condizione** `@greater(length(body('Richieste_riassegnate_in_attesa')), 0)` è vero
            - **Se sì:**
              - `Righe_richieste_riassegnate` — **Seleziona** da `@body('Richieste_riassegnate_in_attesa')` → `@concat('<tr><td style="padding:6px 8px;border:1px solid #E1DFDD;vertical-align:top">', item()?['Title'], '</td><td style="padding:6px 8px;border:1px solid #E1DFDD;vertical-align:top">', replace(repla …`
              - `Email_nuovo_coordinatore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{if(empty(outputs('Coordinatore_desiderato')?['email']), outputs('Coordinatore_desiderato')?['login'], outputs('Coordinatore_desiderato')?['email'])}` · oggetto `Richieste di formazione assegnate a te – @{concat(triggerBody()?['Cognome'], ' ', triggerBody()?['Nome'])}`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])`
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_F9_SincronizzaRuoli

**Scopo.** Allinea i gruppi SharePoint alla lista *Ruoli applicativi*.

**Trigger.** **SharePoint – Quando un elemento viene creato o modificato** (`Quando_un_ruolo_viene_creato_o_modificato`) sulla lista *Ruoli applicativi*, controllo ogni 2 minuti, *Dividi in* attivo · concorrenza del trigger = 1 (esecuzioni una alla volta).

**Passaggi**
1. `Login_utente`: `Title` in minuscolo; se è vuoto, si ricava dalla persona *Utente*. Se il login è vuoto, non contiene `@` o è `Configurazione.AccountServizio`: fine, **senza toccare nulla**.
2. `Leggi_ruoli_utente`: tutti gli elementi con quel login. `Elenco_ruoli_attivi` = ruoli con *Attivo* = Sì. Più righe per la stessa persona sono gestite correttamente.
3. `Nome_accesso` = `i:0#.f|membership|<login>`. `Assicura_utente`: HTTP `POST _api/web/ensureuser` con corpo `{"logonName":"<nome accesso>"}`.
4. *Formazione HR* attivo:
   - sì: `POST _api/web/sitegroups/getbyname('Formazione - HR')/users` con `{"LoginName":"<nome accesso>"}`;
   - no: `POST .../users/removeByLoginName(@v)?@v='<nome accesso codificato>'`. Se l'utente non era nel gruppo la rimozione fallisce ed è previsto: l'azione successiva gira anche dopo un errore.
5. *Amministratore* attivo: stesso schema con `_api/web/AssociatedOwnerGroup/users` (Proprietari del sito).
6. Registro con l'esito.

Intestazioni delle richieste HTTP: `Accept` e `Content-Type` = `application/json;odata=nometadata`.

<details><summary>Elenco completo delle azioni di SDF_F9_SincronizzaRuoli</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Login_utente` — **Componi** `@toLower(trim(if(empty(trim(coalesce(triggerBody()?['Title'], ''))), last(split(coalesce(triggerBody()?['Utente']?['Claims'], ''), '|')), triggerBody()?['Title'])))`
  - `Account_servizio` — **Componi** `@toLower(trim(coalesce(outputs('Configurazione')?['AccountServizio'], '')))`
  - `Se_utente_da_ignorare` — **Condizione** `@or(empty(outputs('Login_utente')), not(contains(outputs('Login_utente'), '@')), equals(outputs('Login_utente'), outputs('Account_servizio')))` è vero
    <br>*Nota: Login vuoto o account di servizio: nessuna modifica ai gruppi.*
    - **Se sì:**
      - `Termina_utente_ignorato` — **Termina** (stato Succeeded)
  - `Leggi_ruoli_utente` — **SharePoint – Ottieni elementi** · lista *Ruoli applicativi* · $filter `Title eq '@{replace(string(outputs('Login_utente')), '''', '''''')}'` · $top 50
    <br>*Nota: Tutti gli elementi dell'utente: il gruppo dipende da tutti i ruoli attivi.*
  - `Ruoli_attivi_utente` — **Filtra matrice** da `@body('Leggi_ruoli_utente')?['value']` dove `@equals(item()?['Attivo'], true)`
  - `Elenco_ruoli_attivi` — **Seleziona** da `@body('Ruoli_attivi_utente')` → `@item()?['Ruolo']?['Value']`
  - `Nome_accesso` — **Componi** `@concat('i:0#.f|membership|', outputs('Login_utente'))`
  - `Assicura_utente` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/ensureuser` · corpo `{"logonName":"@{outputs('Nome_accesso')}"}`
    <br>*Nota: Registra l'utente nel sito se non c'è ancora.*
  - `Se_ruolo_HR` — **Condizione** `@contains(body('Elenco_ruoli_attivi'), 'Formazione HR')` è vero
    <br>*Nota: Gruppo SharePoint 'Formazione - HR'.*
    - **Se sì:**
      - `Aggiungi_a_HR` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/sitegroups/getbyname('Formazione - HR')/users` · corpo `{"LoginName":"@{outputs('Nome_accesso')}"}`
    - **Se no:**
      - `Rimuovi_da_HR` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/sitegroups/getbyname('Formazione - HR')/users/removeByLoginName(@v)?@v='@{encodeUriComponent(outputs('Nome_accesso'))}'`
      - `Rimozione_HR_gestita` — **Componi** `@actions('Rimuovi_da_HR')?['status']` — *esegui dopo: Rimuovi_da_HR (Succeeded, Failed)*
        <br>*Nota: Se l'utente non era nel gruppo la rimozione fallisce: è normale.*
  - `Se_ruolo_amministratore` — **Condizione** `@contains(body('Elenco_ruoli_attivi'), 'Amministratore')` è vero
    <br>*Nota: Gruppo Proprietari del sito.*
    - **Se sì:**
      - `Aggiungi_a_proprietari` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/AssociatedOwnerGroup/users` · corpo `{"LoginName":"@{outputs('Nome_accesso')}"}`
    - **Se no:**
      - `Rimuovi_da_proprietari` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/AssociatedOwnerGroup/users/removeByLoginName(@v)?@v='@{encodeUriComponent(outputs('Nome_accesso'))}'`
      - `Rimozione_proprietari_gestita` — **Componi** `@actions('Rimuovi_da_proprietari')?['status']` — *esegui dopo: Rimuovi_da_proprietari (Succeeded, Failed)*
        <br>*Nota: Se l'utente non era nel gruppo la rimozione fallisce: è normale.*
  - `Registro_sincronizzazione_ruoli` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Sincronizzazione gruppi SharePoint`, Tabella = `Ruoli applicativi`, IdRecord = `@{string(triggerBody()?['ID'])}`, Campo = `Ruolo`, ValoreNuovo = `@{if(empty(body('Elenco_ruoli_attivi')), 'nessun ruolo attivo', join(body('Elenco_ruoli_at …`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`, Nota = `@{concat('Utente ', outputs('Login_utente'), ': Formazione - HR = ', if(contains(body('Ele …`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])`
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

### SDF_F9b_RuoloEliminato

**Scopo.** Quando un elemento di *Ruoli applicativi* viene eliminato, toglie la persona dai gruppi.

**Trigger.** **SharePoint – Quando un elemento viene eliminato** (`Quando_un_ruolo_viene_eliminato`) sulla lista *Ruoli applicativi*, controllo ogni 2 minuti, *Dividi in* attivo · concorrenza del trigger = 1 (esecuzioni una alla volta).

**Passaggi.** Come F9, con il login preso dal campo `Name` del trigger, cioè il titolo dell'elemento eliminato, e senza `ensureuser`. Rileggendo gli elementi che restano, toglie la persona dal gruppo *Formazione - HR* solo se non ha più un ruolo HR attivo, e dai Proprietari solo se non ha più un ruolo Amministratore attivo. L'account di servizio non viene mai toccato.

<details><summary>Elenco completo delle azioni di SDF_F9b_RuoloEliminato</summary>

- `Inizializza_SitoUrl` — **Inizializza variabile** `SitoUrl` (string) = `"{{SITO_URL}}"`
- `Leggi_configurazione` — **SharePoint – Ottieni elementi** · lista *Configurazione* · $top 500
  <br>*Nota: Legge i parametri della lista Configurazione.*
- `Seleziona_configurazione` — **Seleziona** da `@body('Leggi_configurazione')?['value']` → oggetto con chiavi `@item()?['Title']`
- `Configurazione` — **Componi** `@json(replace(replace(replace(string(body('Seleziona_configurazione')),'[{','{'),'}]','}'),'},{',','))`
  <br>*Nota: Oggetto chiave/valore: outputs('Configurazione')?['EmailHR'], ?['AppUrl'], ...*
- `Prova` — **Ambito**
  - `Login_utente` — **Componi** `@toLower(trim(coalesce(triggerBody()?['Name'], '')))`
  - `Account_servizio` — **Componi** `@toLower(trim(coalesce(outputs('Configurazione')?['AccountServizio'], '')))`
  - `Se_utente_da_ignorare` — **Condizione** `@or(empty(outputs('Login_utente')), not(contains(outputs('Login_utente'), '@')), equals(outputs('Login_utente'), outputs('Account_servizio')))` è vero
    <br>*Nota: Login vuoto o account di servizio: nessuna modifica ai gruppi.*
    - **Se sì:**
      - `Termina_utente_ignorato` — **Termina** (stato Succeeded)
  - `Leggi_ruoli_utente` — **SharePoint – Ottieni elementi** · lista *Ruoli applicativi* · $filter `Title eq '@{replace(string(outputs('Login_utente')), '''', '''''')}'` · $top 50
    <br>*Nota: Tutti gli elementi dell'utente: il gruppo dipende da tutti i ruoli attivi.*
  - `Ruoli_attivi_utente` — **Filtra matrice** da `@body('Leggi_ruoli_utente')?['value']` dove `@equals(item()?['Attivo'], true)`
  - `Elenco_ruoli_attivi` — **Seleziona** da `@body('Ruoli_attivi_utente')` → `@item()?['Ruolo']?['Value']`
  - `Nome_accesso` — **Componi** `@concat('i:0#.f|membership|', outputs('Login_utente'))`
  - `Se_non_piu_HR` — **Condizione** `@not(contains(body('Elenco_ruoli_attivi'), 'Formazione HR'))` è vero
    - **Se sì:**
      - `Rimuovi_da_HR` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/sitegroups/getbyname('Formazione - HR')/users/removeByLoginName(@v)?@v='@{encodeUriComponent(outputs('Nome_accesso'))}'`
      - `Rimozione_HR_gestita` — **Componi** `@actions('Rimuovi_da_HR')?['status']` — *esegui dopo: Rimuovi_da_HR (Succeeded, Failed)*
        <br>*Nota: Se l'utente non era nel gruppo la rimozione fallisce: è normale.*
  - `Se_non_piu_amministratore` — **Condizione** `@not(contains(body('Elenco_ruoli_attivi'), 'Amministratore'))` è vero
    - **Se sì:**
      - `Rimuovi_da_proprietari` — **SharePoint – Invia una richiesta HTTP a SharePoint** · POST `_api/web/AssociatedOwnerGroup/users/removeByLoginName(@v)?@v='@{encodeUriComponent(outputs('Nome_accesso'))}'`
      - `Rimozione_proprietari_gestita` — **Componi** `@actions('Rimuovi_da_proprietari')?['status']` — *esegui dopo: Rimuovi_da_proprietari (Succeeded, Failed)*
        <br>*Nota: Se l'utente non era nel gruppo la rimozione fallisce: è normale.*
  - `Registro_sincronizzazione_ruoli` — **SharePoint – Crea elemento** · lista *Registro modifiche* · colonne: Title = `Ruolo eliminato: rimozione dai gruppi SharePoint`, Tabella = `Ruoli applicativi`, IdRecord = `@{string(triggerBody()?['ID'])}`, Campo = `Ruolo`, ValoreNuovo = `@{if(empty(body('Elenco_ruoli_attivi')), 'nessun ruolo attivo', join(body('Elenco_ruoli_at …`, Ruolo/Value = `Sistema`, LoginAutore = `@coalesce(outputs('Configurazione')?['AccountServizio'], 'sistema')`, Nota = `@{concat('Utente ', outputs('Login_utente'), ': Formazione - HR = ', if(contains(body('Ele …`
- `Errore` — **Ambito** — *esegui dopo: Prova (Failed, TimedOut)*
  <br>*Nota: Eseguito solo se 'Prova' non riesce: risponde con un errore generico e avvisa HR.*
  - `Link_esecuzione` — **Componi** `@concat('https://make.powerautomate.com/environments/', workflow()?['tags']?['environmentName'], '/flows/', workflow()?['name'], '/runs/', workflow()?['run']?['name'])`
  - `Azioni_non_riuscite` — **Filtra matrice** da `@result('Prova')` dove `@equals(item()?['status'], 'Failed')`
  - `Dettaglio_azioni_non_riuscite` — **Seleziona** da `@body('Azioni_non_riuscite')` → `@concat(item()?['name'], ': ', coalesce(item()?['error']?['message'], item()?['code'], ''))`
  - `Avvisa_HR_errore` — **Office 365 Outlook – Invia un messaggio di posta elettronica (V2)** · A `@{outputs('Configurazione')?['EmailHR']}` · oggetto `Errore nel flusso @{workflow()?['tags']?['flowDisplayName']}`
  - `Termina_con_errore` — **Termina** (stato Failed) — *esegui dopo: Avvisa_HR_errore (Succeeded, Failed, Skipped, TimedOut)*

</details>

---

## Dopo l'importazione: checklist

1. **Prerequisiti**
   - Sito e liste creati da `sharepoint/` (URL delle raccolte: `AllegatiFormazione`, `FilePaghe`).
   - Account di servizio con licenza Microsoft 365 e cassetta postale. Deve essere **Proprietario** del sito e, consigliato, **amministratore della raccolta siti**: serve al trigger *Quando un elemento viene eliminato* (F9b) e semplifica condivisioni e gruppi.
   - Lista *Configurazione* compilata: `AppUrl` si compila dopo la pubblicazione dell'app; `EmailHR`, `DestinatariPayroll`, `AccountServizio` = account di servizio in minuscolo, `Festivita` con il patrono locale.
   - Se si usa `MittenteEmail`, l'account di servizio deve avere il permesso **Invia come** su quella cassetta.
2. **Pacchetti.** `python powerautomate/crea_pacchetti.py --sito https://<tenant>.sharepoint.com/sites/GestioneFormazione` sostituisce `{{SITO_URL}}` con l'URL del sito e crea un pacchetto per flusso più `GestioneFormazione_tutti_i_flussi.zip`.
3. **Importazione.** Entrare in [make.powerautomate.com](https://make.powerautomate.com) **con l'account di servizio**, così i flussi sono suoi. Poi *I miei flussi → Importa → Importa pacchetto (legacy)*. Per ogni connessione scegliere *Seleziona durante l'importazione* e creare o selezionare la connessione dell'**account di servizio**: SharePoint, Office 365 Outlook e Office 365 Utenti (solo F7). Per ogni flusso scegliere *Crea come nuovo* e poi *Importa*. I flussi importati restano spenti.
4. Aprire ogni flusso nella finestra di progettazione: nessun errore, connessioni valide. Controllare i punti della sezione successiva e **Salvare**. Se la finestra di progettazione sostituisce il titolo della lista con il suo GUID nei trigger, va bene.
5. **Ordine di attivazione**:
   1. **SDF_F9_SincronizzaRuoli**;
   2. **SDF_F9b_RuoloEliminato**;
   3. **SDF_F7_AllineaLavoratore**;
   4. i 10 flussi **API** (SDF_API01 … SDF_API10);
   5. **SDF_F4_Promemoria**;
   6. **SDF_F5_RiepilogoMensile**.

   F9 e F7 reagiscono solo alle modifiche fatte **dopo** l'attivazione. Per allineare gruppi e lavoratori già caricati, modificare e salvare gli elementi (es. con una colonna in modifica rapida) oppure caricarli dopo aver attivato i flussi.
6. **App.** In Power Apps Studio: *Power Automate → Aggiungi flusso* e aggiungere i 10 flussi API. I nomi coincidono con quelli usati nelle formule (`SDF_API03_SalvaRichiesta.Run(...)`). In ogni flusso API, *Utenti solo esecuzione*: le connessioni devono restare **"Usa questa connessione"** (account di servizio), mai "Fornita dall'utente solo esecuzione". Basta condividere l'app: gli utenti non hanno accesso diretto alle liste riservate.
7. **Prove** (con utenti di test, vedi [docs/05-collaudo.md](../docs/05-collaudo.md)):
   1. API01 con un lavoratore, un coordinatore, un utente HR e un utente non censito;
   2. API04: e-mail e CF, poi CF errato (errore);
   3. API03: bozza senza allegati → modifica con attestato (si crea la cartella del coordinatore, condivisa in lettura) → invio (e-mail al coordinatore, registro). Poi errori R1/R3/R11, corso esterno nuovo (`EXT-…`), duplicato senza e con conferma, annullamento;
   4. API05 e API10 come coordinatore; API10 come altro coordinatore (deve rispondere "Richiesta non trovata o non autorizzata.");
   5. API06: approva con ore ridotte, respingi senza nota (errore), integrazione;
   6. API07: una richiesta, poi un perimetro di più di 25 richieste (risposta immediata ed e-mail di riepilogo);
   7. API08 chiudi → API09 (CSV in *File paghe*, aperto in Excel: accenti, virgole, colonne) → API08 riapri come HR (errore) e come Amministratore;
   8. F4 eseguito a mano con `GiorniAttesa` = 2, 4, 6; F5 eseguito a mano;
   9. F7: cambio del coordinatore di un lavoratore con richieste in attesa e allegati;
   10. F9/F9b: aggiunta, disattivazione ed eliminazione di un ruolo; verifica dei gruppi del sito.
8. Controllare in *Registro modifiche* che ogni prova abbia lasciato le sue righe e che gli errori imprevisti arrivino a `EmailHR` con il collegamento all'esecuzione.

## Punti da verificare dopo l'importazione

I file non sono stati esportati da un ambiente Power Automate. Sono stati controllati con `verifica_flussi.py` e le espressioni principali sono state provate con dati di esempio, ma non contro i connettori reali. Dopo l'importazione conviene controllare in particolare:

| Punto | Dove | Cosa controllare |
|---|---|---|
| Nomi delle operazioni e dei parametri SharePoint | tutti | `GetItems` (`$filter`, `$orderby`, `$top`), `PostItem`/`PatchItem` (`item/<Colonna>`, `item/<Scelta>/Value`), `PatchFileItem`, `CreateFile` (`folderPath`, `name`, `body`), `HttpRequest` (`parameters/method`, `parameters/uri`, `parameters/headers`, `parameters/body`). Nella finestra di progettazione nessun campo deve risultare vuoto o in errore |
| *Crea nuova cartella* | API03, F7 | parametro `parameters/path` (nome della cartella relativo alla raccolta) e output `ID` usato da *Concedi l'accesso*. Se l'output ha un altro nome, sostituirlo in `Condividi_cartella_*` |
| *Concedi l'accesso* | API03, F7 | `parameter/recipients`, `parameter/roleValue` = `role:1073741826` (Può visualizzare), `parameter/sendEmail` = false |
| *Ottieni modifiche per un elemento* | F7 | operazione `GetItemChanges`, parametri `id`, `since` = `@triggerOutputs()?['body/{TriggerWindowStartToken}']`, `includeDrafts`; output `ColumnHasChanged` |
| Output di *Crea file* | API03, API09 | `ItemId` (per *Aggiorna proprietà file*) e `Path` (percorso **relativo al sito**, es. `/AllegatiFormazione/...`). Se `Path` contenesse anche `/sites/...` l'URL risulterebbe doppio: in quel caso usare `concat('https://<tenant>.sharepoint.com', ...)` oppure `body(...)?['{Link}']` |
| Proprietà dei file letti con *Ottieni elementi* | F7 | `{FullPath}` e `{FilenameWithExtension}` per lo spostamento con `moveto` |
| Trigger SharePoint | F7, F9, F9b | `GetOnUpdatedItems` / `GetOnDeletedItems` con il **titolo** della lista come `table`, `splitOn`, ricorrenza 2 minuti, concorrenza 1. Nel trigger di eliminazione il titolo dell'elemento arriva nel campo `Name` |
| Colonne Collegamento ipertestuale | API03, F7, API09 | `AttestatoUrl`, `AltraDocUrl`, `FilePagheUrl` vengono scritte come testo (solo URL) e lette come testo |
| Colonna data `DataSessione` | API02/03/05/09/10, F5 | letta come `yyyy-MM-dd`. Se arrivasse come data/ora UTC, `norm_date` la converte nel fuso W. Europe |
| Mittente vuoto | tutte le e-mail | `emailMessage/From` = `coalesce(MittenteEmail, '')`: con valore vuoto Outlook deve usare l'account di servizio. Se il connettore rifiuta la stringa vuota, togliere il campo *Da* |
| Office 365 Utenti | F7 | `UserProfile_V2` con `id` = login; output `displayName` e `mail` |
| Funzioni `sort()` e `reverse()` | API02 | se l'ambiente non le riconosce, sostituire con `body('Mappa_richieste')`: l'ordine sarà per ID decrescente |
| Intestazione `x-ms-user-email` | API | contiene l'UPN/e-mail dell'utente dell'app. I valori `Login` di *Lavoratori* e `Title` di *Ruoli applicativi* devono corrispondere, in minuscolo |
| Ricorrenze | F4, F5 | F4: settimanale, lun–ven, ore 8:00; F5: mensile con *Ora di inizio* `2026-12-02T07:00:00` e fuso *W. Europe Standard Time* |
| Indicazione "Proteggi input/output" | API01, API03, API04, API05, API09, F7 | nascondono il CF nella cronologia. Per il debug si possono disattivare temporaneamente |

## Limiti noti

| Tema | Limite | Come è gestito |
|---|---|---|
| Richieste Power Platform | Con licenza Microsoft 365 ogni utente ha un numero limitato di richieste (azioni) al giorno, oggi 6.000 ogni 24 ore. Le azioni dei flussi automatici e pianificati sono attribuite al proprietario (account di servizio); per i flussi avviati da Power Apps Microsoft le attribuisce all'utente che li avvia. Verificare la pagina *Limiti e configurazione* di Power Automate | Ordine di grandezza delle azioni per chiamata: API01/02/05/10 ≈ 15–25; API03 ≈ 70–100 (con allegati); API06 ≈ 30; API07 ≈ 25 + 10 per richiesta; API08 ≈ 30 + 1 per richiesta; API09 ≈ 45 + 1 per richiesta; F4 ≈ 10 + 4–8 per richiesta in attesa al giorno; F5 ≈ 25 + 8 per coordinatore; F7 ≈ 15 per modifica + 6 per richiesta riassegnata. Oltre ~2.000 richieste al mese conviene chiudere per area |
| Licenza M365 e prestazioni | I flussi dei piani Microsoft 365 girano con il profilo di prestazioni più basso | Letture in parallelo, risposta anticipata nei flussi lunghi |
| Tempo massimo di Power Apps | Power Apps attende la risposta per **120 secondi** | API07 oltre 25 richieste, API08 e API09 rispondono prima degli aggiornamenti in blocco. API03 con allegati grandi può avvicinarsi al limite: limitare nell'app la dimensione dei file (es. 10 MB ciascuno) |
| Soglia di visualizzazione SharePoint (5.000) | Le liste grandi superano 5.000 elementi | Ogni filtro parte da una colonna indicizzata; ordinamenti solo su `ID` o colonne indicizzate. Ogni lettura restituisce al massimo **5.000** elementi (`$top` 5000; l'impaginazione oltre 5.000 non è disponibile con licenza Microsoft 365): API08/API09/F5 gestiscono fino a 5.000 richieste per mese |
| Codici fiscali nel file paghe | API09 legge i lavoratori nell'intervallo di ID delle richieste (massimo 5.000 elementi) | Le righe senza CF sono segnalate nella risposta e nell'e-mail ai destinatari payroll |
| Invio di e-mail | Exchange Online limita il numero di messaggi al minuto e al giorno per cassetta | Le elaborazioni massive (API07 su grandi perimetri, F4) possono rallentare per la limitazione del connettore: Outlook ritenta in automatico |
| Concorrenza | API07 e i cicli di aggiornamento usano una concorrenza di 10, F5 di 5, F7/F9/F9b eseguono un elemento alla volta | Evita conflitti di scrittura e la limitazione di SharePoint (600 chiamate al minuto per connessione) |
| Allegati | Arrivano come data URI in un parametro di testo | Dimensione limitata dalla richiesta HTTP verso il flusso: tenere i file piccoli (PDF/JPG) |
| Ordine delle richieste in API02 | `Modified` non è indicizzata | Lettura per `ID desc` (massimo 5.000 per lavoratore), poi ordinamento nel flusso |

## Verifica dei file

```bash
python3 powerautomate/verifica_flussi.py
```

Lo script controlla:
- JSON valido e struttura dell'involucro;
- nomi delle azioni unici;
- `runAfter` verso azioni sorelle esistenti, senza cicli;
- ogni `body()`, `outputs()`, `actions()`, `result()`, `items()` e `variables()`: l'azione o la variabile deve esistere, essere raggiungibile ed eseguita **prima**;
- sintassi delle espressioni e nomi delle funzioni;
- parametri del trigger Power Apps;
- connessioni dichiarate e usate, `operationId` noti;
- `{{SITO_URL}}` usato una sola volta nelle azioni;
- variabili inizializzate al primo livello;
- risposte e Termina fuori dai cicli;
- colonne, filtri e valori delle scelte confrontati con `sharepoint/schema.yaml` (richiede PyYAML).

Esce con codice 1 se trova errori.
