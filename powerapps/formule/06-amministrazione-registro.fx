// #############################################################################
//  GESTIONE ORE FORMAZIONE – Società Dolce
//  Amministrazione: salvataggi diretti con riga nel Registro modifiche
//
//  Ogni creazione o modifica fatta dall'Amministratore scrive in 'Registro modifiche' una riga
//  per ogni campo cambiato (Azione, Lista, ID elemento, Campo, Valore precedente/nuovo,
//  Ruolo = Amministratore, Login autore). Il codice fiscale non viene mai registrato in chiaro.
//
//  Le formule sono identiche a quelle dei file powerapps/src/*.pa.yaml (generati
//  dalla stessa fonte). Notazione inglese: in Studio con lingua italiana i separatori
//  diventano «;» (argomenti) e «;;» (concatenazione di azioni).
// #############################################################################

// =============================================================================
//  1. Salvataggio di un lavoratore (persona Microsoft 365, struttura, coordinatore)
//  Dove: scrAdmin › adm_btnSalvaLav.OnSelect
//  Le colonne Persona si scrivono con il record {Claims: "i:0#.f|membership|" & Lower(email), ...}.
//  Area, servizio, centro di costo e ID struttura sono copiati dalla struttura scelta.
// =============================================================================
With(
    {
        prima: locLav,
        utente: adm_cmbLavUtente.Selected,
        str: adm_cmbLavStruttura.Selected,
        coord: adm_cmbLavCoord.Selected,
        cf: Upper(Trim(adm_txtLavCF.Text))
    },
    If(
        IsBlank(Trim(adm_txtLavLogin.Text)) || IsBlank(Trim(adm_txtLavCognome.Text)) || IsBlank(Trim(adm_txtLavNome.Text)),
        Notify("Login, cognome e nome sono obbligatori.", NotificationType.Error),
        IsBlank(str.ID),
        Notify("Scegli la struttura organizzativa: area, servizio e centro di costo vengono copiati da lì.", NotificationType.Error),
        !IsBlank(cf) && !IsMatch(cf, "^[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$"),
        Notify("Il codice fiscale non è valido.", NotificationType.Error),
        With(
            {salvato: IfError(
                Patch(
                    Lavoratori,
                    If(locNuovoLav, Defaults(Lavoratori), LookUp(Lavoratori, ID = prima.ID)),
                    {
                        Nominativo: Trim(adm_txtLavCognome.Text) & " " & Trim(adm_txtLavNome.Text),
                        'Utente Microsoft 365': If(IsBlank(utente.Email), Blank(), {Claims: "i:0#.f|membership|" & Lower(utente.Email), DisplayName: utente.DisplayName, Email: utente.Email, Department: "", JobTitle: "", Picture: ""}),
                        'Login Microsoft 365': Lower(Trim(adm_txtLavLogin.Text)),
                        Cognome: Trim(adm_txtLavCognome.Text),
                        Nome: Trim(adm_txtLavNome.Text),
                        'E-mail aziendale': Trim(adm_txtLavEmail.Text),
                        'ID struttura': str.ID,
                        Area: {Value: str.Area.Value},
                        Servizio: str.Servizio,
                        'Centro di costo': str.'Centro di costo',
                        'Coordinatore assegnato': If(IsBlank(coord.Email), Blank(), {Claims: "i:0#.f|membership|" & Lower(coord.Email), DisplayName: coord.DisplayName, Email: coord.Email, Department: "", JobTitle: "", Picture: ""}),
                        'Login coordinatore': Lower(coord.Email),
                        'Nome coordinatore': coord.DisplayName,
                        'E-mail coordinatore': coord.Email,
                        'Stato lavoratore': {Value: adm_ddLavStato.Selected.Value},
                        'Data inizio validità assegnazione': adm_dtpLavInizio.SelectedDate,
                        'Data fine validità assegnazione': adm_dtpLavFine.SelectedDate,
                        'Codice fiscale': If(IsBlank(cf), prima.'Codice fiscale', cf),
                        'Codice fiscale (mascherato)': If(IsBlank(cf), prima.'Codice fiscale (mascherato)', Left(cf, 3) & "**********" & Right(cf, 3)),
                        'Codice fiscale registrato': If(IsBlank(cf), Coalesce(prima.'Codice fiscale registrato', false), true)
                    }
                ),
                Notify("Salvataggio non riuscito: " & FirstError.Message, NotificationType.Error);
                Blank()
            )},
            If(
                !IsBlank(salvato),
                IfError(
                    // Registro modifiche: una riga per ogni campo cambiato (il codice fiscale non viene mai scritto)
                    ForAll(
                        Filter(
                            Table(
                                {Campo: "Nominativo", Prima: prima.Nominativo, Dopo: salvato.Nominativo},
                                {Campo: "Login Microsoft 365", Prima: prima.'Login Microsoft 365', Dopo: salvato.'Login Microsoft 365'},
                                {Campo: "E-mail aziendale", Prima: prima.'E-mail aziendale', Dopo: salvato.'E-mail aziendale'},
                                {Campo: "ID struttura", Prima: Text(prima.'ID struttura'), Dopo: Text(salvato.'ID struttura')},
                                {Campo: "Area", Prima: prima.Area.Value, Dopo: salvato.Area.Value},
                                {Campo: "Servizio", Prima: prima.Servizio, Dopo: salvato.Servizio},
                                {Campo: "Centro di costo", Prima: prima.'Centro di costo', Dopo: salvato.'Centro di costo'},
                                {Campo: "Login coordinatore", Prima: prima.'Login coordinatore', Dopo: salvato.'Login coordinatore'},
                                {Campo: "Stato lavoratore", Prima: prima.'Stato lavoratore'.Value, Dopo: salvato.'Stato lavoratore'.Value},
                                {Campo: "Data inizio validità assegnazione", Prima: Text(prima.'Data inizio validità assegnazione', "dd/mm/yyyy"), Dopo: Text(salvato.'Data inizio validità assegnazione', "dd/mm/yyyy")},
                                {Campo: "Data fine validità assegnazione", Prima: Text(prima.'Data fine validità assegnazione', "dd/mm/yyyy"), Dopo: Text(salvato.'Data fine validità assegnazione', "dd/mm/yyyy")},
                                {Campo: "Codice fiscale", Prima: If(Coalesce(prima.'Codice fiscale', "") <> Coalesce(salvato.'Codice fiscale', ""), "(riservato)", ""), Dopo: If(Coalesce(prima.'Codice fiscale', "") <> Coalesce(salvato.'Codice fiscale', ""), "Codice fiscale aggiornato", "")}
                            ),
                            Coalesce(Prima, "") <> Coalesce(Dopo, "")
                        ) As m,
                        Patch(
                            'Registro modifiche',
                            Defaults('Registro modifiche'),
                            {
                                Azione: If(IsBlank(prima.ID), "Creazione lavoratore", "Modifica lavoratore"),
                                Lista: "Lavoratori",
                                'ID elemento': Text(salvato.ID),
                                Campo: m.Campo,
                                'Valore precedente': m.Prima,
                                'Valore nuovo': m.Dopo,
                                Ruolo: {Value: "Amministratore"},
                                'Login autore': recProfilo.login,
                                Nota: ""
                            }
                        )
                    ),
                    Notify("Dati salvati, ma il Registro modifiche non è stato aggiornato: " & FirstError.Message, NotificationType.Warning),
                    Notify("Lavoratore salvato. Se è cambiato il coordinatore, il flusso F7 sposta richieste aperte e allegati.", NotificationType.Success)
                );
                UpdateContext({locLav: salvato, locNuovoLav: false})
            )
        )
    )
)

