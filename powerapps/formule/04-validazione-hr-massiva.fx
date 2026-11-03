// #############################################################################
//  GESTIONE ORE FORMAZIONE – Società Dolce
//  Ufficio HR: validazione singola, per selezione e per perimetro
//
//  Lettura diretta di 'Richieste formazione' con filtri delegabili (= su colonne indicizzate,
//  StartsWith sui testi). Scritture solo con SDF_API07_EsitoHR(dati JSON):
//    {azione, nota, richieste: [{id, oreRetribuite, oreGettone}]}
//  oreRetribuite / oreGettone = -1 → il flusso usa le ore riconosciute dal coordinatore.
//
//  Le formule sono identiche a quelle dei file powerapps/src/*.pa.yaml (generati
//  dalla stessa fonte). Notazione inglese: in Studio con lingua italiana i separatori
//  diventano «;» (argomenti) e «;;» (concatenazione di azioni).
// #############################################################################

// =============================================================================
//  1. Elenco delle richieste in attesa di validazione (filtri delegabili)
//  Dove: scrValidazioneHR › val_galRichieste.Items
// =============================================================================
Sort(Filter(
    'Richieste formazione',
    'Stato richiesta'.Value = "In attesa di validazione HR",
    val_ddAnno.Selected.Num = 0 || 'Anno di competenza' = val_ddAnno.Selected.Num,
    val_ddMese.Selected.Num = 0 || 'Mese di competenza' = val_ddMese.Selected.Num,
    IsBlank(val_ddArea.Selected.Value) || Area.Value = val_ddArea.Selected.Value,
    IsBlank(val_txtServizio.Text) || StartsWith(Servizio, val_txtServizio.Text),
    IsBlank(val_txtCdc.Text) || StartsWith('Centro di costo', val_txtCdc.Text),
    IsBlank(val_txtCoord.Text) || StartsWith('Login coordinatore', Lower(Trim(val_txtCoord.Text))) || StartsWith(Coordinatore, val_txtCoord.Text),
    IsBlank(val_txtLavoratore.Text) || StartsWith(Cognome, val_txtLavoratore.Text) || StartsWith('Login lavoratore', Lower(Trim(val_txtLavoratore.Text))),
    IsBlank(val_txtCodice.Text) || StartsWith('Codice univoco corso', val_txtCodice.Text)
), 'Data sessione formativa', SortOrder.Descending)

// =============================================================================
//  2. Selezione di una riga (con eventuali ore HR modificate nella riga)
//  Dove: scrValidazioneHR › val_chkSel.OnCheck
// =============================================================================
// selezione della riga con eventuali ore HR modificate (-1 = usa le ore del coordinatore)
RemoveIf(colSelezioneHR, id = ThisItem.ID);
Collect(
    colSelezioneHR,
    {
        id: ThisItem.ID,
        idRichiesta: ThisItem.'ID richiesta',
        oreRetribuite: If(Coalesce(Value(val_txtRigaOreRet.Text), 0) = Coalesce(ThisItem.'Ore retribuite riconosciute coordinatore', 0), -1, Coalesce(Value(val_txtRigaOreRet.Text), 0)),
        oreGettone: If(Coalesce(Value(val_txtRigaOreGet.Text), 0) = Coalesce(ThisItem.'Ore gettone riconosciute coordinatore', 0), -1, Coalesce(Value(val_txtRigaOreGet.Text), 0))
    }
)

