<#
.SYNOPSIS
    Installa il sito SharePoint dell'app "Gestione ore formazione" (Società Dolce).

.DESCRIPTION
    - crea (facoltativo) il sito del team senza gruppo Microsoft 365, in italiano, fuso di Roma;
    - applica il modello PnP template/GestioneFormazione.xml: liste, raccolte, colonne,
      viste, gruppi "Formazione - HR" e "Formazione - Paghe", permessi, parametri di configurazione;
    - aggiunge l'account di servizio e gli amministratori ai Proprietari del sito;
    - registra amministratori e utenti HR nella lista "Ruoli applicativi" e nei gruppi;
    - aggiorna la lista "Configurazione";
    - importa (facoltativo) strutture, corsi e lavoratori da file CSV (separatore ;).

    Lo script si può rilanciare: gli elementi già presenti vengono saltati.

    Prerequisiti:
      - PowerShell 7.4 o successivo (pwsh)
      - modulo PnP.PowerShell:      Install-Module PnP.PowerShell -Scope CurrentUser
      - una registrazione app Entra ID per PnP (una sola volta, da un amministratore):
            Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP Societa Dolce" -Tenant societadolce.onmicrosoft.com -Interactive
        e il relativo ClientId.
      - per -CreaSito: ruolo di amministratore SharePoint.

.EXAMPLE
    ./Installa-GestioneFormazione.ps1 `
        -SitoUrl https://societadolce.sharepoint.com/sites/GestioneFormazione `
        -ClientId 00000000-0000-0000-0000-000000000000 `
        -CreaSito -Proprietario admin@societadolce.it `
        -AccountServizio svc-formazione@societadolce.it `
        -Amministratori mario.rossi@societadolce.it `
        -UtentiHR anna.verdi@societadolce.it,luca.neri@societadolce.it `
        -UtentiPaghe paghe@societadolce.it `
        -EmailHR formazione@societadolce.it `
        -DestinatariPayroll "paghe@societadolce.it;formazione@societadolce.it" `
        -ImportaStrutture ./strutture.csv -ImportaCorsi ./corsi.csv -ImportaLavoratori ./lavoratori.csv
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SitoUrl,
    [Parameter(Mandatory = $true)] [string] $ClientId,
    [Parameter(Mandatory = $true)] [string] $AccountServizio,
    [switch] $CreaSito,
    [string] $Proprietario,
    [string[]] $Amministratori = @(),
    [string[]] $UtentiHR = @(),
    [string[]] $UtentiPaghe = @(),
    [string] $EmailHR,
    [string] $DestinatariPayroll,
    [string] $MittenteEmail,
    [string] $AppUrl,
    [string] $ImportaStrutture,
    [string] $ImportaCorsi,
    [string] $ImportaLavoratori,
    [switch] $DatiEsempio
)

$ErrorActionPreference = 'Stop'
$cartella = $PSScriptRoot
$template = Join-Path $cartella 'template/GestioneFormazione.xml'
$SitoUrl = $SitoUrl.TrimEnd('/')
$AccountServizio = $AccountServizio.Trim().ToLower()

# -----------------------------------------------------------------------------
#  Funzioni di supporto
# -----------------------------------------------------------------------------
function Write-Passo([string] $testo) { Write-Host "`n== $testo ==" -ForegroundColor Cyan }
function Write-Ok([string] $testo) { Write-Host "  [OK] $testo" -ForegroundColor Green }
function Write-Avviso([string] $testo) { Write-Host "  [!]  $testo" -ForegroundColor Yellow }

function ConvertTo-CamlValue([string] $valore) {
    return [System.Security.SecurityElement]::Escape($valore)
}

function Get-ElementoPerCampo([string] $lista, [string] $campo, [string] $valore) {
    $v = ConvertTo-CamlValue $valore
    $query = "<View><Query><Where><Eq><FieldRef Name='$campo'/><Value Type='Text'>$v</Value></Eq></Where></Query><RowLimit>1</RowLimit></View>"
    return @(Get-PnPListItem -List $lista -Query $query) | Select-Object -First 1
}

function ConvertTo-Booleano([string] $valore) {
    if ([string]::IsNullOrWhiteSpace($valore)) { return $false }
    return @('si', 'sì', 'true', '1', 'yes', 'x') -contains $valore.Trim().ToLower()
}

function ConvertTo-Numero([string] $valore) {
    if ([string]::IsNullOrWhiteSpace($valore)) { return $null }
    return [double]::Parse($valore.Trim().Replace(',', '.'), [Globalization.CultureInfo]::InvariantCulture)
}