// =============================================================================
//  2. Coordinatore proposto = coordinatore del servizio della struttura scelta
//  Dove: scrAdmin › adm_cmbLavCoord.DefaultSelectedItems
// =============================================================================
If(
    !IsBlank(adm_cmbLavStruttura.Selected.ID) && adm_cmbLavStruttura.Selected.ID <> Coalesce(locLav.'ID struttura', -1) && !IsBlank(adm_cmbLavStruttura.Selected.'Coordinatore servizio'.Email),
    Table(adm_cmbLavStruttura.Selected.'Coordinatore servizio'),
    !IsBlank(locLav.'Coordinatore assegnato'.Email),
    Table(locLav.'Coordinatore assegnato'),
    Blank()
)

// =============================================================================
//  3. Validazione di un corso esterno inserito da un lavoratore
//  Dove: scrAdmin › adm_icoCorValida.OnSelect
// =============================================================================
With(
    {c: ThisItem},
    IfError(
        Patch('Catalogo corsi', LookUp('Catalogo corsi', ID = c.ID), {'Stato validazione': {Value: "Validato"}, 'Corso attivo': true}),
        Notify("Aggiornamento non riuscito: " & FirstError.Message, NotificationType.Error),
        Patch(
            'Registro modifiche',
            Defaults('Registro modifiche'),
            {
                Azione: "Validazione corso",
                Lista: "Catalogo corsi",
                'ID elemento': Text(c.ID),
                Campo: "Stato validazione",
                'Valore precedente': c.'Stato validazione'.Value,
                'Valore nuovo': "Validato",
                Ruolo: {Value: "Amministratore"},
                'Login autore': recProfilo.login,
                Nota: c.'Codice univoco corso'
            }
        ),
        Notify("Corso aggiornato, ma il Registro modifiche non è stato scritto: " & FirstError.Message, NotificationType.Warning),
        Notify("Corso «" & c.'Titolo corso' & "»: validato.", NotificationType.Success)
    )
)

