# 5. Piano di collaudo (UAT)

**Utenti di prova:**

| Utente | Ruolo | Note |
|---|---|---|
| `test.lavoratore1` | Lavoratore | licenza Microsoft 365 di base, **senza** casella di posta |
| `test.lavoratore2` | Lavoratore | stesso coordinatore di lavoratore1 |
| `test.coord` | Coordinatore + Lavoratore | coordinatore di lavoratore1 e lavoratore2; a sua volta ha `test.coord2` come coordinatore |
| `test.coord2` | Coordinatore | coordinatore di un altro servizio |
| `test.hr` | Formazione HR | in *Ruoli applicativi* |
| `test.admin` | Amministratore | in *Ruoli applicativi* |

Dati: almeno 2 strutture e 3 corsi a catalogo, di cui uno con *Gettone previsto* = No e uno con *Più giornate* = Sì e durata 12 ore.

Esito: ✅ superato · ❌ fallito (annotare il dettaglio) · ⏭ non eseguito.

## A. Accesso, profilo e home page

| ID | Ruolo | Passi | Risultato atteso | Esito |
|---|---|---|---|---|
| A1 | Lavoratore | Aprire l'app (anche dalla intranet) | Nessuna richiesta di password oltre a quella di Microsoft 365; schermata di benvenuto con nome, ruolo e link "Hai dimenticato la password?" → https://password.societadolce.it/ | |
| A2 | Lavoratore, primo accesso | Entrare | Viene aperto **Il mio profilo**; senza e-mail personale e codice fiscale non si prosegue | |
| A3 | Lavoratore | E-mail personale non valida / CF errato | Messaggi d'errore chiari, salvataggio bloccato | |
| A4 | Lavoratore | Salvare e-mail personale e CF corretti | Si entra nella home; al successivo accesso il profilo non viene più richiesto; il CF appare mascherato | |
| A5 | Lavoratore | "Segnala variazione a HR" | Conferma a video; HR riceve un'e-mail; la segnalazione compare in Chiusura mensile tra le anomalie | |
| A6 | Utente non censito | Aprire l'app | "Utente non censito: contatta l'Ufficio HR/Formazione" | |
| A7 | Coordinatore / HR / Admin | Home | Ruolo corretto; riquadri e voci di menu del proprio ruolo | |
| A8 | Tutti | Smartphone e tablet | Layout leggibile senza scorrimento orizzontale; menu ☰ | |

## B. Lavoratore – richieste

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| B1 | Nuova richiesta | Dati del lavoratore precompilati e non modificabili | |
| B2 | Ente "Datore di lavoro": cercare un corso | Solo corsi a catalogo attivi e validati; codice, modalità e durata non modificabili | |
| B3 | Corso con *Gettone previsto* = No | Ore gettone disabilitate a 0 | |
| B4 | Ora fine sessione ≤ ora inizio | Errore R1 | |
| B5 | Ingresso 09:00, uscita 12:30 | Ore frequentate = 3,5 | |
| B6 | Retribuite 3 + gettone 1 con frequentate 3,5 | Errore R3, anche se si forzasse l'invio (il flusso lo rifiuta) | |
| B7 | Salva bozza con un attestato PDF | Stato **Bozza**; in "Le mie richieste" con *Attestato caricato* | |
| B8 | Riaprire la bozza, spuntare le dichiarazioni, "Invia al coordinatore" | Stato **In attesa del coordinatore**; il coordinatore riceve l'e-mail **aziendale** con il pulsante "Apri la richiesta" | |
| B9 | Inviare senza dichiarazioni | Invio bloccato | |
| B10 | Committente/altro soggetto, nuovo corso con *Più giornate* = Sì, durata 8, sessione da 4 ore | Corso creato con codice `EXT-xxxxxx` e stato "Da validare" | |
| B11 | Seconda sessione sullo stesso corso esterno (da storico) di 5 ore | Errore R6: 4 + 5 > 8 | |
| B12 | Stesso corso e stessa data di una richiesta già inviata | Richiesta di conferma "possibile duplicato"; dopo la conferma: *Possibile duplicato* su entrambe, avviso al coordinatore e a HR | |
| B13 | Annullare una richiesta in attesa del coordinatore | Stato **Annullata**; il coordinatore viene avvisato | |
| B14 | Tentare di modificare una richiesta in attesa del coordinatore | Sola lettura | |
| B15 | Ricevere un esito (approvazione, respingimento, integrazione) | E-mail all'**indirizzo personale** con lo stato e il link all'app | |
| B16 | Filtri anno/mese/stato in "Le mie richieste" | Corretti | |

