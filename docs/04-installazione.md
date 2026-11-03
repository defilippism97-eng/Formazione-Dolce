# 4. Guida all'installazione

Tempo stimato: **mezza giornata** per un ambiente di test, se gruppi e licenze sono già pronti.
Ruoli necessari: amministratore Power Platform (ambiente), amministratore Entra ID (gruppi), referente HR (dati iniziali).

## 4.0 Prerequisiti

### Licenze (da verificare prima di partire)
Un'app Canvas che usa **Dataverse** è un'app *premium*: **ogni utente** che la apre deve essere coperto da una di queste opzioni:

| Opzione | Quando conviene |
|---|---|
| **Pagamento a consumo** (Pay-as-you-go, ambiente collegato a una sottoscrizione Azure) | Molti lavoratori che usano l'app poche volte al mese: si paga solo per gli **utenti attivi nel mese** |
| Power Apps **per app** | Numero stabile di utenti che usano solo questa app |
| Power Apps **Premium** (per utente) | Utenti che usano molte app premium (es. HR, coordinatori) |

Con migliaia di lavoratori la licenza pesa sul progetto: chiedete al vostro partner Microsoft i **prezzi correnti** e valutate il pagamento a consumo per i lavoratori, con licenze dedicate per HR e coordinatori. L'account di servizio dei flussi richiede una licenza premium (o Power Automate Process).

### Altro
- Tenant Microsoft 365 con gli utenti dei lavoratori. Chi non ha la casella di posta riceve le notifiche all'*e-mail di contatto* inserita al primo accesso.
- Un sito SharePoint HR con una cartella per i file paghe, es. `Documenti condivisi/Formazione/Payroll`.
- Per lo script: Python 3.10+ e Azure CLI (`az login`), oppure il pacchetto `msal`.

## 4.1 Creare l'ambiente

