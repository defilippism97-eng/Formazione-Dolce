# 2. Modello dati SharePoint

> Documento generato automaticamente da `sharepoint/schema.yaml` con `python sharepoint/genera_template.py`. Non modificarlo a mano.

Sito: **Gestione ore formazione** (indirizzo suggerito `/sites/GestioneFormazione`), sito del team **senza** gruppo Microsoft 365, lingua italiana.

Le colonne si leggono così: *nome visualizzato* (usato dall'app Power Apps) e `nome interno` (usato dai flussi e nei filtri). Le colonne indicizzate (🔎) permettono di filtrare liste oltre la soglia dei 5.000 elementi. I collegamenti tra liste sono ID numerici (es. *ID lavoratore*).

## Gruppi e permessi

| Gruppo | Descrizione | Permesso sul sito |
|---|---|---|
| Proprietari del sito | Amministratori applicativi e account di servizio dei flussi | Controllo completo |
| Formazione - HR | Ufficio HR/Formazione: lettura di tutte le liste, modifica anagrafica lavoratori. Membri gestiti dal flusso F9 a partire dalla lista Ruoli applicativi. | Lettura |
| Formazione - Paghe | Ufficio Paghe: lettura dei soli file paghe. | — |

| Lista / raccolta | Permessi |
|---|---|
| Richieste formazione | ereditati dal sito (Proprietari: controllo completo; Formazione - HR: lettura) |
| Lavoratori | ereditati dal sito + Formazione - HR: Collaborazione |
| Strutture organizzative | ereditati dal sito (Proprietari: controllo completo; Formazione - HR: lettura) |
| Catalogo corsi | ereditati dal sito + Tutti tranne gli utenti esterni: Lettura |
| Chiusure mensili | ereditati dal sito + Tutti tranne gli utenti esterni: Lettura |
| Registro modifiche | ereditati dal sito (Proprietari: controllo completo; Formazione - HR: lettura) |
| Ruoli applicativi | ereditati dal sito (Proprietari: controllo completo; Formazione - HR: lettura) |
| Configurazione | ereditati dal sito (Proprietari: controllo completo; Formazione - HR: lettura) |
| Allegati formazione | ereditati dal sito (Proprietari: controllo completo; Formazione - HR: lettura); ogni cartella coordinatore è condivisa in lettura con il coordinatore (flusso API03) |
| File paghe | ereditarietà interrotta + Proprietari del sito: Controllo completo + Formazione - HR: Lettura + Formazione - Paghe: Lettura |

## Liste e raccolte

### Richieste formazione

Lista · URL `Lists/RichiesteFormazione` · Richieste di riconoscimento delle ore di formazione. Scrittura solo tramite i flussi API; lettura diretta solo per HR e amministratori.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **ID richiesta** | `Title` | Testo (una riga) | colonna titolo rinominata |
| Login lavoratore | `LavoratoreLogin` | Testo (una riga) | 🔎 indicizzata |
| ID lavoratore | `LavoratoreRif` | Numero intero |  |
| Cognome | `Cognome` | Testo (una riga) |  |
| Nome | `Nome` | Testo (una riga) |  |
| E-mail personale | `EmailPersonale` | Testo (una riga) |  |
| Area | `Area` | Scelta | valori: Area Nord Ovest, Area Centro, Area Educativa, Area Socio Sanitaria, Area Staff |
| Servizio | `Servizio` | Testo (una riga) | 🔎 indicizzata |
| Centro di costo | `CentroDiCosto` | Testo (una riga) | 🔎 indicizzata |
| ID struttura | `StrutturaRif` | Numero intero |  |
| Login coordinatore | `CoordinatoreLogin` | Testo (una riga) | 🔎 indicizzata |
| Coordinatore | `CoordinatoreNome` | Testo (una riga) |  |
| E-mail coordinatore | `CoordinatoreEmail` | Testo (una riga) |  |
| ID corso | `CorsoRif` | Numero intero |  |
| Codice univoco corso | `CodiceCorso` | Testo (una riga) | 🔎 indicizzata |
| Titolo del corso a catalogo | `TitoloCorsoCatalogo` | Testo (una riga) |  |
| Titolo corso libero | `TitoloCorsoLibero` | Testo (una riga) |  |
| Durata complessiva corso | `DurataCorso` | Numero (2 decimali) |  |
| Ente erogatore | `EnteErogatore` | Scelta | valori: Datore di lavoro, Committente o altro soggetto; Datore di lavoro = corso interno; Committente o altro soggetto = corso esterno |
| Modalità di svolgimento | `Modalita` | Scelta | valori: In presenza, A distanza - sincrona, A distanza - asincrona |
| Più giornate formative | `PiuGiornate` | Sì/No |  |
| Data sessione formativa | `DataSessione` | Data | 🔎 indicizzata |
| Ora inizio sessione | `OraInizioSessione` | Testo (una riga) | HH:mm |
| Ora fine sessione | `OraFineSessione` | Testo (una riga) |  |
| Durata sessione | `DurataSessione` | Numero (2 decimali) | Ore (fine - inizio sessione) |
| Ora ingresso lavoratore | `OraIngresso` | Testo (una riga) |  |
| Ora uscita lavoratore | `OraUscita` | Testo (una riga) |  |
| Ore frequentate dichiarate | `OreFrequentate` | Numero (2 decimali) |  |
| Ore retribuite richieste | `OreRetribuiteRichieste` | Numero (2 decimali) |  |
| Ore gettone richieste | `OreGettoneRichieste` | Numero (2 decimali) |  |
| Ore retribuite riconosciute coordinatore | `OreRetribuiteCoord` | Numero (2 decimali) |  |
| Ore gettone riconosciute coordinatore | `OreGettoneCoord` | Numero (2 decimali) |  |
| Ore retribuite approvate HR | `OreRetribuiteHR` | Numero (2 decimali) |  |
| Ore gettone approvate HR | `OreGettoneHR` | Numero (2 decimali) |  |
| Attestato | `AttestatoUrl` | Collegamento ipertestuale |  |
| Altra documentazione | `AltraDocUrl` | Collegamento ipertestuale |  |
| Attestato presente | `AttestatoPresente` | Sì/No |  |
| Note del lavoratore | `NoteLavoratore` | Testo (più righe) |  |
| Note del coordinatore | `NoteCoordinatore` | Testo (più righe) |  |
| Note HR | `NoteHR` | Testo (più righe) |  |
| Stato richiesta | `Stato` | Scelta | valori: Bozza, Inviata al coordinatore, In attesa del coordinatore, Integrazione richiesta dal coordinatore, Respinta dal coordinatore, Approvata dal coordinatore, In attesa di validazione HR, Integrazione richiesta da HR, Respinta da HR, Validata da HR, Inclusa nel riepilogo mensile, Inviata a Payroll, Annullata; predefinito: Bozza; 🔎 indicizzata |
| Data invio | `DataInvio` | Data e ora |  |
| Data approvazione coordinatore | `DataApprovazioneCoord` | Data e ora |  |
| Data validazione HR | `DataValidazioneHR` | Data e ora |  |
| Mese di competenza | `MeseCompetenza` | Numero intero | 🔎 indicizzata |
| Anno di competenza | `AnnoCompetenza` | Numero intero | 🔎 indicizzata |
| Periodo chiusura | `PeriodoChiusura` | Testo (una riga) | AAAA-MM della chiusura mensile che ha incluso la richiesta |
| Conferma partecipazione | `ConfermaPartecipazione` | Sì/No |  |
| Conferma correttezza dati | `ConfermaCorrettezza` | Sì/No |  |
| Autorizzazione all'invio | `AutorizzazioneInvio` | Sì/No |  |
| Possibile duplicato | `PossibileDuplicato` | Sì/No |  |
| Anomalie rilevate | `Anomalie` | Testo (più righe) |  |
| Giorni lavorativi in attesa | `GiorniAttesa` | Numero intero |  |
| Sollecito segnalato a HR | `SegnalataHR` | Sì/No |  |
| Utente ultima modifica | `UltimaModificaDa` | Testo (una riga) | Login di chi ha eseguito l'ultima azione (le scritture avvengono tramite l'account di servizio) |