// =============================================================================
//  3. Preparazione: righe selezionate oppure intero perimetro (coordinatore, centro di costo, servizio, area)
//  Dove: scrValidazioneHR › val_btnPrepara.OnSelect
//  Il perimetro = tutte le richieste che rispettano i filtri correnti + il valore di perimetro scelto
//  (massimo 2000 per volta, limite delle righe di Power Apps).
// =============================================================================
If(
    locAzione <> "valida" && IsBlank(Trim(val_txtNota.Text)),
    Notify("Per respingere o chiedere un’integrazione la motivazione è obbligatoria.", NotificationType.Error),
    val_ddAmbito.Selected.Value = "Intero perimetro" && val_ddTipoPerimetro.Selected.Value <> "Tutte le richieste filtrate" && IsBlank(val_ddValorePerimetro.Selected.Value),
    Notify("Scegli il valore del perimetro (es. il centro di costo).", NotificationType.Error),
    If(
        val_ddAmbito.Selected.Value = "Righe selezionate",
        ClearCollect(colDaElaborareHR, colSelezioneHR),
        // intero perimetro: tutte le richieste che rispettano i filtri e il perimetro scelto (massimo 2000)
        ClearCollect(
            colDaElaborareHR,
            ForAll(
                Filter(
                    'Richieste formazione',
                    'Stato richiesta'.Value = "In attesa di validazione HR",
                    val_ddAnno.Selected.Num = 0 || 'Anno di competenza' = val_ddAnno.Selected.Num,
                    val_ddMese.Selected.Num = 0 || 'Mese di competenza' = val_ddMese.Selected.Num,
                    IsBlank(val_ddArea.Selected.Value) || Area.Value = val_ddArea.Selected.Value,
                    IsBlank(val_txtServizio.Text) || StartsWith(Servizio, val_txtServizio.Text),
                    IsBlank(val_txtCdc.Text) || StartsWith('Centro di costo', val_txtCdc.Text),
                    IsBlank(val_txtCoord.Text) || StartsWith('Login coordinatore', Lower(Trim(val_txtCoord.Text))) || StartsWith(Coordinatore, val_txtCoord.Text),
                    IsBlank(val_txtLavoratore.Text) || StartsWith(Cognome, val_txtLavoratore.Text) || StartsWith('Login lavoratore', Lower(Trim(val_txtLavoratore.Text))),
                    IsBlank(val_txtCodice.Text) || StartsWith('Codice univoco corso', val_txtCodice.Text),
                    val_ddTipoPerimetro.Selected.Value <> "Coordinatore" || 'Login coordinatore' = val_ddValorePerimetro.Selected.Value,
                    val_ddTipoPerimetro.Selected.Value <> "Centro di costo" || 'Centro di costo' = val_ddValorePerimetro.Selected.Value,
                    val_ddTipoPerimetro.Selected.Value <> "Servizio" || Servizio = val_ddValorePerimetro.Selected.Value,
                    val_ddTipoPerimetro.Selected.Value <> "Area" || Area.Value = val_ddValorePerimetro.Selected.Value
                ) As x,
                {
                    id: x.ID,
                    idRichiesta: x.'ID richiesta',
                    oreRetribuite: Coalesce(LookUp(colSelezioneHR, id = x.ID, oreRetribuite), -1),
                    oreGettone: Coalesce(LookUp(colSelezioneHR, id = x.ID, oreGettone), -1)
                }
            )
        )
    );
    If(
        CountRows(colDaElaborareHR) = 0,
        Notify("Nessuna richiesta da elaborare: spunta almeno una riga oppure controlla filtri e perimetro.", NotificationType.Warning),
        UpdateContext({locDialogo: "conferma"})
    )
)

// =============================================================================
//  4. Testo della finestra di conferma con il conteggio
//  Dove: scrValidazioneHR › val_lblDialogoTesto.Text
// =============================================================================
"Stai per " & Switch(locAzione, "valida", "VALIDARE", "respingi", "RESPINGERE", "chiedere un’INTEGRAZIONE per") & " " &
CountRows(colDaElaborareHR) & " richieste" &
If(
    val_ddAmbito.Selected.Value = "Intero perimetro",
    " (perimetro: " & val_ddTipoPerimetro.Selected.Value & If(val_ddTipoPerimetro.Selected.Value = "Tutte le richieste filtrate", "", " " & val_ddValorePerimetro.Selected.Value) & ")",
    " selezionate"
) & ". " &
If(locAzione = "valida", "Dove non hai modificato le ore verranno usate quelle riconosciute dal coordinatore. ", "Motivazione: " & Trim(val_txtNota.Text) & ". ") &
If(CountRows(colDaElaborareHR) >= 2000, "Attenzione: si elaborano al massimo 2000 richieste per volta, restringi i filtri. ", "") &
If(CountRows(colDaElaborareHR) > 25, "Oltre 25 richieste l’elaborazione prosegue in background e riceverai un’e-mail con l’esito. ", "") &
"Confermi?"

// =============================================================================
//  5. Invio a SDF_API07 e visualizzazione di messaggio e richieste scartate
//  Dove: scrValidazioneHR › val_btnDialogoConferma.OnSelect
// =============================================================================
Set(varCaricamento, true);
Set(varMessaggioCaricamento, "Elaborazione di " & CountRows(colDaElaborareHR) & " richieste…");
With(
    {r: IfError(
        SDF_API07_EsitoHR.Run(
            JSON(
                {
                    azione: locAzione,
                    nota: Trim(val_txtNota.Text),
                    richieste: ForAll(colDaElaborareHR, {id: id, oreRetribuite: oreRetribuite, oreGettone: oreGettone})
                },
                JSONFormat.IgnoreBinaryData
            )
        ),
        {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
    )},
    If(
        r.esito = "OK",
        With(
            {
                scartate: IfError(
                    Concat(
                        Table(ParseJSON(r.dati).scartate) As s,
                        "• " & Coalesce(LookUp(colDaElaborareHR, id = Value(s.Value.id), idRichiesta), Text(s.Value.id)) & ": " & Text(s.Value.motivo),
                        Char(10)
                    ),
                    ""
                )
            },
            UpdateContext({locEsito: Coalesce(r.messaggio, "Operazione completata.") & If(IsBlank(scartate), "", Char(10) & "Richieste scartate:" & Char(10) & scartate)});
            Notify(Coalesce(r.messaggio, "Operazione completata.") & If(IsBlank(scartate), "", " Alcune richieste sono state scartate: vedi il dettaglio sopra l’elenco."), If(IsBlank(scartate), NotificationType.Success, NotificationType.Warning))
        );
        Clear(colSelezioneHR);
        Clear(colDaElaborareHR);
        Reset(val_txtNota);
        Refresh('Richieste formazione'),
        Notify(r.messaggio, NotificationType.Error)
    )
);
UpdateContext({locDialogo: ""});
Set(varCaricamento, false)