1. [Interfaccia di amministrazione di Power Platform](https://admin.powerplatform.microsoft.com) → **Ambienti → Nuovo**:
   - Tipo: *Sandbox* per collaudo, *Produzione* per l'esercizio
   - Area: **Europa**
   - Aggiungi Dataverse: **Sì**, lingua **Italiano**, valuta **EUR**
   - Gruppo di sicurezza: `GRP-Formazione-Lavoratori` (vedi 4.2)
2. Ambiente → **Impostazioni → Audit e log → Impostazioni di controllo**: attivare *Avvia controllo* e *Registra accesso*.
3. **Criteri dati (DLP)**: mettere Microsoft Dataverse, Office 365 Outlook, SharePoint e Office 365 Users nel gruppo *Business* per questo ambiente.

## 4.2 Gruppi Microsoft Entra ID e account di servizio

1. Creare i 4 gruppi di sicurezza descritti in [03-sicurezza.md §3.2](03-sicurezza.md#32-gruppi-team-e-ruoli) e annotare gli **Object ID**.
2. Creare l'account `svc-formazione@…` (vedi [§3.5](03-sicurezza.md#35-account-di-servizio-dei-flussi)), aggiungerlo all'ambiente con il ruolo *System Administrator* e dargli accesso in scrittura alla cartella SharePoint dei file paghe.

## 4.3 Creare tabelle, sicurezza e flussi con lo script

```bash
cd Formazione-Dolce
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r dataverse/requirements.txt
cp dataverse/config.example.json dataverse/config.json
```

Compilare `dataverse/config.json`:
- `environment_url`: *Interfaccia di amministrazione → Ambiente → URL ambiente* (es. `https://societadolce-formazione.crm4.dynamics.com`);
- `tenant_id` e gli Object ID dei 4 gruppi;
- `variabili_ambiente`: e-mail HR, destinatari del file paghe, sito e cartella SharePoint. `sdf_AppUrl` si compila dopo aver pubblicato l'app (4.5).

```bash
az login --tenant <ID-tenant>
python dataverse/provision.py --config dataverse/config.json --dry-run    # anteprima, non modifica nulla
python dataverse/provision.py --config dataverse/config.json              # esecuzione
```

Lo script esegue in ordine: `solution, choices, tables, columns, relationships, keys, publish, envvars, connrefs, roles, colsec, teams, flows`. Si può rilanciare senza rischi: i componenti già presenti vengono saltati. Per eseguire solo alcuni passi:

```bash
python dataverse/provision.py --steps roles,colsec,teams
```

Per caricare in un ambiente di **test** le strutture e i corsi d'esempio di `dataverse/seed/`:

```bash
python dataverse/provision.py --steps seed
```

> **Senza script.** Le tabelle si possono creare anche a mano da [make.powerapps.com](https://make.powerapps.com) → Soluzioni → *Gestione ore formazione* seguendo [02-modello-dati.md](02-modello-dati.md). Bisogna rispettare nomi logici e valori delle scelte, perché app e flussi li usano.

## 4.4 Collegare le connessioni e verificare le variabili

1. make.powerapps.com → **Soluzioni → Gestione ore formazione → Riferimenti di connessione**.
2. Per `SDF Dataverse`, `SDF Office 365 Outlook` e `SDF SharePoint` scegliere *Modifica → Nuova connessione*, collegandosi **con l'account di servizio**.
3. **Variabili d'ambiente**: controllare i valori (e-mail HR, destinatari paghe, sito, cartella, festività dell'anno con il **patrono locale**).

## 4.5 Creare l'app Canvas

Seguire [powerapps/README.md](../powerapps/README.md): creare l'app nella soluzione, aggiungere le origini dati, incollare formule e schermate, aggiungere il flusso F8, creare il modulo allegati, salvare e pubblicare.

Poi:
1. Aprire i **Dettagli** dell'app e copiare il **Collegamento web** (`https://apps.powerapps.com/play/e/<ambiente>/a/<app>?tenantId=<tenant>`).
2. Scriverlo nella variabile d'ambiente **`sdf_AppUrl`**: i flussi aggiungono `&richiesta=<ID>` per il collegamento diretto.
3. **Condividere** l'app con i 4 gruppi Entra (*Condividi → gruppo → Utente*), lasciando i ruoli Dataverse già assegnati ai team.

## 4.6 Attivare i flussi

make.powerapps.com → Soluzioni → *Gestione ore formazione* → **Flussi cloud**. Attivarli in quest'ordine:

1. F7 – Allinea lavoratore
2. F8 – Aggiorna dati personali
3. F1 – Invio al coordinatore
4. F2 – Esito coordinatore
5. F3 – Esito HR
6. F6 – Esportazione Payroll
7. F4 – Promemoria
8. F5 – Riepilogo mensile

Se un flusso non si attiva, aprirlo nella finestra di progettazione: i dettagli e le verifiche post-importazione sono in [powerautomate/README.md](../powerautomate/README.md).

## 4.7 Caricare i dati iniziali

| Ordine | Tabella | Come | Note |
|---|---|---|---|
| 1 | **Strutture organizzative** | Excel (make.powerapps.com → Tabelle → *Importa → Importa dati da Excel*) o schermata Amministrazione dell'app | Area, servizio, centro di costo, coordinatore servizio, date di validità |
| 2 | **Catalogo corsi** | Excel o schermata Amministrazione | Solo i corsi *Datore di lavoro*: codice, titolo, modalità, durata, gettone previsto, attivo |
| 3 | **Lavoratori** | Excel (modello `dataverse/seed/lavoratori_modello.csv`) o un **flusso di dati** (Dataflow) collegato all'anagrafica paghe/HR | `Login Microsoft 365` in minuscolo. Dopo l'importazione compilare *Utente Microsoft 365*, *Struttura* e *Coordinatore*: F7 completa gli altri campi e condivide i record |

> Per mantenere l'organigramma allineato nel tempo conviene un **Dataflow pianificato** (es. settimanale) dall'anagrafica del gestionale del personale verso *Lavoratori*, con chiave `Login Microsoft 365`.

## 4.8 Collaudo e passaggio in produzione

1. Eseguire i casi di test di [05-collaudo.md](05-collaudo.md) con almeno un utente per ruolo.
2. Esportare la soluzione come **gestita** (Soluzioni → Esporta → Gestita) e importarla nell'ambiente di produzione, oppure usare le **Pipeline** di Power Platform.
3. In produzione: ricollegare i riferimenti di connessione, impostare le variabili d'ambiente (in particolare `sdf_AppUrl` di produzione), attivare i flussi nell'ordine di 4.6, caricare i dati reali.
4. Comunicazione ai lavoratori: link all'app (anche da **Microsoft Teams**, *App → Power Apps → aggiungi come scheda/app*), breve guida, informativa privacy.

## 4.9 Manutenzione

| Attività | Chi | Dove |
|---|---|---|
| Nuovi coordinatori, cambi di servizio | Amministratore | App → Amministrazione → Lavoratori / Organigramma, oppure Dataflow |
| Nuovi ruoli HR / Admin | IT | Gruppi Entra ID |
| Nuovi corsi a catalogo; validazione dei corsi esterni inseriti dai lavoratori | Amministratore / HR | App → Amministrazione → Catalogo corsi |
| Festività dell'anno successivo | Amministratore | Variabile d'ambiente `sdf_Festivita` |
| Riapertura di un mese chiuso | Amministratore | App → Chiusura mensile → Riapri |
| Modifiche al modello dati | Sviluppatore | `dataverse/schema.yaml` → `provision.py` → `genera_documentazione.py` |