### Lavoratori

Lista · URL `Lists/Lavoratori` · Anagrafica dei lavoratori e assegnazione organizzativa corrente.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **Nominativo** | `Title` | Testo (una riga) | colonna titolo rinominata |
| Utente Microsoft 365 | `UtenteM365` | Persona |  |
| Login Microsoft 365 | `Login` | Testo (una riga) | obbligatoria; valori univoci; 🔎 indicizzata; UPN in minuscolo, es. mario.rossi@societadolce.it |
| Cognome | `Cognome` | Testo (una riga) | obbligatoria |
| Nome | `Nome` | Testo (una riga) | obbligatoria |
| E-mail aziendale | `EmailAziendale` | Testo (una riga) |  |
| E-mail personale | `EmailPersonale` | Testo (una riga) | Inserita dal lavoratore al primo accesso: riceve qui le notifiche |
| Codice fiscale | `CodiceFiscale` | Testo (una riga) |  |
| Codice fiscale (mascherato) | `CFMascherato` | Testo (una riga) |  |
| Codice fiscale registrato | `CFRegistrato` | Sì/No |  |
| ID struttura | `StrutturaRif` | Numero intero |  |
| Area | `Area` | Scelta | valori: Area Nord Ovest, Area Centro, Area Educativa, Area Socio Sanitaria, Area Staff |
| Servizio | `Servizio` | Testo (una riga) |  |
| Centro di costo | `CentroDiCosto` | Testo (una riga) | 🔎 indicizzata |
| Coordinatore assegnato | `Coordinatore` | Persona |  |
| Login coordinatore | `CoordinatoreLogin` | Testo (una riga) | 🔎 indicizzata |
| Nome coordinatore | `CoordinatoreNome` | Testo (una riga) |  |
| E-mail coordinatore | `CoordinatoreEmail` | Testo (una riga) |  |
| Stato lavoratore | `StatoLavoratore` | Scelta | valori: Attivo, Non attivo; predefinito: Attivo; 🔎 indicizzata |
| Data inizio validità assegnazione | `InizioAssegnazione` | Data |  |
| Data fine validità assegnazione | `FineAssegnazione` | Data |  |
| Segnalazione variazione dati | `SegnalazioneVariazione` | Testo (più righe) |  |
| Segnalazione da gestire | `SegnalazioneAperta` | Sì/No | 🔎 indicizzata |