function ConvertTo-Data([string] $valore) {
    if ([string]::IsNullOrWhiteSpace($valore)) { return $null }
    return [datetime]::ParseExact($valore.Trim(), 'dd/MM/yyyy', [Globalization.CultureInfo]::InvariantCulture)
}

$script:cacheUtenti = @{}
function Get-NomeUtente([string] $login) {
    # Restituisce il nome visualizzato di un utente del tenant (lo registra nel sito se serve)
    if ($script:cacheUtenti.ContainsKey($login)) { return $script:cacheUtenti[$login] }
    try {
        $u = New-PnPUser -LoginName "i:0#.f|membership|$login"
        $nome = $u.Title
    }
    catch {
        Write-Avviso "Utente non trovato nel tenant: $login"
        $nome = ''
    }
    $script:cacheUtenti[$login] = $nome
    return $nome
}

function Set-Configurazione([string] $chiave, [string] $valore) {
    if ([string]::IsNullOrWhiteSpace($valore)) { return }
    $elemento = Get-ElementoPerCampo 'Configurazione' 'Title' $chiave
    if ($elemento) {
        Set-PnPListItem -List 'Configurazione' -Identity $elemento.Id -Values @{ Valore = $valore } | Out-Null
    }
    else {
        Add-PnPListItem -List 'Configurazione' -Values @{ Title = $chiave; Valore = $valore } | Out-Null
    }
    Write-Ok "Configurazione: $chiave = $valore"
}

function Add-Ruolo([string] $login, [string] $ruolo) {
    $login = $login.Trim().ToLower()
    $v = ConvertTo-CamlValue $login
    $query = "<View><Query><Where><And><Eq><FieldRef Name='Title'/><Value Type='Text'>$v</Value></Eq>" +
             "<Eq><FieldRef Name='Ruolo'/><Value Type='Choice'>$ruolo</Value></Eq></And></Where></Query></View>"
    if (@(Get-PnPListItem -List 'Ruoli applicativi' -Query $query).Count -gt 0) {
        Write-Avviso "Ruolo $ruolo già presente per $login"
        return
    }
    Add-PnPListItem -List 'Ruoli applicativi' -Values @{ Title = $login; Utente = $login; Ruolo = $ruolo; Attivo = $true } | Out-Null
    Write-Ok "Ruolo $ruolo assegnato a $login"
}

function Add-MembroGruppo($gruppo, [string] $login) {
    $login = $login.Trim().ToLower()
    try {
        Add-PnPGroupMember -Group $gruppo -LoginName $login
        Write-Ok "$login aggiunto al gruppo $($gruppo.Title)"
    }
    catch {
        Write-Avviso "Impossibile aggiungere $login al gruppo $($gruppo.Title): $($_.Exception.Message)"
    }
}

# -----------------------------------------------------------------------------
#  Importazioni da CSV
# -----------------------------------------------------------------------------
function Import-Strutture([string] $percorso) {
    Write-Passo "Importazione strutture da $percorso"
    foreach ($r in (Import-Csv -Path $percorso -Delimiter ';' -Encoding UTF8)) {
        $cdc = $r.'Centro di costo'.Trim()
        if (Get-ElementoPerCampo 'Strutture organizzative' 'CentroDiCosto' $cdc) {
            Write-Avviso "Struttura $cdc già presente"
            continue
        }
        $valori = @{ Title = $r.Servizio.Trim(); Area = $r.Area.Trim(); CentroDiCosto = $cdc; Attiva = $true }
        $login = "$($r.'Login coordinatore servizio')".Trim().ToLower()
        if ($login) {
            $valori.CoordinatoreServizio = $login
            $valori.CoordinatoreServizioLogin = $login
            $valori.EmailCoordinatoreServizio = $login
        }
        try {
            Add-PnPListItem -List 'Strutture organizzative' -Values $valori | Out-Null
            Write-Ok "Struttura $($valori.Title) ($cdc)"
        }
        catch { Write-Avviso "Struttura $cdc non importata: $($_.Exception.Message)" }
    }
}

