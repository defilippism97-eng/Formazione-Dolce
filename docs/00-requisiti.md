# 0. Requisiti originali

> Documento di analisi fornito da Società Dolce ("Analisi processo formazione per creazione APP"), riportato senza modifiche come riferimento.

```text
Crea una app denominata “Gestione ore formazione” per digitalizzare il processo di rilevazione, approvazione e rendicontazione delle ore di formazione dei lavoratori di Società Dolce.

OBIETTIVO

Sostituire il foglio cartaceo delle ore di formazione con un’applicazione digitale utilizzabile da lavoratori, coordinatori e Ufficio HR/Formazione.

Il processo deve seguire questa logica:

LAVORATORE
→ COORDINATORE DEL LAVORATORE
→ UFFICIO HR/FORMAZIONE
→ ESPORTAZIONE MENSILE PER L’UFFICIO PAGHE

La soluzione deve essere composta da:

1. Power App Canvas responsive
2. Tabelle Dataverse per l’archiviazione dei dati
3. Flussi Power Automate per notifiche e approvazioni
4. Riepiloghi mensili per coordinatore, servizio, centro di costo e divisione
5. Esportazione finale dei dati approvati per l’Ufficio Paghe

RUOLI UTENTE

Prevedere quattro ruoli.

1. LAVORATORE

Il lavoratore deve poter:

- visualizzare esclusivamente le proprie richieste;
- creare una nuova richiesta di riconoscimento della formazione;
- salvare una richiesta in bozza;
- inviare la richiesta al proprio coordinatore;
- allegare un attestato o altra documentazione;
- visualizzare lo stato della richiesta;
- modificare una richiesta solo se è in bozza o se il coordinatore o HR richiedono un’integrazione;
- visualizzare eventuali note del coordinatore o di HR;
- annullare una richiesta non ancora approvata.

I dati anagrafici e organizzativi del lavoratore devono essere compilati automaticamente utilizzando l’account Microsoft 365 e la tabella dell’organigramma associata attraverso l'APP alla sua identità Microsoft.

2. COORDINATORE

Il coordinatore deve poter:

- visualizzare esclusivamente le richieste dei lavoratori assegnati;
- filtrare le richieste per mese, lavoratore, servizio, centro di costo e stato;
- aprire il dettaglio della singola richiesta;
- verificare corso, data, orari, ore frequentate, ore richieste e allegati;
- approvare la richiesta;
- respingere la richiesta indicando una motivazione;
- richiedere un’integrazione al lavoratore indicando cosa deve essere corretto;
- modificare, se autorizzato, le ore riconosciute rispetto alle ore richieste;
- visualizzare il riepilogo mensile del proprio gruppo di lavoro;
- visualizzare il totale delle ore e degli eventuali gettoni del mese.

3. UFFICIO HR/FORMAZIONE

L’Ufficio HR/Formazione deve poter:

- visualizzare tutte le richieste approvate dai coordinatori;
- consultare anche le richieste respinte o in attesa;
- filtrare per mese, anno, area, servizio, centro di costo, coordinatore, lavoratore, corso e stato;
- verificare e validare le richieste approvate dai coordinatori;
- modificare le ore effettivamente riconosciute;
- modificare il valore del gettone riconosciuto;
- respingere una richiesta indicando la motivazione;
- richiedere un’integrazione al lavoratore e al coordinatore;
- visualizzare gli allegati;
- visualizzare il quadro completo mensile della formazione;
- chiudere il mese;
- generare il file finale per l’Ufficio Paghe;
- visualizzare richieste duplicate, attestati mancanti e dati incompleti.

4. AMMINISTRATORE 

L’amministratore deve poter:

- gestire gli utenti e i ruoli;
- aggiornare l’organigramma;
- associare ogni lavoratore al proprio coordinatore;
- aggiornare il catalogo dei corsi a partire dai titoli dei corsi inseriti dai lavoratori e approvati dai coordinatori;
- gestire aree, servizi e centri di costo;
- riaprire eccezionalmente un mese già chiuso;

TABELLE DATAVERSE

Crea le seguenti tabelle collegate tra loro.

TABELLA “LAVORATORI”

Campi:

- Utente da Microsoft 365
- Cognome
- Nome 
- E-mail aziendale (se in possesso)
- Area
- Servizio
- Centro di costo
- Coordinatore
- E-mail coordinatore
- Stato lavoratore, attivo o non attivo
- Data inizio validità dell’assegnazione
- Data fine validità dell’assegnazione

TABELLA “RICHIESTE FORMAZIONE”

Campi:

- ID richiesta, generato automaticamente;
- Utente da Microsoft 365;
- Cognome;
- Nome;
- E-mail aziendale (se in possesso);
- Area;
- Servizio;
- Centro di costo;
- Coordinatore associato;
- Codice univoco corso;
- Durata complessiva corso (in ore);
- Titolo del corso a catalogo;
- Titolo corso libero, utilizzabile soltanto se il corso non è presente nel catalogo
- Corso interno/esterno (interno - Datore di lavoro; esterno - Committente o altro soggetto)
- Modalità di svolgimento; (in presenza; A Distanza - Sincrona; A Distanza - Asincrona)
- Data sessione formativa;
- Ora di inizio sessione formativa;
- Ora di fine sessione formativa;
- Durata sessione formativa; (Ora di inizio - Ora di fine); N.B. La durata complessiva delle sessioni formative associate allo stesso codice univoco corso deve essere coincidente con Durata complessiva Corso
- Ora di ingresso lavoratore;
- Ora di uscita lavoratore;
- Ore frequentate dichiarate; (Ora di ingresso - Ora di uscita)
- Ore retribuite richieste;
- Ore gettone richieste; 
- Ore retribuite riconosciute dal coordinatore;
- Ore gettone riconosciute dal coordinatore;
- Ore retribuite approvate definitivamente da HR;
- Ore gettone riconosciute definitivamente da HR;
- Attestato o altri allegati;
- Note del lavoratore;
- Note del coordinatore;
- Note HR;
- Stato della richiesta;
- Data creazione;
- Data invio;
- Data approvazione coordinatore;
- Data validazione HR;
- Mese di competenza;
- Anno di competenza;
- Data ultima modifica;
- Utente ultima modifica;

TABELLA “CATALOGO CORSI”

Campi:

- Codice univoco corso;
- Titolo corso;
- Descrizione;
- Ente erogatore;
- Tipologia;
- Durata corso;
- Gettone previsto; (se "no" allora non selezionabile dal lavoratore)
- Corso attivo, sì o no; (se "no" allora non selezionabile dal lavoratore)

TABELLA “STRUTTURA ORGANIZZATIVA”

Campi:

- Area (Area Nord Ovest; Area Centro, Area Educativa; Area Socio Sanitaria; Area Staff);
- Coordinatore responsabile;
- Centro di costo;
- Coordinatore servizio;
- Servizio;
- E-mail coordinatore servizio;
- Data inizio validità;
- Data fine validità;
- Struttura attiva, sì o no;

TABELLA “CHIUSURE MENSILI”

Campi:

- Mese;
- Anno;
- Periodo;
- Stato del periodo;
- Data chiusura;
- Utente che ha effettuato la chiusura;
- Numero richieste incluse;
- Totale ore riconosciute;
- Totale gettoni;
- File paghe generato;
- Note HR;

STATI DELLA RICHIESTA

Configurare i seguenti stati:

- Bozza;
- Inviata al coordinatore;
- In attesa del coordinatore;
- Integrazione richiesta dal coordinatore;
- Respinta dal coordinatore;
- Approvata dal coordinatore;
- In attesa di validazione HR;
- Integrazione richiesta da HR;
- Respinta da HR;
- Validata da HR;
- Inclusa nel riepilogo mensile;
- Inviata a Payroll;
- Annullata;

SCHERMATE DELL’APP

Creare le seguenti schermate.

0. LOGIN
- inserisci nome utente Microsoft 365;
- inserisci password;

-->login

Hai dimenticato la password? Reset su https://password.societadolce.it/

1. HOME PAGE

Mostrare:

- nome dell’utente loggato;
- ruolo nell'applicativo (lavoratore; coordinatore; Formazione HR; Amministratore);
- numero di richieste aperte; (se Coordinatore o HR)
- numero di richieste da approvare; (se Coordinatore o HR)
- messaggi relativi a integrazioni richieste; (se Coordinatore o HR)
- inserisci formazione; (tutti)
- formazione approvata; (tutti)
- formazione in attesa di approvazione e/o richieste di integrazione; (tutti)
- riepilogo formazione; (tutti)
- altri collegamenti rapidi alle principali funzioni (reportistica, generazione file per payroll).

Il contenuto della Home Page deve cambiare in base al ruolo dell’utente.

2. LE MIE RICHIESTE

Destinata al lavoratore.

Mostrare una raccolta con:

- numero richiesta;
- data corso;
- titolo corso;
- ore richieste;
- stato;
- data ultima modifica.

Prevedere filtri per anno, mese e stato.

Aggiungere il pulsante “Nuova richiesta”.

3. NUOVA RICHIESTA

Creare un modulo suddiviso in sezioni.

Sezione dati del lavoratore:

- nome e cognome; (da login 365)
- e-mail di contatto; (da inserire la prima volta, poi resta in memoria)
- codice fiscale; (da inserire la prima volta poi resta in memoria) 
- area;  il dato scende in automatico da TABELLA “STRUTTURA ORGANIZZATIVA”, non modificabile direttamente dal lavoratore ma possibilità di segnalare cambio ad HR 
- servizio; il dato scende in automatico da TABELLA “STRUTTURA ORGANIZZATIVA”, non modificabile direttamente dal lavoratore ma possibilità di segnalare cambio ad HR 
- centro di costo;  il dato scende in automatico da TABELLA “STRUTTURA ORGANIZZATIVA”, non modificabile direttamente dal lavoratore ma possibilità di segnalare cambio ad HR 
- coordinatore; il dato scende in automatico da TABELLA “STRUTTURA ORGANIZZATIVA”, non modificabile direttamente dal lavoratore ma possibilità di segnalare cambio ad HR 


Sezione attività formativa:

- ente erogatore (Datore di lavoro / Committente o altro soggetto);

se si seleziona "Datore di lavoro" allora il corso è a catalogo, quindi il flusso:

- titolo del corso - catalogo; (si può fare ricerca testuale ma non modificare i titoli) 
- codice univoco corso; (campo non modificabile)
- modalità di svolgimento; (campo non modificabile)
- data di svolgimento;
- ora ingresso;
- ora uscita;
- ore frequentate;
- ore retribuite richieste;
- ore gettone richieste;
- note.

se si seleziona "Committente o altro soggetto" allora il corso NON è a catalogo, quindi il flusso:

- titolo del corso - libero o selezionabile da storico; 
- codice univoco corso; (codice progressivo, si crea automaticamente la prima volta ed è ri-selezionabile le volte successive)
- modalità di svolgimento; (In presenza, Formazione a distanza)
- data svolgimento;
- durata complessiva corso;
- previste più giornate formative? (si/no); se risposta è si allora selezionabile nelle volte successive; 
- ora ingresso;
- ora uscita;
- ore totali sessione formativa;
- ore retribuite richieste;
- ore gettone richieste;
- note.


Sezione allegati:

- attestato rilasciati;
- altra documentazione.

Sezione dichiarazioni:

- conferma della partecipazione;
- conferma della correttezza dei dati;
- autorizzazione all’invio della richiesta.

Pulsanti:

- Salva bozza
- Invia al coordinatore
- Annulla
- Torna alle richieste

4. RICHIESTE DEL TEAM

Destinata al coordinatore.

Mostrare una raccolta delle richieste dei propri collaboratori.

Filtri:

- mese;
- anno;
- lavoratore;
- servizio;
- centro di costo;
- stato.

Mostrare:

- lavoratore; 
- corso;
- data;
- ore formazione svolta;
- ore retribuite richieste;
- ore gettone richieste;
- ore retribuite riconosciute;
- ore gettone riconosciute;
- stato lavoratore;


5. DETTAGLIO E APPROVAZIONE DEL COORDINATORE

Mostrare tutti i dati della richiesta ed eventuali allegati.

Consentire al coordinatore di:

- inserire le ore retribuite e gettone riconosciute;
- inserire note;
- approvare in toto la richiesta;
- respingere in toto la richiesta;
- richiedere integrazione.

6. VALIDAZIONE HR

Mostrare tutte le richieste approvate dai coordinatori.

Consentire a HR di:

- modificare le ore retribuite riconosciute;
- modificare le ore gettone;
- validare in toto la richiesta del singolo lavoratore o di un intero perimetro; (coordinatore; centro di costo; servizio; area;)
- respoingere in toto la richiesta del singolo lavoratore o di un intero perimetro; (coordinatore; centro di costo; servizio; area;)- richiedere integrazione;
- visualizzare lo storico delle modifiche sulla singola richiesta.

7. RIEPILOGO MENSILE

Creare una schermata destinata a coordinatori e HR.

Per il coordinatore mostrare solo i dati del proprio gruppo.

Per HR mostrare il quadro completo.

Filtri:

- mese;
- anno;
- area;
- servizio;
- centro di costo;
- coordinatore;
- lavoratore;
- stato.

Indicatori:

- numero lavoratori coinvolti; (conteggio distinto su login Microsoft 365);
- numero richieste totali;
- totale ore frequentate;
- totale ore retribuite richieste;
- totale ore gettone richieste;
- totale ore retribuite approvate dai coordinatori;
- totale ore gettone approvate dai coordinatori;
- totale ore retribuite approvate da HR;
- totale ore gettone approvate da HR;
- elenco richieste in attesa di approvazione da coordinatori;
- elenco richieste respinte da coordinatori;

Tabella di dettaglio con i dati della singola richiesta


8. CHIUSURA MENSILE HR

Consentire a HR di:

- verificare eventuali richieste ancora aperte;
- visualizzare le anomalie;
- chiudere il mese;
- impedire modifiche successive alla chiusura;
- generare il file per Payroll; 
- riaprire il mese solo se l’utente ha il ruolo di amministratore.

FLUSSI 

Creare i seguenti flussi.

FLUSSO 1: INVIO AL COORDINATORE

Quando il lavoratore invia una richiesta:

- verificare che i campi obbligatori siano compilati;
- recuperare il coordinatore dalla tabella ORGANIGRAMMA;
- impostare lo stato “In attesa del coordinatore”;
- registrare data e ora dell’invio;
- inviare al coordinatore una notifica tramite email aziendale - disponibile da ID Microsoft;
- includere nella notifica un collegamento diretto alla richiesta.

FLUSSO 2: ESITO DEL COORDINATORE

Se il coordinatore approva:

- registrare l’esito;
- salvare le ore riconosciute;
- impostare lo stato “In attesa di validazione HR”;
- notificare il lavoratore;
- rendere la richiesta visibile a HR.

Se il coordinatore respinge:

- richiedere obbligatoriamente una motivazione;
- impostare lo stato “Respinta dal coordinatore”;
- notificare il lavoratore.

Se il coordinatore richiede integrazione:

- impostare lo stato “Integrazione richiesta dal coordinatore”;
- notificare il lavoratore;
- consentire al lavoratore di modificare e reinviare la richiesta.

FLUSSO 3: VALIDAZIONE HR

Se HR valida:

- registrare ore e gettone definitivamente riconosciuti;
- impostare lo stato “Validata da HR”;
- notificare il lavoratore e il coordinatore.

Se HR respinge:

- registrare la motivazione;
- impostare lo stato “Respinta da HR”;
- notificare lavoratore e coordinatore.

Se HR richiede integrazione:

- impostare lo stato “Integrazione richiesta da HR”;
- notificare lavoratore e coordinatore;
- consentire la correzione della richiesta.

FLUSSO 4: PROMEMORIA

Eseguire il flusso ogni giorno lavorativo.

Inviare un promemoria:

- dopo 3 giorni lavorativi senza approvazione;
- dopo 5 giorni lavorativi senza approvazione;
- dopo 7 giorni lavorativi segnalare la richiesta anche a HR.

FLUSSO 5: RIEPILOGO MENSILE

Entro il quarto giorno del mese successivo:

- recuperare tutte le richieste del mese precedente;
- raggrupparle per coordinatore;
- inviare a ogni coordinatore il riepilogo del proprio gruppo;
- inviare a HR il quadro completo;
- evidenziare richieste ancora aperte, respinte o incomplete.

FLUSSO 6: ESPORTAZIONE PAYROLL

Dopo la chiusura HR:

- generare un file Excel o CSV;
- includere esclusivamente le richieste validate da HR;
- impostare lo stato “Inviata a Payroll”;
- archiviare il file nella raccolta documentale HR;
- inviare il collegamento al file agli utenti autorizzati.

Il file deve contenere:

- Codice fiscale;
- cognome;
- nome;
- area;
- servizio;
- centro di costo;
- mese;
- anno;
- titolo corso;
- data corso;
- ore retribuite riconosciute da HR;
- ore gettone riconosciute da HR;
- ID della richiesta.

REGOLE E CONTROLLI

Applicare i seguenti controlli:

- l’ora di fine deve essere successiva all’ora di inizio;
- le ore frequentate non possono essere negative;
- le ore richieste non possono essere superiori alle ore frequentate;
- le ore approvate non possono essere superiori alle ore frequentate;
- il gettone non può essere negativo;
- segnala richieste duplicate per stesso lavoratore, stesso corso e stessa data a coordinatore e HR;
- non consentire modifiche dopo la validazione HR;
- non consentire modifiche dopo la chiusura del mese;
- registrare tutte le variazioni effettuate da coordinatore, HR e amministratore.

SICUREZZA

Configurare la sicurezza in modo che:

- il lavoratore visualizzi solo le proprie richieste;
- il coordinatore visualizzi solo le richieste dei lavoratori assegnati;
- HR visualizzi tutte le richieste;
- l’amministratore gestisca configurazioni e autorizzazioni;
- gli allegati siano accessibili soltanto agli utenti autorizzati;
- le informazioni siano trattate nel rispetto della normativa sulla protezione dei dati personali.

INTERFACCIA

Utilizzare un’interfaccia semplice, responsive e coerente con l’identità visiva di Società Dolce.

Prevedere:

- intestazione con titolo dell’app;
- menu laterale;
- colori di stato facilmente riconoscibili;
- messaggi di conferma;
- messaggi di errore comprensibili;
- icone per approvare, respingere, modificare e visualizzare;
- visualizzazione ottimizzata per computer, tablet e smartphone.

```