### Strutture organizzative

Lista · URL `Lists/StruttureOrganizzative` · Organigramma: un elemento per servizio / centro di costo.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **Servizio** | `Title` | Testo (una riga) | colonna titolo rinominata |
| Area | `Area` | Scelta | valori: Area Nord Ovest, Area Centro, Area Educativa, Area Socio Sanitaria, Area Staff; obbligatoria |
| Centro di costo | `CentroDiCosto` | Testo (una riga) | obbligatoria; 🔎 indicizzata |
| Coordinatore responsabile | `CoordinatoreResponsabile` | Persona |  |
| Coordinatore servizio | `CoordinatoreServizio` | Persona |  |
| Login coordinatore servizio | `CoordinatoreServizioLogin` | Testo (una riga) |  |
| E-mail coordinatore servizio | `EmailCoordinatoreServizio` | Testo (una riga) |  |
| Data inizio validità | `DataInizioValidita` | Data |  |
| Data fine validità | `DataFineValidita` | Data |  |
| Struttura attiva | `Attiva` | Sì/No | predefinito: Sì |

### Catalogo corsi

Lista · URL `Lists/CatalogoCorsi` · Catalogo dei corsi aziendali e corsi esterni inseriti dai lavoratori. Leggibile da tutti gli utenti dell'app.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **Titolo corso** | `Title` | Testo (una riga) | colonna titolo rinominata |
| Codice univoco corso | `CodiceCorso` | Testo (una riga) | 🔎 indicizzata; Interni: codice HR. Esterni: EXT-<ID> generato dal flusso |
| Descrizione | `Descrizione` | Testo (più righe) |  |
| Ente erogatore | `EnteErogatore` | Scelta | valori: Datore di lavoro, Committente o altro soggetto; obbligatoria; 🔎 indicizzata |
| Nome ente erogatore | `NomeEnte` | Testo (una riga) |  |
| Tipologia | `Tipologia` | Testo (una riga) |  |
| Modalità di svolgimento | `Modalita` | Scelta | valori: In presenza, A distanza - sincrona, A distanza - asincrona |
| Durata corso | `DurataCorso` | Numero (2 decimali) | Ore |
| Gettone previsto | `GettonePrevisto` | Sì/No |  |
| Corso attivo | `CorsoAttivo` | Sì/No | predefinito: Sì; 🔎 indicizzata |
| Più giornate formative | `PiuGiornate` | Sì/No |  |
| Origine | `Origine` | Scelta | valori: Catalogo aziendale, Inserito dal lavoratore; predefinito: Catalogo aziendale |
| Stato validazione | `StatoValidazione` | Scelta | valori: Da validare, Validato, Scartato; predefinito: Validato; 🔎 indicizzata |
| Login autore | `LoginAutore` | Testo (una riga) | 🔎 indicizzata; Corsi esterni: lavoratore che li ha inseriti (storico personale) |