function Import-Corsi([string] $percorso) {
    Write-Passo "Importazione catalogo corsi da $percorso"
    foreach ($r in (Import-Csv -Path $percorso -Delimiter ';' -Encoding UTF8)) {
        $codice = $r.'Codice univoco corso'.Trim()
        if (Get-ElementoPerCampo 'Catalogo corsi' 'CodiceCorso' $codice) {
            Write-Avviso "Corso $codice già presente"
            continue
        }
        $valori = @{
            Title            = $r.'Titolo corso'.Trim()
            CodiceCorso      = $codice
            Descrizione      = $r.Descrizione
            EnteErogatore    = $r.'Ente erogatore'.Trim()
            NomeEnte         = $r.'Nome ente erogatore'
            Tipologia        = $r.Tipologia
            Modalita         = $r.'Modalità di svolgimento'.Trim()
            DurataCorso      = ConvertTo-Numero $r.'Durata corso (ore)'
            GettonePrevisto  = ConvertTo-Booleano $r.'Gettone previsto'
            CorsoAttivo      = ConvertTo-Booleano $r.'Corso attivo'
            PiuGiornate      = ConvertTo-Booleano $r.'Più giornate formative'
            Origine          = 'Catalogo aziendale'
            StatoValidazione = 'Validato'
        }
        try {
            Add-PnPListItem -List 'Catalogo corsi' -Values $valori | Out-Null
            Write-Ok "Corso $codice"
        }
        catch { Write-Avviso "Corso $codice non importato: $($_.Exception.Message)" }
    }
}

function Import-Lavoratori([string] $percorso) {
    Write-Passo "Importazione lavoratori da $percorso"
    # Strutture indicizzate per centro di costo
    $strutture = @{}
    foreach ($s in (Get-PnPListItem -List 'Strutture organizzative' -PageSize 2000)) {
        $strutture[$s['CentroDiCosto']] = $s
    }
    # Lavoratori già presenti
    $esistenti = @{}
    foreach ($l in (Get-PnPListItem -List 'Lavoratori' -PageSize 2000 -Fields 'Login')) {
        if ($l['Login']) { $esistenti[$l['Login'].ToLower()] = $true }
    }
    $batch = New-PnPBatch
    $inCoda = 0; $importati = 0; $saltati = 0
    foreach ($r in (Import-Csv -Path $percorso -Delimiter ';' -Encoding UTF8)) {
        $login = "$($r.Login)".Trim().ToLower()
        if (-not $login) { continue }
        if ($esistenti.ContainsKey($login)) { $saltati++; continue }
        $cognome = "$($r.Cognome)".Trim(); $nome = "$($r.Nome)".Trim()
        $valori = @{
            Title           = "$cognome $nome"
            Login           = $login
            Cognome         = $cognome
            Nome            = $nome
            EmailAziendale  = "$($r.'E-mail aziendale')".Trim()
            StatoLavoratore = $(if ($r.'Stato lavoratore') { $r.'Stato lavoratore'.Trim() } else { 'Attivo' })
            CFRegistrato    = $false
        }
        $inizio = ConvertTo-Data $r.'Data inizio validità assegnazione'
        if ($inizio) { $valori.InizioAssegnazione = $inizio }
        $fine = ConvertTo-Data $r.'Data fine validità assegnazione'
        if ($fine) { $valori.FineAssegnazione = $fine }
        $cdc = "$($r.'Centro di costo')".Trim()
        $coord = "$($r.'Login coordinatore')".Trim().ToLower()
        if ($cdc -and $strutture.ContainsKey($cdc)) {
            $s = $strutture[$cdc]
            $valori.StrutturaRif = $s.Id
            $valori.Area = $s['Area']
            $valori.Servizio = $s['Title']
            $valori.CentroDiCosto = $cdc
            if (-not $coord -and $s['CoordinatoreServizioLogin']) { $coord = $s['CoordinatoreServizioLogin'].ToLower() }
        }
        elseif ($cdc) {
            Write-Avviso "$login`: centro di costo $cdc non presente in Strutture organizzative"
            $valori.CentroDiCosto = $cdc
        }
        if ($coord) {
            $valori.CoordinatoreLogin = $coord
            $valori.CoordinatoreEmail = $coord
            $valori.CoordinatoreNome = Get-NomeUtente $coord
        }
        Add-PnPListItem -List 'Lavoratori' -Values $valori -Batch $batch
        $inCoda++; $importati++
        if ($inCoda -ge 200) { Invoke-PnPBatch -Batch $batch; $batch = New-PnPBatch; $inCoda = 0; Write-Ok "$importati lavoratori importati..." }
    }
    if ($inCoda -gt 0) { Invoke-PnPBatch -Batch $batch }
    Write-Ok "Lavoratori importati: $importati (già presenti: $saltati)"
    Write-Avviso "Gli amministratori possono completare il campo persona 'Utente Microsoft 365' dalla schermata Amministrazione (facoltativo)."
}

