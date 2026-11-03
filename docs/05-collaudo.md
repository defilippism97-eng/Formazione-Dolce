# 5. Piano di collaudo (UAT)

**Utenti di test necessari** (in un ambiente sandbox):

| Utente | Ruolo | Note |
|---|---|---|
| `test.lavoratore1` | Lavoratore | con casella di posta aziendale |
| `test.lavoratore2` | Lavoratore | **senza** casella di posta (notifiche all'e-mail di contatto) |
| `test.coord` | Coordinatore + Lavoratore | coordinatore di lavoratore1 e lavoratore2 |
| `test.coord2` | Coordinatore | coordinatore di un altro servizio |
| `test.hr` | Formazione HR | |
| `test.admin` | Amministratore | |

Dati: almeno 2 strutture, 3 corsi a catalogo (uno con *Gettone previsto = No*, uno con *Più giornate = Sì* e durata 12 ore).

Esito: ✅ superato · ❌ fallito (annotare il dettaglio) · ⏭ non eseguito.

## A. Accesso e home page

| ID | Ruolo | Passi | Risultato atteso | Esito |
|---|---|---|---|---|
| A1 | Lavoratore | Aprire l'app | Schermata di benvenuto con nome, e-mail, ruolo "Lavoratore" e link "Hai dimenticato la password?" verso https://password.societadolce.it/ | |
| A2 | Utente non censito | Aprire l'app con un utente presente nel gruppo ma non in *Lavoratori* | Messaggio "Utente non censito: contatta l'Ufficio HR/Formazione"; nessun accesso ai dati | |
| A3 | Coordinatore | Home | Ruolo "Coordinatore"; riquadri richieste aperte / da approvare / integrazioni; voce di menu "Richieste del team" | |
| A4 | HR | Home | Ruolo "Formazione HR"; collegamenti a Validazione, Riepilogo, Chiusura e file payroll | |
| A5 | Admin | Home | Ruolo "Amministratore"; voce "Amministrazione" | |
| A6 | Tutti | Aprire l'app da smartphone e da tablet | Layout leggibile senza scorrimento orizzontale; menu laterale apribile con l'icona ☰ | |

## B. Lavoratore – richiesta

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| B1 | Nuova richiesta, primo accesso | Nome e cognome precompilati; area, servizio, centro di costo e coordinatore in sola lettura; e-mail di contatto e codice fiscale richiesti | |
| B2 | Inserire un CF formalmente errato | Messaggio d'errore, salvataggio bloccato | |
| B3 | Inserire CF corretto e salvare | Al successivo accesso il CF compare mascherato e non va reinserito | |
| B4 | "Segnala variazione a HR" con un testo | Conferma a video; HR riceve un'e-mail; in Chiusura mensile la segnalazione compare tra le anomalie | |
| B5 | Ente "Datore di lavoro": cercare un corso per parte del titolo | Elenco filtrato del catalogo attivo; codice, modalità e durata non modificabili | |
| B6 | Corso con *Gettone previsto = No* | Campo ore gettone disabilitato a 0 | |
| B7 | Ora fine sessione ≤ ora inizio | Errore R1, invio bloccato | |
| B8 | Ingresso 9:00, uscita 12:30 | Ore frequentate calcolate = 3,5 | |
| B9 | Ore retribuite 3 + gettone 1 con frequentate 3,5 | Errore R3 | |
| B10 | Salva bozza senza allegati | Richiesta in stato **Bozza** visibile in "Le mie richieste" | |
| B11 | Riaprire la bozza, allegare un PDF come attestato, spuntare le 3 dichiarazioni, "Invia al coordinatore" | Stato "Inviata al coordinatore", poi entro 1–2 minuti **"In attesa del coordinatore"**; il coordinatore riceve l'e-mail con il collegamento diretto | |
| B12 | Invia senza dichiarazioni | Invio bloccato con messaggio chiaro | |
| B13 | Ente "Committente o altro soggetto", nuovo corso con *Più giornate = Sì*, durata 8 ore, sessione da 4 ore | Il corso viene creato con codice `EXT-xxxxxx`; la richiesta lo usa | |
| B14 | Seconda richiesta sullo stesso corso esterno (da storico) con sessione da 5 ore | Errore R6: la somma delle sessioni (9) supera la durata del corso (8) | |
| B15 | Stessa data e stesso corso di una richiesta già inviata | Avviso di possibile duplicato; dopo l'invio la richiesta è marcata *Possibile duplicato* e coordinatore e HR vengono avvisati | |
| B16 | Annullare una richiesta "In attesa del coordinatore" | Stato "Annullata"; il coordinatore riceve un avviso; non è più modificabile | |
| B17 | Tentare di modificare una richiesta "In attesa del coordinatore" | Modulo in sola lettura | |
| B18 | Filtri anno/mese/stato in "Le mie richieste" | Elenco filtrato correttamente | |
| B19 | lavoratore2 (senza casella aziendale) invia una richiesta e riceve un esito | Le notifiche arrivano all'e-mail di contatto | |

## C. Coordinatore

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| C1 | "Richieste del team" | Solo richieste di lavoratore1 e lavoratore2, non quelle del team di coord2 | |
| C2 | Filtri mese, anno, lavoratore, servizio, centro di costo, stato | Funzionano e si combinano | |
| C3 | Aprire dal collegamento nell'e-mail | Si apre direttamente il dettaglio della richiesta | |
| C4 | Dettaglio: aprire l'attestato | Il file si apre | |
| C5 | Ridurre le ore retribuite riconosciute e approvare | Stato "Approvata dal coordinatore", poi **"In attesa di validazione HR"**; il lavoratore riceve l'e-mail con le ore riconosciute; nel registro: approvazione + variazione ore | |
| C6 | Ore riconosciute > ore frequentate | Errore R4 | |
| C7 | Respingi senza motivazione | Bloccato: motivazione obbligatoria | |
| C8 | Respingi con motivazione | Stato "Respinta dal coordinatore"; e-mail al lavoratore con la motivazione | |
| C9 | Richiedi integrazione con nota | Stato "Integrazione richiesta dal coordinatore"; il lavoratore può modificare e reinviare (torna "In attesa del coordinatore") | |
| C10 | `test.coord` invia una **propria** richiesta | Non può approvarla dalla schermata (pannello assente); la approva il suo coordinatore | |
| C11 | Riepilogo mensile | Solo il proprio gruppo; totali di ore e gettoni coerenti con il dettaglio | |
| C12 | coord2 prova ad aprire il collegamento di una richiesta del team di coord | Nessun dato visibile (record non condiviso) | |

## D. Ufficio HR / Formazione

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| D1 | Validazione HR | Tutte le richieste approvate dai coordinatori; filtri per mese, anno, area, servizio, centro di costo, coordinatore, lavoratore, corso, stato | |
| D2 | Modificare le ore HR e validare una richiesta | Stato "Validata da HR"; e-mail a lavoratore e coordinatore; registro con valori prima/dopo | |
| D3 | Validare un **perimetro** (es. tutto un centro di costo per ottobre) | Conferma con il numero di richieste; tutte validate; ore HR = ore del coordinatore dove non modificate | |
| D4 | Respingere con motivazione / richiedere integrazione | Stati corretti; e-mail a lavoratore **e** coordinatore | |
| D5 | Storico modifiche di una richiesta | Tutte le azioni, con autore, ruolo, data e valori | |
| D6 | Tentare di modificare una richiesta validata | Non consentito | |
| D7 | Riepilogo mensile completo | Indicatori: lavoratori coinvolti (conteggio distinto), richieste, ore frequentate, ore richieste, ore approvate da coordinatori e HR, elenchi in attesa e respinte | |
| D8 | Chiusura mensile: verifica | Richieste ancora aperte e anomalie (duplicati, attestati mancanti, dati incompleti, segnalazioni) | |
| D9 | Chiudere il mese | Avviso se ci sono richieste aperte; conferma; stato periodo **Chiuso**; entro pochi minuti: richieste validate → "Inclusa nel riepilogo mensile" → **"Inviata a Payroll"**; CSV nella cartella SharePoint; e-mail con il link ai destinatari | |
| D10 | Aprire il CSV in Excel | Colonne nell'ordine: Codice fiscale; Cognome; Nome; Area; Servizio; Centro di costo; Mese; Anno; Titolo corso; Data corso; Ore retribuite riconosciute HR; Ore gettone riconosciute HR; ID richiesta. Accenti corretti, decimali con la virgola | |
| D11 | Dopo la chiusura: lavoratore prova a inserire una richiesta con data nel mese chiuso | Bloccato (R9) | |
| D12 | HR prova a riaprire il mese | Pulsante non disponibile | |

## E. Amministratore

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| E1 | Creare una struttura e un lavoratore associato a un coordinatore | Area/servizio/centro di costo/coordinatore compilati da F7; il lavoratore vede i propri dati, il coordinatore vede il lavoratore | |
| E2 | Cambiare il coordinatore di un lavoratore con richieste aperte | Il nuovo coordinatore vede le richieste aperte | |
| E3 | Validare un corso esterno inserito da un lavoratore | Compare nell'elenco "da validare"; dopo la validazione è nel catalogo | |
| E4 | Riaprire un mese chiuso con motivazione | Stato "Riaperto"; motivazione, data e utente registrati; registro aggiornato | |
| E5 | Richiudere il mese riaperto dopo nuove validazioni | Nuovo file `…_v2.csv` con le sole richieste validate e non ancora inviate | |

## F. Flussi pianificati

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| F1 | Lasciare una richiesta "In attesa del coordinatore" ed eseguire F4 manualmente per 3, 5 e 7 giorni (oppure impostare *Giorni lavorativi in attesa* = 2, 4, 6 prima di ogni esecuzione) | Promemoria al 3° e al 5° giorno; al 7° anche e-mail a HR e *Sollecito segnalato a HR* = Sì | |
| F2 | Eseguire F4 in un giorno presente in `sdf_Festivita` | Il flusso termina senza contare il giorno | |
| F3 | Eseguire F5 manualmente | Ogni coordinatore riceve il riepilogo del proprio gruppo del mese precedente; HR riceve il quadro completo con aperte, respinte e incomplete evidenziate | |

## G. Sicurezza (con strumenti esterni all'app)

| ID | Passi | Risultato atteso | Esito |
|---|---|---|---|
| G1 | Lavoratore: aprire la tabella Richieste formazione in Excel (Dati → Da Dataverse) | Solo le proprie richieste | |
| G2 | Lavoratore: tentare via Web API di scrivere *Ore retribuite approvate HR* sulla propria richiesta | Errore di sicurezza a livello di colonna | |
| G3 | Coordinatore: leggere il codice fiscale di un lavoratore del team | Valore vuoto o nascosto | |
| G4 | coord approva via API una propria richiesta | F2 riporta lo stato a "In attesa del coordinatore" e avvisa HR | |