### Chiusure mensili

Lista · URL `Lists/ChiusureMensili` · Stato dei periodi mensili e file paghe generati. Leggibile da tutti gli utenti dell'app (per bloccare i mesi chiusi).

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **Periodo** | `Title` | Testo (una riga) | colonna titolo rinominata |
| Mese | `Mese` | Numero intero | obbligatoria |
| Anno | `Anno` | Numero intero | obbligatoria; 🔎 indicizzata |
| Stato del periodo | `StatoPeriodo` | Scelta | valori: Aperto, Chiuso, Riaperto; predefinito: Aperto |
| Data chiusura | `DataChiusura` | Data e ora |  |
| Utente chiusura | `UtenteChiusura` | Testo (una riga) |  |
| Numero richieste incluse | `NumeroRichieste` | Numero intero |  |
| Totale ore riconosciute | `TotaleOreRiconosciute` | Numero (2 decimali) |  |
| Totale gettoni | `TotaleGettoni` | Numero (2 decimali) |  |
| File paghe generato | `FilePagheGenerato` | Sì/No |  |
| File paghe | `FilePagheUrl` | Collegamento ipertestuale |  |
| Versione file paghe | `VersioneFile` | Numero intero |  |
| Note HR | `NoteHR` | Testo (più righe) |  |
| Data riapertura | `DataRiapertura` | Data e ora |  |
| Utente riapertura | `UtenteRiapertura` | Testo (una riga) |  |
| Motivo riapertura | `MotivoRiapertura` | Testo (più righe) |  |

### Registro modifiche

Lista · URL `Lists/RegistroModifiche` · Storico delle azioni di lavoratori, coordinatori, HR, amministratori e flussi.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **Azione** | `Title` | Testo (una riga) | colonna titolo rinominata |
| ID elemento richiesta | `RichiestaRif` | Numero intero | 🔎 indicizzata |
| ID richiesta | `IdRichiesta` | Testo (una riga) |  |
| Lista | `Tabella` | Testo (una riga) |  |
| ID elemento | `IdRecord` | Testo (una riga) |  |
| Campo | `Campo` | Testo (una riga) |  |
| Valore precedente | `ValorePrecedente` | Testo (più righe) |  |
| Valore nuovo | `ValoreNuovo` | Testo (più righe) |  |
| Ruolo | `Ruolo` | Scelta | valori: Lavoratore, Coordinatore, Formazione HR, Amministratore, Sistema |
| Login autore | `LoginAutore` | Testo (una riga) | 🔎 indicizzata |
| Nota | `Nota` | Testo (più righe) |  |

### Ruoli applicativi