// =============================================================================
//  4. Ruoli applicativi (il flusso F9 aggiorna i gruppi SharePoint)
//  Dove: scrAdmin › adm_btnSalvaRuo.OnSelect
// =============================================================================
With(
    {prima: locRuolo, ut: adm_cmbRuoUtente.Selected},
    If(
        IsBlank(Trim(adm_txtRuoLogin.Text)) || IsBlank(adm_ddRuoRuolo.Selected.Value),
        Notify("Login e ruolo sono obbligatori.", NotificationType.Error),
        With(
            {salvato: IfError(
                Patch(
                    'Ruoli applicativi',
                    If(locNuovoRuolo, Defaults('Ruoli applicativi'), LookUp('Ruoli applicativi', ID = prima.ID)),
                    {
                        Login: Lower(Trim(adm_txtRuoLogin.Text)),
                        Utente: If(IsBlank(ut.Email), Blank(), {Claims: "i:0#.f|membership|" & Lower(ut.Email), DisplayName: ut.DisplayName, Email: ut.Email, Department: "", JobTitle: "", Picture: ""}),
                        Ruolo: {Value: adm_ddRuoRuolo.Selected.Value},
                        Attivo: adm_tglRuoAttivo.Value,
                        Note: adm_txtRuoNote.Text
                    }
                ),
                Notify("Salvataggio non riuscito: " & FirstError.Message, NotificationType.Error);
                Blank()
            )},
            If(
                !IsBlank(salvato),
                IfError(
                    ForAll(
                        Filter(
                            Table(
                                {Campo: "Login", Prima: prima.Login, Dopo: salvato.Login},
                                {Campo: "Ruolo", Prima: prima.Ruolo.Value, Dopo: salvato.Ruolo.Value},
                                {Campo: "Attivo", Prima: If(IsBlank(prima.ID), "", If(prima.Attivo, "Sì", "No")), Dopo: If(salvato.Attivo, "Sì", "No")},
                                {Campo: "Note", Prima: prima.Note, Dopo: salvato.Note}
                            ),
                            Coalesce(Prima, "") <> Coalesce(Dopo, "")
                        ) As m,
                        Patch(
                            'Registro modifiche',
                            Defaults('Registro modifiche'),
                            {
                                Azione: If(IsBlank(prima.ID), "Assegnazione ruolo", "Modifica ruolo"),
                                Lista: "Ruoli applicativi",
                                'ID elemento': Text(salvato.ID),
                                Campo: m.Campo,
                                'Valore precedente': m.Prima,
                                'Valore nuovo': m.Dopo,
                                Ruolo: {Value: "Amministratore"},
                                'Login autore': recProfilo.login,
                                Nota: ""
                            }
                        )
                    ),
                    Notify("Dati salvati, ma il Registro modifiche non è stato aggiornato: " & FirstError.Message, NotificationType.Warning),
                    Notify("Ruolo salvato: i gruppi SharePoint vengono aggiornati dal flusso entro qualche minuto.", NotificationType.Success)
                );
                UpdateContext({locRuolo: salvato, locNuovoRuolo: false})
            )
        )
    )
)
