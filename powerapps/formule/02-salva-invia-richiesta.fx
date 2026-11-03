// #############################################################################
//  GESTIONE ORE FORMAZIONE – Società Dolce
//  Nuova richiesta / modifica: controlli, salvataggio, invio con allegati, annullamento
//
//  Flusso: SDF_API03_SalvaRichiesta(dati JSON, azione, attestato, nomeAttestato, altraDoc, nomeAltraDoc)
//  azione = "bozza" | "invia" | "annulla". Gli allegati sono data URI «data:<tipo>;base64,...»
//  ottenuti dai controlli allegati ric_attAttestato e ric_attAltraDoc (vedi README).
//  Le regole sono verificate di nuovo dal flusso: quelle dell'app servono a guidare l'utente.
//
//  Le formule sono identiche a quelle dei file powerapps/src/*.pa.yaml (generati
//  dalla stessa fonte). Notazione inglese: in Studio con lingua italiana i separatori
//  diventano «;» (argomenti) e «;;» (concatenazione di azioni).
// #############################################################################

// =============================================================================
//  1. Inizializzazione del modulo (nuova richiesta o modifica)
//  Dove: scrRichiesta.OnVisible
//  varIdModifica = 0 → nuova richiesta; altrimenti l'ID della richiesta da modificare, presa da
//  colMieRichieste. Sola lettura se lo stato non è modificabile (§1.5) o se il mese è chiuso (R9).
// =============================================================================
Set(varMenuAperto, false);
UpdateContext({locDialogo: "", locAzione: "", locConfermaDup: false, locAllegatiInviati: false, locMsgDialogo: ""});
ClearCollect(
    colMesiChiusi,
    ShowColumns(Filter('Chiusure mensili', 'Stato del periodo'.Value = "Chiuso"), Periodo, Anno, Mese)
);
// in modifica: la richiesta deve essere tra quelle caricate con SDF_API02
If(
    varIdModifica > 0 && IsBlank(LookUp(colMieRichieste, id = varIdModifica)),
    Set(varCaricamento, true);
    Set(varMessaggioCaricamento, "Caricamento della richiesta…");
    With(
        {rm: IfError(SDF_API02_MieRichieste.Run(0), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
        If(
            rm.esito = "OK",
            Set(varJsonMieRichieste, rm.dati);
            Set(varMieCaricate, true),
            Notify("Non è stato possibile caricare le tue richieste. " & rm.messaggio, NotificationType.Error)
        )
    );
    Set(varCaricamento, false)
);
If(
    varIdModifica > 0 && IsBlank(LookUp(colMieRichieste, id = varIdModifica)),
    Notify("Richiesta non trovata: si apre un modulo vuoto.", NotificationType.Warning);
    Set(varIdModifica, 0)
);
Set(varRicEdit, LookUp(colMieRichieste, id = varIdModifica));
// sola lettura se lo stato non è modificabile (§1.5) o se il mese della richiesta è chiuso (R9)
UpdateContext({
    locSolaLettura: varIdModifica > 0 && (
        !varRicEdit.modificabile ||
        !IsBlank(LookUp(colMesiChiusi, Anno = varRicEdit.annoCompetenza && Mese = varRicEdit.meseCompetenza))
    )
});
Reset(ric_ddEnte);
Reset(ric_cmbCorsoCatalogo);
Reset(ric_tglStorico);
Reset(ric_cmbCorsoStorico);
Reset(ric_txtTitoloLibero);
Reset(ric_ddModalita);
Reset(ric_txtDurataCorso);
Reset(ric_tglPiuGiornate);
Reset(ric_txtNomeEnte);
Reset(ric_dtpData);
Reset(ric_ddIniH);
Reset(ric_ddIniM);
Reset(ric_ddFinH);
Reset(ric_ddFinM);
Reset(ric_ddIngH);
Reset(ric_ddIngM);
Reset(ric_ddUscH);
Reset(ric_ddUscM);
Reset(ric_txtOreRetribuite);
Reset(ric_txtOreGettone);
Reset(ric_txtNote);
Reset(ric_chkPartecipazione);
Reset(ric_chkCorrettezza);
Reset(ric_chkAutorizzazione);
Reset(ric_attAttestato);
Reset(ric_attAltraDoc)

// =============================================================================
//  2. Controlli bloccanti per bozza e invio: corso, data, R1, R2, R3, R9
//  Dove: scrRichiesta › ric_lblErrori.Text
//  Durate calcolate con Time(ora, minuti, 0) e DateDiff in minuti; ore = Round(minuti / 60, 2).
//  R9: LookUp su 'Chiusure mensili' (lista leggibile da tutti) con Anno/Mese e stato Chiuso.
//  Se il testo non è vuoto i pulsanti Salva bozza e Invia sono disabilitati.
// =============================================================================
With(
    {
        minSess: DateDiff(Time(Value(ric_ddIniH.Selected.Value), Value(ric_ddIniM.Selected.Value), 0), Time(Value(ric_ddFinH.Selected.Value), Value(ric_ddFinM.Selected.Value), 0), TimeUnit.Minutes),
        minFreq: DateDiff(Time(Value(ric_ddIngH.Selected.Value), Value(ric_ddIngM.Selected.Value), 0), Time(Value(ric_ddUscH.Selected.Value), Value(ric_ddUscM.Selected.Value), 0), TimeUnit.Minutes),
        oreRet: Coalesce(Value(ric_txtOreRetribuite.Text), 0),
        oreGet: If((ric_ddEnte.Selected.Value = "Datore di lavoro" && !IsBlank(ric_cmbCorsoCatalogo.Selected.ID) && !ric_cmbCorsoCatalogo.Selected.'Gettone previsto'), 0, Coalesce(Value(ric_txtOreGettone.Text), 0)),
        d: ric_dtpData.SelectedDate
    },
    Concat(
        Filter(
            Table(
                {Errore: If(
                    ric_ddEnte.Selected.Value = "Datore di lavoro", IsBlank(ric_cmbCorsoCatalogo.Selected.ID),
                    ric_tglStorico.Value, IsBlank(ric_cmbCorsoStorico.Selected.ID),
                    IsBlank(Trim(ric_txtTitoloLibero.Text)) || IsBlank(ric_ddModalita.Selected.Value) || Coalesce(Value(ric_txtDurataCorso.Text), 0) <= 0
                ), Testo: "Indica il corso: sceglilo dal catalogo o dallo storico, oppure inserisci titolo, modalità e durata del nuovo corso."},
                {Errore: IsBlank(d), Testo: "Indica la data della sessione formativa."},
                {Errore: minSess <= 0, Testo: "R1 · L’ora di fine sessione deve essere successiva all’ora di inizio."},
                {Errore: minFreq <= 0, Testo: "R1 · L’ora di uscita deve essere successiva all’ora di ingresso."},
                {Errore: minFreq > minSess, Testo: "R2 · Le ore frequentate non possono superare la durata della sessione."},
                {Errore: oreRet < 0 || oreGet < 0, Testo: "R3 · Le ore richieste non possono essere negative."},
                {Errore: oreRet + oreGet > Round(minFreq / 60, 2), Testo: "R3 · Ore retribuite + ore gettone richieste non possono superare le ore frequentate."},
                {Errore: !IsBlank(d) && !IsBlank(LookUp('Chiusure mensili', Anno = Year(d) && Mese = Month(d) && 'Stato del periodo'.Value = "Chiuso")), Testo: "R9 · Il mese della data indicata è chiuso: non si possono inserire o modificare richieste."}
            ),
            Errore
        ),
        "• " & Testo,
        Char(10)
    )
)

// =============================================================================
//  3. Controlli aggiuntivi per l'invio (R11)
//  Dove: scrRichiesta › ric_lblErroriInvio.Text
//  Ore richieste > 0, tre dichiarazioni, coordinatore e e-mail personale presenti.
// =============================================================================
Concat(
    Filter(
        Table(
            {Errore: Coalesce(Value(ric_txtOreRetribuite.Text), 0) + If((ric_ddEnte.Selected.Value = "Datore di lavoro" && !IsBlank(ric_cmbCorsoCatalogo.Selected.ID) && !ric_cmbCorsoCatalogo.Selected.'Gettone previsto'), 0, Coalesce(Value(ric_txtOreGettone.Text), 0)) <= 0, Testo: "R11 · Per inviare indica le ore retribuite e/o le ore gettone richieste (maggiori di zero)."},
            {Errore: !(ric_chkPartecipazione.Value && ric_chkCorrettezza.Value && ric_chkAutorizzazione.Value), Testo: "R11 · Per inviare spunta le tre dichiarazioni."},
            {Errore: IsBlank(recProfilo.coordinatoreLogin), Testo: "R11 · Non hai un coordinatore assegnato: segnala la variazione a HR dal tuo profilo."},
            {Errore: IsBlank(recProfilo.emailPersonale), Testo: "R11 · Manca l’e-mail personale nel profilo."}
        ),
        Errore
    ),
    "• " & Testo,
    Char(10)
)

// =============================================================================
//  4. Avvisi non bloccanti: R6 (somma delle sessioni) e R7 (possibile duplicato)
//  Dove: scrRichiesta › ric_lblAvvisi.Text
//  Calcolati sulle richieste del lavoratore già caricate (colMieRichieste), escluse annullate e respinte.
// =============================================================================
With(
    {cod: If(ric_ddEnte.Selected.Value = "Datore di lavoro", ric_cmbCorsoCatalogo.Selected.'Codice univoco corso', ric_tglStorico.Value, ric_cmbCorsoStorico.Selected.'Codice univoco corso', ""), dur: If(ric_ddEnte.Selected.Value = "Datore di lavoro", Coalesce(ric_cmbCorsoCatalogo.Selected.'Durata corso', 0), ric_tglStorico.Value, Coalesce(ric_cmbCorsoStorico.Selected.'Durata corso', 0), Coalesce(Value(ric_txtDurataCorso.Text), 0)), sess: Round(DateDiff(Time(Value(ric_ddIniH.Selected.Value), Value(ric_ddIniM.Selected.Value), 0), Time(Value(ric_ddFinH.Selected.Value), Value(ric_ddFinM.Selected.Value), 0), TimeUnit.Minutes) / 60, 2)},
    Concat(
        Filter(
            Table(
                {
                    Avviso: !IsBlank(cod) && dur > 0 && Sum(Filter(colMieRichieste, codiceCorso = cod && id <> varIdModifica && !(stato in ["Annullata", "Respinta dal coordinatore", "Respinta da HR"])), durataSessione) + sess > dur,
                    Testo: "R6 · Con questa sessione la somma delle tue sessioni per il corso supera la durata complessiva (" & Text(dur, "[$-en-US]0.##") & " h): l’invio verrà bloccato."
                },
                {
                    Avviso: IsBlank(cod) && dur > 0 && sess > dur,
                    Testo: "R6 · La durata della sessione supera la durata complessiva indicata per il corso."
                },
                {
                    Avviso: !IsBlank(cod) && !IsBlank(LookUp(colMieRichieste, codiceCorso = cod && dataSessione = ric_dtpData.SelectedDate && id <> varIdModifica && !(stato in ["Annullata", "Respinta dal coordinatore", "Respinta da HR"]))),
                    Testo: "R7 · Hai già una richiesta per questo corso nella stessa data: all’invio ti verrà chiesta conferma (possibile duplicato)."
                }
            ),
            Avviso
        ),
        "• " & Testo,
        Char(10)
    )
)

// =============================================================================
//  5. R5: ore gettone disabilitate se il corso a catalogo non prevede il gettone
//  Dove: scrRichiesta › ric_txtOreGettone.DisplayMode
//  Stessa condizione usata nel JSON inviato (ore gettone forzate a 0).
// =============================================================================
If(locSolaLettura, DisplayMode.View, (ric_ddEnte.Selected.Value = "Datore di lavoro" && !IsBlank(ric_cmbCorsoCatalogo.Selected.ID) && !ric_cmbCorsoCatalogo.Selected.'Gettone previsto'), DisplayMode.Disabled, DisplayMode.Edit)

// =============================================================================
//  6. Salvataggio / invio (pulsante nascosto richiamato da «Salva bozza» e «Invia al coordinatore»)
//  Dove: scrRichiesta › ric_btnEsegui.OnSelect
//  - I file diventano data URI: JSON(allegato, JSONFormat.IncludeBinaryData) restituisce il testo tra
//    virgolette, che vengono tolte con Mid(j, 2, Len(j) - 2). Limite 10 MB (circa 14 milioni di caratteri).
//  - Se il flusso risponde dati.richiestaConferma = "duplicato" si apre la finestra di conferma e,
//    confermando, si ripete l'invio con confermaDuplicato: true (gli allegati non vengono ricaricati).
//  - In caso di successo: messaggio, ricarica delle richieste (SDF_API02), ritorno all'elenco.
// =============================================================================
// Procedura di salvataggio (locAzione = "bozza" oppure "invia"), richiamata con Select(ric_btnEsegui).
// Gli allegati diventano data URI: JSON(..., IncludeBinaryData) restituisce "data:...;base64,..." tra virgolette.
With(
    {
        attUri: If(locAllegatiInviati || CountRows(ric_attAttestato.Attachments) = 0, "", With({j: JSON(First(ric_attAttestato.Attachments).Value, JSONFormat.IncludeBinaryData)}, Mid(j, 2, Len(j) - 2))),
        attNome: If(locAllegatiInviati || CountRows(ric_attAttestato.Attachments) = 0, "", First(ric_attAttestato.Attachments).Name),
        altraUri: If(locAllegatiInviati || CountRows(ric_attAltraDoc.Attachments) = 0, "", With({j: JSON(First(ric_attAltraDoc.Attachments).Value, JSONFormat.IncludeBinaryData)}, Mid(j, 2, Len(j) - 2))),
        altraNome: If(locAllegatiInviati || CountRows(ric_attAltraDoc.Attachments) = 0, "", First(ric_attAltraDoc.Attachments).Name)
    },
    If(
        Len(attUri) > 14000000 || Len(altraUri) > 14000000,
        Notify("Ogni allegato può pesare al massimo 10 MB: riduci il file (es. PDF compresso) e riprova.", NotificationType.Error),
        Set(varCaricamento, true);
        Set(varMessaggioCaricamento, If(locAzione = "invia", "Invio al coordinatore in corso…", "Salvataggio della bozza in corso…"));
        With(
            {r: IfError(
                SDF_API03_SalvaRichiesta.Run(
                    JSON(
                        {
                            id: varIdModifica,
                            enteErogatore: ric_ddEnte.Selected.Value,
                            corsoId: If(ric_ddEnte.Selected.Value = "Datore di lavoro", Coalesce(ric_cmbCorsoCatalogo.Selected.ID, 0), ric_tglStorico.Value, Coalesce(ric_cmbCorsoStorico.Selected.ID, 0), 0),
                            nuovoCorso: If(
                                !(ric_ddEnte.Selected.Value = "Datore di lavoro") && !ric_tglStorico.Value,
                                {
                                    titolo: Trim(ric_txtTitoloLibero.Text),
                                    modalita: ric_ddModalita.Selected.Value,
                                    durata: Coalesce(Value(ric_txtDurataCorso.Text), 0),
                                    piuGiornate: ric_tglPiuGiornate.Value,
                                    nomeEnte: Trim(ric_txtNomeEnte.Text)
                                },
                                Blank()
                            ),
                            dataSessione: Text(ric_dtpData.SelectedDate, "yyyy-mm-dd"),
                            oraInizioSessione: ric_ddIniH.Selected.Value & ":" & ric_ddIniM.Selected.Value,
                            oraFineSessione: ric_ddFinH.Selected.Value & ":" & ric_ddFinM.Selected.Value,
                            oraIngresso: ric_ddIngH.Selected.Value & ":" & ric_ddIngM.Selected.Value,
                            oraUscita: ric_ddUscH.Selected.Value & ":" & ric_ddUscM.Selected.Value,
                            oreRetribuiteRichieste: Coalesce(Value(ric_txtOreRetribuite.Text), 0),
                            oreGettoneRichieste: If((ric_ddEnte.Selected.Value = "Datore di lavoro" && !IsBlank(ric_cmbCorsoCatalogo.Selected.ID) && !ric_cmbCorsoCatalogo.Selected.'Gettone previsto'), 0, Coalesce(Value(ric_txtOreGettone.Text), 0)),
                            noteLavoratore: Trim(ric_txtNote.Text),
                            confermaPartecipazione: ric_chkPartecipazione.Value,
                            confermaCorrettezza: ric_chkCorrettezza.Value,
                            autorizzazioneInvio: ric_chkAutorizzazione.Value,
                            confermaDuplicato: locConfermaDup
                        },
                        JSONFormat.IgnoreBinaryData
                    ),
                    locAzione,
                    attUri,
                    attNome,
                    altraUri,
                    altraNome
                ),
                {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
            )},
            With(
                {d: IfError(ParseJSON(r.dati), ParseJSON("{}"))},
                If(
                    r.esito = "OK",
                    With(
                        {avvisi: IfError(Concat(Table(d.avvisi) As a, Text(a.Value), " · "), "")},
                        Notify(
                            If(locAzione = "invia", "Richiesta " & Text(d.idRichiesta) & " inviata al coordinatore.", "Bozza " & Text(d.idRichiesta) & " salvata.") &
                            If(IsBlank(avvisi), "", " Attenzione: " & avvisi),
                            If(IsBlank(avvisi), NotificationType.Success, NotificationType.Warning)
                        )
                    );
                    With(
                        {rm: IfError(SDF_API02_MieRichieste.Run(0), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
                        If(
                            rm.esito = "OK",
                            Set(varJsonMieRichieste, rm.dati);
                            Set(varMieCaricate, true),
                            Notify("Non è stato possibile caricare le tue richieste. " & rm.messaggio, NotificationType.Error)
                        )
                    );
                    Reset(ric_attAttestato);
                    Reset(ric_attAltraDoc);
                    Set(varIdModifica, 0);
                    Navigate(scrMieRichieste, ScreenTransition.None),
                    // R7: il flusso chiede conferma del possibile duplicato (la bozza è già salvata)
                    Text(d.richiestaConferma) = "duplicato",
                    If(Coalesce(Value(d.id), 0) > 0, Set(varIdModifica, Value(d.id)); UpdateContext({locAllegatiInviati: true}));
                    UpdateContext({locMsgDialogo: r.messaggio, locDialogo: "duplicato"}),
                    Notify(r.messaggio, NotificationType.Error)
                )
            )
        );
        Set(varCaricamento, false)
    )
)

// =============================================================================
//  7. Finestra di conferma: possibile duplicato oppure annullamento
//  Dove: scrRichiesta › ric_btnDialogoConferma.OnSelect
//  Annullamento: SDF_API03 con azione "annulla" e JSON {id}.
// =============================================================================
If(
    locDialogo = "duplicato",
    // conferma del possibile duplicato: si ripete l'invio con confermaDuplicato = true
    UpdateContext({locConfermaDup: true, locAzione: "invia", locDialogo: ""});
    Select(ric_btnEsegui),
    Set(varCaricamento, true);
    Set(varMessaggioCaricamento, "Annullamento in corso…");
    With(
        {r: IfError(
            SDF_API03_SalvaRichiesta.Run(JSON({id: varIdModifica}, JSONFormat.IgnoreBinaryData), "annulla", "", "", "", ""),
            {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"}
        )},
        If(
            r.esito = "OK",
            Notify("Richiesta annullata.", NotificationType.Success);
            With(
                {rm: IfError(SDF_API02_MieRichieste.Run(0), {esito: "ERRORE", messaggio: testoErroreRete, dati: "{}"})},
                If(
                    rm.esito = "OK",
                    Set(varJsonMieRichieste, rm.dati);
                    Set(varMieCaricate, true),
                    Notify("Non è stato possibile caricare le tue richieste. " & rm.messaggio, NotificationType.Error)
                )
            );
            UpdateContext({locDialogo: ""});
            Set(varIdModifica, 0);
            Navigate(scrMieRichieste, ScreenTransition.None),
            Notify(r.messaggio, NotificationType.Error)
        )
    );
    Set(varCaricamento, false)
)

// =============================================================================
//  8. Le mie richieste: elenco filtrato per anno, mese e stato
//  Dove: scrMieRichieste › mie_galRichieste.Items
// =============================================================================
Sort(
    Filter(
        colMieRichieste,
        mie_ddAnno.Selected.Num = 0 || annoCompetenza = mie_ddAnno.Selected.Num,
        mie_ddMese.Selected.Num = 0 || meseCompetenza = mie_ddMese.Selected.Num,
        Switch(
            mie_ddStato.Selected.Gruppo,
            "tutti", true,
            "attesa_integr", gruppo = "attesa" || gruppo = "integrazione",
            gruppo = mie_ddStato.Selected.Gruppo
        )
    ),
    modificato,
    SortOrder.Descending
)
