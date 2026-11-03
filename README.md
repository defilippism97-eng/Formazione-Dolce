# Gestione ore formazione – Società Dolce

App per **digitalizzare il foglio delle ore di formazione**:

**Lavoratore → Coordinatore → Ufficio HR/Formazione → Ufficio Paghe**

Realizzata con gli strumenti **già inclusi in Microsoft 365**: nessuna licenza premium, nessun pagamento a consumo.

| | |
|---|---|
| App | Power Apps **Canvas** responsive: PC, tablet, smartphone, pagina della intranet |
| Dati | **SharePoint**: sito riservato con 8 liste e 2 raccolte documenti |
| Logica e sicurezza | **Power Automate**: 10 flussi "API" che controllano chi chiama + 5 flussi automatici (notifiche, promemoria, riepiloghi, ruoli) |
| Notifiche | Lavoratori → **e-mail personale** inserita al primo accesso · Coordinatori → e-mail aziendale · HR → casella HR |
| Ruoli | Lavoratore · Coordinatore · Formazione HR · Amministratore |

## Struttura del repository

```
docs/
  00-requisiti.md            requisiti originali
  01-architettura.md         architettura, ruoli, stati, regole, schermate, flussi  ← partire da qui
  02-modello-dati.md         liste, colonne, permessi (generato da schema.yaml)
  03-sicurezza.md            modello di sicurezza e GDPR
  04-installazione.md        guida all'installazione passo passo
  05-collaudo.md             piano di test per ruolo
  06-api-flussi.md           contratto tra app e flussi
sharepoint/
  schema.yaml                modello dati: fonte unica di verità
  genera_template.py         genera il modello PnP e la documentazione
  template/GestioneFormazione.xml   modello PnP (liste, colonne, viste, gruppi, permessi)
  Installa-GestioneFormazione.ps1   crea sito, liste, permessi, ruoli e importa i dati
  seed/                      modelli CSV (strutture, corsi, lavoratori)
powerautomate/
  flows/*.json               definizioni dei flussi
  crea_pacchetti.py          crea i pacchetti .zip da importare in Power Automate
  pacchetti/                 pacchetti pronti per il sito /sites/GestioneFormazione
  README.md                  descrizione dei flussi e verifiche dopo l'importazione
powerapps/
  src/*.pa.yaml              formule e schermate dell'app (formato YAML di Power Apps)
  formule/                   formule principali commentate
  README.md                  come costruire l'app dal sorgente
```

## Come si installa (in breve)

1. Account di servizio e registrazione app PnP: IT, una sola volta.
2. `sharepoint/Installa-GestioneFormazione.ps1` crea sito, liste e permessi e importa strutture, corsi e lavoratori.
3. Importare i flussi da `powerautomate/pacchetti/` con l'account di servizio.
4. Creare l'app Power Apps seguendo `powerapps/README.md`, pubblicarla e inserire il suo link nella lista *Configurazione*.
5. Attivare i flussi, collaudare con `docs/05-collaudo.md`, pubblicare l'app nella intranet.

Dettagli in [docs/04-installazione.md](docs/04-installazione.md).

## Da sapere

- **Login.** Si entra con l'account Microsoft 365, lo stesso della intranet. Un'app Power Apps non può chiedere nome utente e password al proprio interno, e non sarebbe sicuro. La schermata iniziale mostra l'utente collegato e il link *"Hai dimenticato la password?"* → https://password.societadolce.it/.
- **Sicurezza.** Lavoratori e coordinatori non accedono direttamente alle liste: leggono e scrivono tramite flussi che verificano l'identità e le regole. Così ognuno vede solo ciò che gli spetta e nessuno può modificare le approvazioni.
- **Prestazioni.** Ogni salvataggio o caricamento del lavoratore passa da un flusso e richiede qualche secondo: è il prezzo della soluzione a costo zero.
- **Identità visiva.** I colori dell'app sono nelle formule iniziali (`colPrimario` e simili): sostituirli con quelli ufficiali di Società Dolce.
- **Da confermare** con HR e Paghe: i punti aperti in [docs/01-architettura.md §1.10](docs/01-architettura.md#110-punti-aperti-da-confermare-con-società-dolce).

## Modificare il modello dati

1. Modificare `sharepoint/schema.yaml`.
2. `python sharepoint/genera_template.py` rigenera il modello PnP e la documentazione.
3. Rilanciare `Installa-GestioneFormazione.ps1`, che aggiunge ciò che manca.
4. Aggiornare flussi e app se usano le nuove colonne, e il contratto in `docs/06-api-flussi.md`.