Lista · URL `Lists/RuoliApplicativi` · Utenti con ruolo Formazione HR o Amministratore. Il flusso F9 allinea i gruppi SharePoint.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **Login** | `Title` | Testo (una riga) | colonna titolo rinominata |
| Utente | `Utente` | Persona |  |
| Ruolo | `Ruolo` | Scelta | valori: Formazione HR, Amministratore; obbligatoria |
| Attivo | `Attivo` | Sì/No | predefinito: Sì |
| Note | `NoteRuolo` | Testo (più righe) |  |

### Configurazione

Lista · URL `Lists/Configurazione` · Parametri letti dai flussi (chiave/valore).

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| **Chiave** | `Title` | Testo (una riga) | colonna titolo rinominata |
| Valore | `Valore` | Testo (più righe) |  |
| Descrizione | `Descrizione` | Testo (più righe) |  |

Valori iniziali:

| Chiave | Valore | Descrizione |
|---|---|---|
| `AppUrl` | `https://apps.powerapps.com/play/e/<ID-AMBIENTE>/a/<ID-APP>?tenantId...` | Collegamento web dell'app: i flussi aggiungono &richiesta=<ID> per aprire direttamente una richiesta |
| `EmailHR` | `formazione@societadolce.it` | Casella dell'Ufficio HR/Formazione che riceve segnalazioni e riepiloghi |
| `MittenteEmail` | `` | Facoltativo: cassetta condivisa da cui inviare le e-mail (l'account di servizio deve avere il permesso Invia come). Vuoto = account di servizio |
| `DestinatariPayroll` | `paghe@societadolce.it;formazione@societadolce.it` | Destinatari del collegamento al file paghe, separati da punto e virgola |
| `SitoUrl` | `https://societadolce.sharepoint.com/sites/GestioneFormazione` | URL di questo sito |
| `AccountServizio` | `svc-formazione@societadolce.it` | Account di servizio dei flussi: non viene mai tolto dai gruppi dal flusso F9 |
| `LinkResetPassword` | `https://password.societadolce.it/` | Pagina di reimpostazione della password |
| `Festivita` | `["2026-01-01","2026-01-06","2026-04-06","2026-04-25","2026-05-01","...` | Giorni festivi (AAAA-MM-GG) esclusi dal conteggio dei giorni lavorativi. Aggiungere il patrono locale e aggiornare ogni anno |

### Allegati formazione

Raccolta documenti · URL `AllegatiFormazione` · Attestati e documenti delle richieste. Una cartella per coordinatore, condivisa in sola lettura con il coordinatore dal flusso API03.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| ID elemento richiesta | `RichiestaRif` | Numero intero | 🔎 indicizzata |
| ID richiesta | `IdRichiesta` | Testo (una riga) |  |
| Tipo allegato | `TipoAllegato` | Scelta | valori: Attestato, Altra documentazione |
| Login lavoratore | `LavoratoreLogin` | Testo (una riga) | 🔎 indicizzata |

### File paghe

Raccolta documenti · URL `FilePaghe` · File CSV mensili per l'Ufficio Paghe.

| Nome visualizzato | Nome interno | Tipo | Dettagli |
|---|---|---|---|
| Periodo | `Periodo` | Testo (una riga) | 🔎 indicizzata |
| Numero richieste | `NumeroRichieste` | Numero intero |  |

## Colori degli stati

| Stato | Colore |
|---|---|
| Bozza | `#8A8886` |
| Inviata al coordinatore | `#0078D4` |
| In attesa del coordinatore | `#0078D4` |
| Integrazione richiesta dal coordinatore | `#CA5010` |
| Respinta dal coordinatore | `#D13438` |
| Approvata dal coordinatore | `#498205` |
| In attesa di validazione HR | `#8764B8` |
| Integrazione richiesta da HR | `#CA5010` |
| Respinta da HR | `#D13438` |
| Validata da HR | `#107C10` |
| Inclusa nel riepilogo mensile | `#005B70` |
| Inviata a Payroll | `#004E8C` |
| Annullata | `#605E5C` |
