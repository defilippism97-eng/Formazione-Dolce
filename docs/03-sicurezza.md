# 3. Sicurezza e protezione dei dati

La sicurezza è applicata **in Dataverse**, non solo nell'app: anche chi accede ai dati con altri strumenti (Excel, API, altre app) vede e modifica solo ciò che il suo ruolo consente. L'app nasconde in più pulsanti e schermate non pertinenti, ma non è l'unica barriera.

## 3.1 Livelli di protezione

| Livello | Misura | Come si configura |
|---|---|---|
| Identità | Accesso solo con account Microsoft 365 / Entra ID (SSO), con MFA e accesso condizionale secondo le policy aziendali | Entra ID (IT) |
| Ambiente | L'ambiente Power Platform è limitato a un **gruppo di sicurezza** (es. `GRP-Formazione-Utenti`): gli altri utenti del tenant non vi accedono | Interfaccia di amministrazione di Power Platform → Ambiente → Modifica → Gruppo di sicurezza |
| Ruoli | Ruoli `SDF - Lavoratore`, `SDF - Formazione HR`, `SDF - Amministratore`, più il ruolo standard *Basic User* | `provision.py` (passo `roles`) |
| Righe | Proprietà del record e condivisione automatica da parte dei flussi | Ruoli + flussi F1 e F7 |
| Colonne | Profili di sicurezza delle colonne per esiti, ore definitive e codice fiscale | `provision.py` (passo `colsec`) |
| Allegati | Colonne *File* sulla richiesta: stessa visibilità del record | Modello dati |
| Integrità | I flussi F2 e F3 annullano le transizioni non autorizzate e avvisano HR; audit Dataverse; *Registro modifiche* | Flussi + audit |
| Connettori | Criterio DLP: Dataverse, Office 365 Outlook e SharePoint nel gruppo *Business*, gli altri bloccati nell'ambiente | Interfaccia di amministrazione → Criteri → Criteri dati |

## 3.2 Gruppi, team e ruoli

Si creano in Microsoft Entra ID quattro gruppi di sicurezza. Ogni gruppo è collegato a un **team Dataverse di tipo "Gruppo Microsoft Entra"**, così chi entra o esce dal gruppo ottiene o perde i permessi in automatico.

| Gruppo Entra (nome suggerito) | Team Dataverse | Ruoli Dataverse | Profilo colonne | Chi ne fa parte |
|---|---|---|---|---|
| `GRP-Formazione-Lavoratori` | SDF Lavoratori | SDF - Lavoratore | SDF - Lettura esiti | tutti gli utenti dell'app |
| `GRP-Formazione-Coordinatori` | SDF Coordinatori | SDF - Lavoratore | SDF - Coordinatori | i coordinatori |
| `GRP-Formazione-HR` | SDF Formazione HR | SDF - Formazione HR | SDF - Formazione HR | Ufficio HR/Formazione |
| `GRP-Formazione-Admin` | SDF Amministratori | SDF - Amministratore + SDF - Formazione HR | SDF - Formazione HR | amministratori applicativi |

A tutti gli utenti va assegnato anche il ruolo standard **Basic User** (Utente di base), di norma assegnandolo al team `SDF Lavoratori`.

Se in `config.json` si indicano gli Object ID dei gruppi, `provision.py` crea i team e assegna ruoli e profili. Altrimenti si procede a mano: *Impostazioni → Utenti e autorizzazioni → Team → Nuovo team → Tipo: Gruppo di sicurezza Microsoft Entra*, poi *Gestisci ruoli di sicurezza*, quindi *Sicurezza → Profili di sicurezza delle colonne → (profilo) → Team → Aggiungi*.

### Matrice dei permessi