## C. Coordinatore

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| C1 | Richieste del team | Solo le richieste di lavoratore1 e lavoratore2, senza le bozze | |
| C2 | Filtri mese, anno, lavoratore, servizio, centro di costo, stato | Corretti | |
| C3 | Aprire dal link nell'e-mail | Si apre il dettaglio della richiesta | |
| C4 | Aprire l'attestato | Il file si apre nel browser | |
| C5 | Ridurre le ore retribuite e approvare | Stato **In attesa di validazione HR**; e-mail al lavoratore con le ore riconosciute; registro con l'approvazione e la variazione delle ore | |
| C6 | Ore riconosciute > ore frequentate | Errore R4 | |
| C7 | Respingere senza motivazione | Bloccato | |
| C8 | Respingere con motivazione | Stato **Respinta dal coordinatore**; e-mail al lavoratore con la motivazione | |
| C9 | Chiedere un'integrazione | Il lavoratore modifica e reinvia; torna "In attesa del coordinatore" | |
| C10 | test.coord apre una **propria** richiesta | Nessun pulsante di approvazione: la approva test.coord2 | |
| C11 | Riepilogo mensile | Solo il proprio gruppo; totali coerenti | |
| C12 | test.coord2 apre il link di una richiesta del team di test.coord | "Richiesta non trovata o non autorizzata" | |

## D. Ufficio HR / Formazione

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| D1 | Validazione HR | Tutte le richieste in attesa di validazione; filtri per mese, anno, area, servizio, centro di costo, coordinatore, lavoratore, corso | |
| D2 | Modificare le ore HR e validare | Stato **Validata da HR**; e-mail a lavoratore (personale) e coordinatore (aziendale); registro con prima/dopo | |
| D3 | Validare un perimetro (es. un centro di costo, ottobre) | Conferma con il numero di richieste; tutte validate con le ore del coordinatore | |
| D4 | Validare oltre 25 richieste insieme | Messaggio "Elaborazione avviata…"; al termine e-mail di riepilogo | |
| D5 | Respingere / chiedere integrazione | Stati corretti, e-mail a entrambi | |
| D6 | Storico modifiche di una richiesta | Tutte le azioni con autore, ruolo, data, valori | |
| D7 | Riepilogo mensile completo | Tutti gli indicatori richiesti, compreso il conteggio distinto dei lavoratori | |
| D8 | Chiusura mensile: verifica | Richieste aperte e anomalie (duplicati, attestati mancanti, segnalazioni, CF mancanti) | |
| D9 | Chiudere il mese | Avviso sulle richieste aperte; periodo **Chiuso**; le richieste validate diventano **Inclusa nel riepilogo mensile** | |
| D10 | Generare il file paghe | CSV nella raccolta *File paghe*; richieste **Inviata a Payroll**; e-mail con il link ai destinatari | |
| D11 | Aprire il CSV con Excel | Colonne nell'ordine richiesto, accenti corretti, decimali con la virgola, CF presenti | |
| D12 | Lavoratore: nuova richiesta con data nel mese chiuso | Bloccata (R9) | |
| D13 | HR prova a riaprire il mese | Funzione non disponibile | |

## E. Amministratore

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| E1 | Aggiungere un lavoratore associandolo a struttura e coordinatore | Area, servizio e centro di costo compilati; il lavoratore può entrare | |
| E2 | Cambiare il coordinatore di un lavoratore con richieste in attesa | Le richieste passano al nuovo coordinatore, gli allegati sono nella sua cartella e riceve un avviso | |
| E3 | Aggiungere un utente HR in *Ruoli applicativi* | Entro pochi minuti è nel gruppo *Formazione - HR* e vede le funzioni HR | |
| E4 | Disattivare il ruolo | Esce dal gruppo; perde le funzioni HR | |
| E5 | Validare un corso esterno inserito da un lavoratore | Passa a "Validato" | |
| E6 | Riaprire un mese chiuso con motivazione | Stato **Riaperto**; motivazione, data e utente registrati | |
| E7 | Richiudere e rigenerare il file | Nuovo file `…_v2.csv` con le sole richieste validate dopo la riapertura | |

## F. Flussi pianificati

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| F1 | Richiesta in attesa del coordinatore; impostare *Giorni lavorativi in attesa* a 2, 4, 6 ed eseguire F4 manualmente dopo ogni modifica | Promemoria a 3 e 5; a 7 anche HR e *Sollecito segnalato a HR* = Sì | |
| F2 | Eseguire F4 con la data odierna inserita in `Festivita` | Il flusso termina senza contare il giorno | |
| F3 | Eseguire F5 manualmente | Riepilogo del mese precedente a ogni coordinatore e a HR, con aperte, respinte e incomplete evidenziate | |

## G. Sicurezza (provare **fuori** dall'app)

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| G1 | Lavoratore: aprire nel browser `…/sites/GestioneFormazione/Lists/RichiesteFormazione` | Accesso negato | |
| G2 | Lavoratore: aprire *Catalogo corsi* | Sola lettura | |
| G3 | Coordinatore: aprire la lista *Lavoratori* o *Richieste formazione* | Accesso negato | |
| G4 | Coordinatore: aprire la cartella allegati di un altro coordinatore | Accesso negato | |
| G5 | HR: tentare di modificare una richiesta direttamente in SharePoint | Non consentito (solo lettura) | |
| G6 | Cercare il nome di un lavoratore nella ricerca della intranet | Nessun risultato dalle liste della soluzione | |