# -----------------------------------------------------------------------------
#  0. Controlli
# -----------------------------------------------------------------------------
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Serve PowerShell 7.4 o successivo: avviare lo script con pwsh.' }
if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
    throw 'Modulo PnP.PowerShell non installato. Eseguire: Install-Module PnP.PowerShell -Scope CurrentUser'
}
if (-not (Test-Path $template)) { throw "Modello non trovato: $template (eseguire python sharepoint/genera_template.py)" }
Import-Module PnP.PowerShell

# -----------------------------------------------------------------------------
#  1. Creazione del sito (facoltativa)
# -----------------------------------------------------------------------------
if ($CreaSito) {
    Write-Passo 'Creazione del sito'
    if (-not $Proprietario) { throw 'Con -CreaSito indicare anche -Proprietario (account amministratore del sito)' }
    $uri = [Uri] $SitoUrl
    $adminUrl = "https://$($uri.Host -replace '\.sharepoint\.com$', '-admin.sharepoint.com')"
    Connect-PnPOnline -Url $adminUrl -Interactive -ClientId $ClientId
    $esistente = Get-PnPTenantSite -Identity $SitoUrl -ErrorAction SilentlyContinue
    if ($esistente) {
        Write-Avviso "Il sito esiste già: $SitoUrl"
    }
    else {
        New-PnPTenantSite -Title 'Gestione ore formazione' -Url $SitoUrl -Owner $Proprietario `
            -Template 'STS#3' -Lcid 1040 -TimeZone 4 -Wait
        Write-Ok "Sito creato: $SitoUrl"
    }
}

# -----------------------------------------------------------------------------
#  2. Applicazione del modello
# -----------------------------------------------------------------------------
Write-Passo "Connessione a $SitoUrl"
Connect-PnPOnline -Url $SitoUrl -Interactive -ClientId $ClientId
$web = Get-PnPWeb -Includes Language
if ($web.Language -ne 1040) { Write-Avviso "La lingua del sito è $($web.Language), non italiano (1040): le etichette di sistema saranno in un'altra lingua." }

Write-Passo 'Applicazione del modello (liste, colonne, viste, gruppi, permessi)'
Invoke-PnPSiteTemplate -Path $template
Write-Ok 'Modello applicato'

# -----------------------------------------------------------------------------
#  3. Proprietari, ruoli e gruppi
# -----------------------------------------------------------------------------
Write-Passo 'Proprietari del sito, ruoli e gruppi'
$proprietari = Get-PnPGroup -AssociatedOwnerGroup
$gruppoHR = Get-PnPGroup -Identity 'Formazione - HR'
$gruppoPaghe = Get-PnPGroup -Identity 'Formazione - Paghe'

Add-MembroGruppo $proprietari $AccountServizio
foreach ($a in $Amministratori) {
    Add-MembroGruppo $proprietari $a
    Add-Ruolo $a 'Amministratore'
}
foreach ($h in $UtentiHR) {
    Add-MembroGruppo $gruppoHR $h
    Add-Ruolo $h 'Formazione HR'
}
foreach ($p in $UtentiPaghe) { Add-MembroGruppo $gruppoPaghe $p }

# -----------------------------------------------------------------------------
#  4. Configurazione
# -----------------------------------------------------------------------------
Write-Passo 'Configurazione'
Set-Configurazione 'SitoUrl' $SitoUrl
Set-Configurazione 'AccountServizio' $AccountServizio
Set-Configurazione 'EmailHR' $EmailHR
Set-Configurazione 'DestinatariPayroll' $DestinatariPayroll
Set-Configurazione 'MittenteEmail' $MittenteEmail
Set-Configurazione 'AppUrl' $AppUrl

# -----------------------------------------------------------------------------
#  5. Dati
# -----------------------------------------------------------------------------
if ($DatiEsempio) {
    Import-Strutture (Join-Path $cartella 'seed/strutture.csv')
    Import-Corsi (Join-Path $cartella 'seed/corsi.csv')
}
if ($ImportaStrutture) { Import-Strutture $ImportaStrutture }
if ($ImportaCorsi) { Import-Corsi $ImportaCorsi }
if ($ImportaLavoratori) { Import-Lavoratori $ImportaLavoratori }

# -----------------------------------------------------------------------------
#  Fine
# -----------------------------------------------------------------------------
Write-Passo 'Completato'
Write-Host @"
Passi successivi (vedi docs/04-installazione.md):
  1. Importare i flussi (powerautomate/pacchetti/*.zip) creando le connessioni con $AccountServizio
  2. Creare l'app Power Apps seguendo powerapps/README.md
  3. Scrivere il collegamento web dell'app nella lista Configurazione, chiave AppUrl
  4. Attivare i flussi nell'ordine indicato e collaudare con docs/05-collaudo.md
"@