| Tabella | Lavoratore | Coordinatore | Formazione HR | Amministratore |
|---|---|---|---|---|
| Richieste formazione | crea; legge e modifica **solo le proprie** | in più: legge e modifica quelle **condivise da F1** (il suo team) | legge e modifica **tutte** | tutte (senza eliminazione) |
| Lavoratori | legge **solo il proprio** record (condiviso da F7) | in più: legge quelli del team (condivisi da F7) | legge e modifica tutti | gestione completa |
| Catalogo corsi | legge tutto; crea corsi esterni | come lavoratore | gestione | gestione completa |
| Strutture organizzative | lettura | lettura | lettura | gestione completa |
| Chiusure mensili | lettura | lettura | crea e modifica | crea e modifica (riapertura) |
| Registro modifiche | crea; legge i propri | crea; legge quelli delle richieste del team | crea; legge tutto | crea; legge tutto |

Nessun ruolo applicativo può **eliminare** richieste o righe del registro: lo storico non si cancella.

## 3.3 Sicurezza a livello di riga

- **Richieste.** Il proprietario è il lavoratore che crea la richiesta. Quando la richiesta viene inviata, il flusso **F1** la condivide (Lettura, Scrittura, Aggiungi, Aggiungi a) con il coordinatore assegnato. Se l'amministratore cambia il coordinatore di un lavoratore, il flusso **F7** condivide con il nuovo coordinatore le richieste ancora aperte.
- **Lavoratori.** Sono di proprietà dell'amministratore o del team. F7 li condivide in sola lettura con il lavoratore e con il suo coordinatore. Il lavoratore **non può modificare** la propria anagrafica né il proprio coordinatore: i dati personali (e-mail di contatto, CF) e le segnalazioni di variazione passano dal flusso **F8**, che verifica l'identità di chi chiama.
- **Registro modifiche.** La relazione con la richiesta è di tipo *padre-figlio*: chi ha accesso alla richiesta vede anche il suo storico.

## 3.4 Sicurezza a livello di colonna

| Colonne protette | Lettura | Scrittura |
|---|---|---|
| Ore retribuite/gettone riconosciute dal coordinatore, Note del coordinatore, Data approvazione coordinatore | tutti gli utenti dell'app | coordinatori, HR, amministratori |
| Ore retribuite/gettone approvate HR, Note HR, Data validazione HR | tutti gli utenti dell'app | HR, amministratori |
| **Codice fiscale** (tabella Lavoratori) | HR, amministratori, account di servizio | HR, amministratori, account di servizio (flusso F8) |

L'app mostra al lavoratore solo il **CF mascherato** (es. `RSS**********X1`). Il CF in chiaro compare solo nel file paghe generato dal flusso F6.

## 3.5 Account di servizio dei flussi

Le connessioni dei flussi vanno create con un account dedicato, ad esempio `svc-formazione@societadolce.it`:

- licenza Power Automate / Power Apps adeguata e cassetta postale (oppure permesso *Invia come* su una cassetta condivisa, es. `formazione@societadolce.it`);
- ruolo **System Administrator** nell'ambiente: serve per condividere i record e scrivere la colonna protetta del CF;
- accesso in scrittura alla cartella SharePoint del file paghe;
- MFA o criteri di accesso condizionale come previsto per gli account di servizio aziendali; password e credenziali gestite dall'IT.

## 3.6 Integrità del processo e rafforzamenti opzionali

Il lavoratore deve poter scrivere sulla propria richiesta (bozze, integrazioni). Dataverse da solo non può quindi impedirgli, ad esempio via API, di impostare uno stato non consentito. Le contromisure previste sono:

1. **colonne protette:** il lavoratore non può scrivere ore riconosciute né note di coordinatore e HR;
2. **controllo dei flussi:** F2 verifica che l'approvazione arrivi dal coordinatore assegnato e non dal proprietario (un coordinatore non può approvare le proprie richieste). F3 verifica le transizioni HR. In caso di anomalia lo stato viene ripristinato e HR riceve un'e-mail;
3. **audit Dataverse:** registra chi ha modificato cosa e quando, anche fuori dall'app.

Per un **blocco preventivo** lato server, cioè per rifiutare la modifica invece di correggerla dopo, si può aggiungere un **plug-in Dataverse** (C#) registrato su *Update* di `sdf_richiestaformazione` in fase *PreOperation*. Il plug-in verifica:
- che la transizione di stato sia ammessa per il ruolo dell'utente (vedi la tabella in [01-architettura.md §1.3](01-architettura.md#13-ciclo-di-vita-della-richiesta-macchina-a-stati));
- che non si modifichino richieste *Validata da HR* o successive;
- che non si modifichino richieste di un periodo con *Chiusura mensile* = Chiuso, salvo per gli amministratori.

È consigliato se l'app viene estesa ad altri canali o se l'audit interno lo richiede.

## 3.7 Audit

1. Interfaccia di amministrazione di Power Platform → Ambiente → **Impostazioni → Audit e log** → attivare *Avvia controllo*, *Registra accesso* e impostare il periodo di conservazione.
2. Le tabelle della soluzione hanno già il controllo attivo (`IsAuditEnabled`), impostato da `provision.py`.
3. La cronologia è consultabile da un'app basata su modello o con *Cronologia controllo*. Lo storico **leggibile nell'app** è la tabella *Registro modifiche*, scritta dall'app e dai flussi a ogni azione di lavoratore, coordinatore, HR, amministratore e sistema.

## 3.8 Protezione dei dati personali (GDPR)

Elementi da condividere con il **DPO** e l'Ufficio Privacy di Società Dolce prima dell'avvio:

| Tema | Indicazione |
|---|---|
| Finalità | Gestione e rendicontazione delle ore di formazione; riconoscimento economico (retribuzione / gettone) tramite l'Ufficio Paghe; adempimenti sulla formazione obbligatoria |
| Base giuridica | Esecuzione del contratto di lavoro e obblighi di legge (art. 6.1 b, c GDPR), da confermare con il DPO |
| Informativa | Aggiornare l'informativa ai lavoratori (art. 13) indicando il nuovo strumento; l'app può riportarla nella schermata di benvenuto |
| Registro dei trattamenti | Aggiornare il registro (art. 30) con il nuovo trattamento e i responsabili (Microsoft come responsabile del trattamento ai sensi del DPA) |
| Minimizzazione | Sulle richieste non c'è il CF; i coordinatori non vedono il CF; gli allegati sono visibili solo a chi vede la richiesta |
| Localizzazione | Creare l'ambiente nell'area geografica **Europa** |
| Conservazione | Definire i tempi di conservazione di richieste, allegati e file paghe (es. allineati alla documentazione paghe), poi pianificare la cancellazione o l'archiviazione, ad esempio con un flusso annuale o le regole di conservazione dei dati a lungo termine di Dataverse |
| Diritti degli interessati | HR può estrarre tutte le richieste di un lavoratore (filtro per lavoratore nel riepilogo) |
| Controllo a distanza | L'app registra le azioni di processo (invii, approvazioni), non monitora l'attività lavorativa. Verificare con il DPO e le relazioni sindacali gli aspetti dell'art. 4 L. 300/1970 |
| Sicurezza del file paghe | Cartella SharePoint con permessi limitati a HR e Paghe; il collegamento inviato per e-mail funziona solo per gli utenti autorizzati |

## 3.9 Rischi residui noti

| Rischio | Mitigazione |
|---|---|
| Un coordinatore che è anche lavoratore potrebbe scrivere le colonne del coordinatore sulle **proprie** richieste via API | F2 annulla l'approvazione e avvisa HR; plug-in opzionale (§3.6) |
| Cambiato il coordinatore, il precedente conserva l'accesso in lettura alle richieste già condivise | Le richieste restano consultabili dal precedente coordinatore. Se non è accettabile, aggiungere a F7 la revoca (`RevokeAccess`) |
| Volumi sopra le 2.000 richieste per filtro nel riepilogo dell'app | Filtrare per periodo/perimetro; per analisi massive usare Power BI sulle stesse tabelle (rispetta la sicurezza di Dataverse) |
