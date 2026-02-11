# Tiøren - Product Specification

> This document contains the complete product specification for Tiøren.
> It is NOT auto-loaded into Claude Code sessions. Reference it when needed
> for domain understanding, UI design, or architecture decisions.

> "Så faldt tiøren" - dansk ordsprog

Personlig økonomi-app med fokus på **overblik over nutid OG fremtid**.

---

## Problemet vi løser

Eksisterende løsninger (Firefly III, YNAB, Spiir, etc.) fokuserer på:

- "Hvad har jeg brugt denne måned?"
- "Hvor mange penge har jeg lige nu?"

Men de svarer dårligt på:

- "Har jeg råd til forsikringen i november?"
- "Hvornår løber min opsparing tør hvis jeg fortsætter sådan?"
- "Er alle mine faste udgifter betalt denne måned?"

**Tiøren giver overblik over både fortid, nutid og fremtid.**

---

## Kernekoncepter

### Hierarki

```
Bruger (User)
  └── Budgetter (Budgets) - kan deles med andre brugere
        ├── Konti (Accounts) - med formål: normal, opsparing, lån
        │     └── Transaktioner (Transactions) - faktiske bevægelser
        ├── Budgetposter (forventninger) - hvad vi forventer skal ske
        │     └── bindes til én eller flere Konti
        ├── Regler (Rules) - auto-matching
        │     └── henviser til Budgetposter
        └── Kategorier (Categories) - hierarkisk
```

**Flow:** Transaktion → Konto → Budgetposter der bruger denne konto → Regler → Tildeling til Budgetpost(er)

### Visualisering af relationer

```
┌─────────────────────────────────────────────────────────────────┐
│                 BUDGET "Min økonomi"                            │
│              (kan deles med andre brugere)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  KONTI (med formål):                                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Lønkonto     │ │ Mastercard   │ │ Kontanter    │            │
│  │ formål:normal│ │ formål:normal│ │ formål:normal│            │
│  │ 10.000 kr    │ │ -500 kr      │ │ 200 kr       │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│  ┌──────────────┐ ┌──────────────┐                              │
│  │ Ferie-       │ │ Billån       │                              │
│  │ opsparing    │ │ formål: lån  │                              │
│  │ formål:opsp. │ │ -150.000 kr  │                              │
│  │ 12.000 kr    │ │ (gæld)       │                              │
│  └──────────────┘ └──────────────┘                              │
│                                                                 │
│  Samlet saldo (normale konti): 9.700 kr                         │
│                                                                 │
│  KATEGORIER:                                                    │
│  ├── Indtægt                                                    │
│  │     └── Løn +25.000 (fast)                                  │
│  ├── Udgift                                                     │
│  │     ├── Husleje -8.000 (fast)                               │
│  │     ├── Mad -3.000 (loft)                                   │
│  │     └── Bilreparation -1.000 (loft/akkumuler)               │
│  ├── Opsparing (auto fra opsparingskonti)                       │
│  │     └── Ferieopsparing -2.000                               │
│  └── Lån (auto fra lånekonti)                                   │
│        └── Billån -3.500                                        │
│                                                                 │
│  TRANSAKTIONER (på konti):                                      │
│                                                                 │
│  Lønkonto (normal):                                             │
│  • 28/1: +25.000 "Løn" → Indtægt > Løn                         │
│  • 1/2:  -8.000 "Husleje" → Udgift > Bolig                     │
│  • 1/2:  -2.000 "Til opsparing" → Opsparing                    │
│                                                                 │
│  Ferieopsparing (opsparing):                                    │
│  • 1/2:  +2.000 "Fra Lønkonto" → indskud                       │
│                                                                 │
│  Billån (lån):                                                  │
│  • 1/2:  +3.500 "Ydelse" → afdrag på gæld                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detaljerede koncepter

### 1. Konto (Account)

En container for transaktioner. Repræsenterer et sted hvor penge "bor".

| Felt           | Beskrivelse                                |
| -------------- | ------------------------------------------ |
| navn           | "Lønkonto", "Mastercard", "Ferieopsparing" |
| formål         | normal, opsparing, lån                     |
| datakilde      | bank, kredit, kontant, virtuel             |
| valuta         | DKK (default)                              |
| startsaldo     | Saldo ved oprettelse                       |
| kan_gå_i_minus | Om kontoen tillader negativ saldo          |
| skal_dækkes    | Om negativ saldo skal udlignes (kredit)    |

**Konto-formål (ny!):**

| Formål        | Beskrivelse         | I budgettet                          |
| ------------- | ------------------- | ------------------------------------ |
| **Normal**    | Daglig økonomi      | Primære konti, tæller i samlet saldo |
| **Opsparing** | Dedikeret opsparing | Auto-kategori "Opsparing"            |
| **Lån**       | Gæld/afdrag         | Auto-kategori "Lån"                  |

Formål bestemmer hvordan kontoen bruges i budgettet og hvilke kategorier der auto-genereres.

**Datakilde (tidligere "type"):**

| Datakilde | Beskrivelse             | Kan gå i minus       | Import |
| --------- | ----------------------- | -------------------- | ------ |
| Bank      | Normal bankkonto        | Nej (eller overtræk) | Ja     |
| Kredit    | Kassekredit, kreditkort | Ja, skal dækkes      | Ja     |
| Kontant   | Fysiske penge           | Nej                  | Nej    |
| Virtuel   | Kun i Tiøren            | Konfigurerbar        | Nej    |

Datakilde angiver hvor transaktioner kommer fra og tekniske egenskaber.

**Relationer:**

- Tilhører ét Budget
- Transaktioner sker på én specifik konto

**Interne overførsler:**

Når penge flyttes mellem konti inden for samme budget, oprettes to bundne transaktioner:

```
Lønkonto:   -500 kr  "Til Mastercard" ─┐
                                       ├─ bundet som intern overførsel
Mastercard: +500 kr  "Fra Lønkonto"  ─┘
```

Interne overførsler påvirker per-konto saldo, men IKKE budgettets samlede saldo.

### 2. Transaktion (Transaction)

En transaktion er en **faktisk pengebevægelse** på en konto - ikke en forventning, men noget der er sket. Transaktioner er "virkeligheden" i Tiøren, mens budgetposter er "forventningen".

| Felt                 | Beskrivelse                                 |
| -------------------- | ------------------------------------------- |
| dato                 | Hvornår skete det                           |
| beløb                | Positivt = ind, negativt = ud               |
| beskrivelse          | Fra banken eller manuelt                    |
| konto                | Hvilken konto (påkrævet)                    |
| status               | Se nedenfor                                 |
| er_intern_overførsel | Om dette er del af intern flytning          |
| modpart_transaktion  | Reference til den anden side af overførslen |

**Transaktionsstatus:**

| Status               | Beskrivelse                                                  |
| -------------------- | ------------------------------------------------------------ |
| ukategoriseret       | Ingen regel matchede, kræver manuel håndtering               |
| afventer_bekræftelse | Regel matchede, men kræver brugerbekræftelse                 |
| afventer_bilag       | Regel kræver kvittering/opgørelse før endelig kategorisering |
| kategoriseret        | Færdigbehandlet og tildelt budgetpost(er)                    |

**Transaktionstyper:**

| Type              | Påvirker samlet saldo | Eksempel                |
| ----------------- | --------------------- | ----------------------- |
| Indtægt           | Ja (+)                | Løn, renter             |
| Udgift            | Ja (-)                | Køb, regninger          |
| Intern overførsel | Nej                   | Penge mellem egne konti |

**Relationer:**

- Tilhører én Konto (fysisk faktum)
- Kan være bundet til en modpart-transaktion (intern overførsel)
- Kan tildeles én eller flere Budgetposter (via regler eller manuelt)

**Flow når transaktion ankommer:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. TRANSAKTION ANKOMMER                                         │
│    -523 kr "NETS *FØTEX" på Lønkonto                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. FIND BUDGETPOSTER DER BRUGER DENNE KONTO                     │
│    Lønkonto bruges af:                                          │
│    ├── "Husleje" (kun Lønkonto)                                 │
│    ├── "Mad-budget" (Lønkonto, Mastercard, Kontanter)           │
│    └── "Husholdning" (Lønkonto, Mastercard)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. FIND REGLER DER HENVISER TIL DISSE BUDGETPOSTER              │
│    Relevante regler:                                            │
│    ├── "Husleje-match" → Husleje                                │
│    └── "Føtex-split" → Mad-budget, Husholdning                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. KØR MATCHENDE REGLER                                         │
│    "Føtex-split" matcher (beskrivelse indeholder "FØTEX")       │
│    ├── 80% (418 kr) → Mad-budget                                │
│    └── 20% (105 kr) → Husholdning                               │
│                                                                 │
│    Status: kategoriseret (eller afventer_bekræftelse)           │
└─────────────────────────────────────────────────────────────────┘
```

**Split-kategorisering eksempel:**

```
Transaktion: -523 kr hos Føtex

Split på budgetposter:
├── 418 kr → Mad-budget (budgetpost)
└── 105 kr → Husholdning (budgetpost)
```

**Fremtidig feature:** Kvitteringsscanning med OCR + LLM til automatisk split-forslag.

**Tildelingsmodel (fast beløb + "resten"):**

- Hver tildeling gemmes som et fast beløb (i øre)
- Én tildeling kan markeres som "resten" (`is_remainder = true`)
- "Resten" beregnes som: transaktionsbeløb minus sum af øvrige tildelinger
- Hvis kun én tildeling, er den implicit "resten"
- UI kan vise/beregne procent som hjælpemiddel, men DB gemmer beløb
- Split kan ændres efterfølgende
- Validering: Sum må aldrig overstige transaktionsbeløb, "resten" kan ikke blive negativ

**Delvis tildeling:**

- En transaktion kan have en "ufordelt rest" (delvis tildeling er tilladt)
- Transaktioner med ufordelt beløb vises i afventer-listen
- Brugeren kan arbejde sig igennem transaktioner løbende
- Man kan aldrig fordele mere end transaktionens beløb
- Man kan ikke fordele 0 kr (validering)

**Ukategoriserede transaktioner:**

- Når ingen regel matcher, forbliver transaktionen ukategoriseret (ingen automatisk catch-all)
- Vises i "afventer"-liste opdelt på indtægter/udgifter
- Brugeren håndterer manuelt: tildel budgetpost, opret ny, eller opret regel
- Ukategoriserede transaktioner påvirker periodens totaler (samlet ind/ud)
- Respekterer konto-formål (transaktion på opsparingskonto påvirker kun opsparings-sektionen)
- Ingen timeout eller påmindelser i MVP - synlig badge/tæller i UI er tilstrækkeligt

### 3. Budgetpost (forventning)

En budgetpost beskriver **hvad vi forventer skal ske** - en plan for fremtidige pengebevægelser. Budgetposter er "forventningen" i Tiøren, mens transaktioner er "virkeligheden".

En enkelt budgetpost kan matche med **mange transaktioner** over tid (f.eks. "Husleje" matcher med 12 huslejetransaktioner om året).

| Felt           | Beskrivelse                                     |
| -------------- | ----------------------------------------------- |
| navn           | "Løn", "Husleje", "Netflix"                     |
| type           | fast, loft (se budgetpost-typer)                |
| akkumuler      | Kun for loft: overføres rest til næste periode? |
| beløbsmønstre  | Et eller flere beløbsmønstre (se nedenfor)      |
| from_account_ids / to_account_ids | Konti budgetposten gælder for (se "Fra/til konti model") |

**Relationer:**

- Tilhører ét Budget
- Bindes til én eller flere Konti
- Regler henviser til budgetposter (for automatisk matching)
- Transaktioner tildeles budgetposter (via regler eller manuelt)

**Eksempel på budgetpost med matchede transaktioner:**

```
Budgetpost: "Husleje"
├── Beløb: -8.000 kr (fast)
├── Type: Fast
├── Gentagelse: D. 1. hver måned
├── Konti: Kun Lønkonto
│
└── Matchede transaktioner:
    ├── 1/1: -8.000 kr "Boligforening" ✓ matched
    ├── 1/2: -8.000 kr "Boligforening" ✓ matched
    ├── 1/3: (forventet, ikke sket endnu)
    └── ...
```

**Beløbsmønstre:**

En budgetpost har et eller flere beløbsmønstre. Hvert mønster definerer et beløb og hvornår det gælder:

| Felt       | Beskrivelse                                      |
| ---------- | ------------------------------------------------ |
| beløb      | Beløbet i øre (mindste møntenhed)                |
| startdato  | Fra hvilken dato mønstret gælder (påkrævet)      |
| slutdato   | Til hvilken dato mønstret gælder (valgfri)       |
| gentagelse | Dato-baseret ELLER periode-baseret (se nedenfor) |

**Hvorfor flere mønstre?**

- Lønstigning fra 1. februar: Nyt mønster med højere beløb og ny startdato
- Sæsonvariation: El-regning varierer efter årstid (forskellige beløb per måned)
- Midlertidig ændring: Højere budget i december

**Eksempel - El-regning med sæsonvariation:**

```
Budgetpost: "El-regning"
├── Type: Fast
├── Beløbsmønstre:
│   ├── 5.000 kr i [jan, mar, nov, dec] - årligt
│   ├── 7.000 kr i [feb] - årligt
│   ├── 3.000 kr i [apr, okt] - årligt
│   └── 1.500 kr i [jun, jul, aug, sep] - årligt
```

**Gentagelsesmønstre:**

Gentagelse kan være **dato-baseret** (specifikke datoer) eller **periode-baseret** (budget-perioder).

**Dato-baseret gentagelse:**

For transaktioner der sker på specifikke datoer.

| Type               | Konfiguration                                         | Eksempel              |
| ------------------ | ----------------------------------------------------- | --------------------- |
| Engangs            | Én bestemt dato                                       | 15. nov 2026          |
| Daglig             | Hver [N] dag fra startdato                            | Hver dag              |
| Ugentlig           | Hver [N] uge på [ugedag]                              | Hver fredag           |
| Månedlig (fast)    | Hver [N] måned på dag [1-31]                          | D. 1. hver måned      |
| Månedlig (relativ) | Hver [N] måned på [første/sidste] [hverdag]           | Sidste hverdag        |
| Årlig              | Hvert [N] år i [måned] på dag [1-31] eller relativ    | 15. juni hvert år     |

**Option:** Hvis beregnet dato falder på weekend/helligdag → udskydes til næste hverdag [ja/nej]

**Periode-baseret gentagelse:**

For budgetter der gælder for perioder (måneder) snarere end specifikke datoer.

| Type              | Konfiguration                          | Eksempel                    |
| ----------------- | -------------------------------------- | --------------------------- |
| Engangs           | I specifikke måneder [jan, feb, ...]   | Kun i januar 2026           |
| Årlig gentagelse  | Hvert [N] år i måneder [jan, feb, ...] | Mar, jun, sep, dec hvert år |

**Eksempler på gentagelsesmønstre:**

- "Løn: Sidste hverdag i måneden" → Dato-baseret, månedlig relativ
- "Husleje: D. 1. hver måned (eller næste hverdag)" → Dato-baseret, månedlig fast, udskyd: ja
- "Børneopsparing: Hver fredag" → Dato-baseret, ugentlig
- "Forsikring: Kvartalsvis" → Periode-baseret, årlig i [mar, jun, sep, dec]
- "El-regning (sommer): Jun-Sep" → Periode-baseret, årlig i [jun, jul, aug, sep]

**Budgetpost-livscyklus:**

Ved periode-afslutning "spaltes" budgetposten:

- **Arkiveret budgetpost:** Den eksisterende budgetpost markeres som arkiveret (`is_archived=true`).
  Periode gemmes som `period_year` og `period_month`. Transaktioner forbliver bundet hertil. Uforanderlig.
- **Ny aktiv budgetpost:** Oprettes som klon med `successor_id` der peger på den arkiverede.
  Beløbsmønstre kopieres med justerede startdatoer. Hvis ingen mønstre er aktive fremadrettet,
  oprettes ingen ny budgetpost (budgetposten er afsluttet).
- Arkiveret og aktiv lever i samme tabel (`budget_posts`).

**Forventede forekomster:**

- Gentagelsesmønster genererer konkrete forventede forekomster per periode
- F.eks. "100 kr hver mandag" → 4-5 forventede forekomster i en måned
- Matching sker på antal forekomster, ikke bare totalt beløb

**Afvigelser:**

- Forkert antal eller beløb markeres som afvigelse
- Bruger kan "kvittere" afvigelse (har set problemet)
- Kvittering fjerner IKKE afvigelsen fra grafer/rapporter - den vises stadig
- Afvigelser kan kvitteres i både aktive og arkiverede perioder

**Beløbsmønstre over tid:**

Se "Beløbsmønstre" afsnit ovenfor for detaljer om hvordan mønstre kan overlappe (sæsonvariation) og være sekventielle (permanente ændringer som lønstigning).

**Fra/til konti model (retning):**

Budgetpostens retning bestemmes af fra/til konto-binding:

| Fra       | Til       | Retning    | Håndtering           |
| --------- | --------- | ---------- | -------------------- |
| null      | konto(er) | Indtægt    | Normal kategorisering |
| konto(er) | null      | Udgift     | Normal kategorisering |
| én konto  | én konto  | Overførsel | Auto-kategoriseret*  |

*Normal→Normal påvirker ikke budget. Andre overførsler (Normal→Opsparing, Normal→Lån, etc.) auto-kategoriseres til relevante sektioner.

**Bemærk:** "Retning" (indtægt/udgift/overførsel) er uafhængig af "type" (fast/loft). En budgetpost har begge.

**Eksempler:**
- Budgetpost "Løn" (Indtægt): `from_account_ids=null`, `to_account_ids=[Lønkonto]`
- Budgetpost "Husleje" (Udgift): `from_account_ids=[Lønkonto]`, `to_account_ids=null`
- Budgetpost "Dagligvarer" (Udgift, fleksibel): `from_account_ids=[Lønkonto, Mastercard, Kontanter]`, `to_account_ids=null`
- Budgetpost "Til ferieopsparing" (Overførsel): `from_account_ids=[Lønkonto]`, `to_account_ids=[Ferieopsparing]` → Auto-kategoriseret til Opsparing

**Saldo-effekt ved overførsler:**

| Fra → Til          | Hovedsektion saldo |
| ------------------ | ------------------ |
| Normal → Normal    | Uændret            |
| Normal → Opsparing | Falder             |
| Normal → Lån       | Falder (afdrag)    |
| Opsparing → Normal | Stiger             |

**Konti med/uden bankforbindelse:**

- Med bankforbindelse: Transaktioner importeres, skal matche
- Uden bankforbindelse (virtuel): Transaktioner oprettes manuelt eller auto-genereres som modpart

### 4. Budget

Budget er den centrale enhed i Tiøren - en samling af økonomi-data der kan deles mellem brugere.

**Eksempler:**

- "Min private økonomi" (kun mig)
- "Fælles husholdning" (delt med partner)
- "Sommerhus" (delt med familie)

| Felt            | Beskrivelse                                   |
| --------------- | --------------------------------------------- |
| navn            | "Daglig økonomi", "Husholdning"               |
| periode         | Kalendermåned (den aktuelle visningsperiode)  |
| konti           | Liste af tilknyttede konti (påkrævet, min. 1) |
| advarselsgrænse | Advar når saldo under X                       |

**Indeholder:**

- Konti (med formål: normal, opsparing, lån)
- Kategorier (hierarkiske)
- Regler for auto-kategorisering og matching
- Transaktioner (via konti)
- Budgetposter / planlagte transaktioner

**UI-tekst:** "Opret nyt budget", "Mine budgetter", etc.

**Isolation:**

Budgetter er fuldstændig isolerede fra hinanden. De deler ikke kategorier, regler eller planlagte transaktioner.

**Budget og Konti:**

Et budget kan tilknyttes flere konti (f.eks. Lønkonto + Mastercard + Kontanter). Budgettet har:

- **Samlet saldo:** Sum af tilknyttede konti med formål "normal" (den disponible saldo)
- **Per-konto saldo:** Individuel saldo for hver konto

```
Budget "Daglig økonomi"
├── Konti:
│     ├── Lønkonto (bank)      10.000 kr
│     ├── Mastercard (kredit)    -500 kr
│     └── Kontanter (virtuel)     200 kr
│     ─────────────────────────────────
│     Samlet saldo:             9.700 kr
```

**Planlagte transaktioner i et budget:**

| Type           | Konto-binding          | Eksempel                              |
| -------------- | ---------------------- | ------------------------------------- |
| Konto-specifik | Kun én bestemt konto   | Husleje (kun Lønkonto)                |
| Fleksibel      | Kan ske på flere konti | Mad (Lønkonto, Mastercard, Kontanter) |

**Kategorier i Budget:**

Kun budgetter har kategorier. De faste kategorier er:

- **Indtægt** - med bruger-definerede underkategorier (Løn, Feriepenge, ...)
- **Udgift** - med bruger-definerede underkategorier (Bolig, Mad, Transport, ...)
- **Opsparing** - auto-vises når opsparing-planer linkes til budgettet
- **Lån** - auto-vises når lån-planer linkes til budgettet

**Eksempel:**

```
Budget "Daglig økonomi"
├── Indtægt
│     └── Løn +25.000 (kun Lønkonto)
├── Udgift
│     ├── Husleje -8.000 (kun Lønkonto)
│     └── Mad -4.000 (fleksibel)
├── Opsparing (auto)
│     └── Til "Ferie 2026" -2.000
└── Lån (auto)
      └── Til "Billån" -3.500
```

**Forecasting:**

Budgettet besvarer:

1. "Har jeg råd?" → Samlet saldo
2. "Har jeg nok på lønkontoen til regningerne?" → Per-konto saldo

#### Deling og roller (post-MVP)

> **Bemærk:** Delte budgetter er en post-MVP feature (medium prioritet). Nedenstående beskriver arkitekturen der implementeres når featuren tilføjes.

Et budget kan deles med andre brugere. Der er to roller:

| Handling                       | Ejer | Medlem |
| ------------------------------ | ---- | ------ |
| Se alt                         | Ja   | Ja     |
| Oprette/redigere transaktioner | Ja   | Ja     |
| Oprette/redigere budgetposter  | Ja   | Ja     |
| Oprette/redigere regler        | Ja   | Ja     |
| Tilføje/fjerne konti           | Ja   | Ja     |
| Invitere nye medlemmer         | Ja   | Nej    |
| Fjerne medlemmer               | Ja   | Nej    |
| Slette budgettet               | Ja   | Nej    |
| Forlade budgettet              | -    | Ja     |

- Medlemmer har fuld redigerings-adgang (høj tillid, typisk familie/partner)
- Ejer beskytter mod utilsigtet sletning og medlemshåndtering
- Post-MVP: "Læseadgang"-rolle kan tilføjes hvis behov opstår

**Invitation:**

- Ejer indtaster email → system sender invitation med unikt link
- Token-levetid: 7 dage (kan gen-sendes)
- Modtager klikker link → login/opret konto → tilføjes som Medlem
- Afventende invitationer vises i budget-indstillinger, kan annulleres

**Forlade budget:**

- Medlem kan altid forlade
- Ejer kan kun forlade hvis der er mindst én anden bruger (som bliver ny ejer)
- Sidste bruger kan ikke forlade - skal slette budgettet
- Alle data (transaktioner, konti, etc.) forbliver i budgettet

**Konti og deling:**

- Konto oprettes i ét specifikt budget og lever der (`budget_id` required)
- Inden for ét budget: Duplikat-check - samme fysiske bankkonto kan kun tilføjes én gang
- På tværs af budgetter: Ingen tjek - samme konto kan bruges uafhængigt
- Delte budgetter løser use-casen hvor flere personer skal se samme konto

#### Budgetpost-typer

Hver budgetpost har en type der bestemmer hvordan beløbet håndteres:

| Type     | Beskrivelse                | Nulstilling                       | Eksempel           |
| -------- | -------------------------- | --------------------------------- | ------------------ |
| **Fast** | Præcist beløb hver periode | Ja, per periode                   | Husleje 8.000 kr   |
| **Loft** | Maksimum beløb per periode | Valgfrit: nulstil eller akkumuler | Mad max 3.000 kr   |

**Fast:** Forventer præcist dette beløb hver periode. Bruges til faste udgifter som husleje, abonnementer, løn.

**Loft:** Sætter en øvre grænse for perioden. To akkumulerings-modes:

- **Nulstil** (default): Ubrugte midler "forsvinder" ved ny periode. Bruges til variable udgifter som mad, tøj, underholdning.
- **Akkumuler**: Ubrugte/overforbrugte midler overføres til næste periode. Fungerer som intern øremærkning. Bruges til bilreparation, vedligeholdelse, buffer.

```
Eksempel på loft med akkumulering:

Bilreparation (loft, akkumuler, 1.000 kr/md)
├── Januar: budget 1.000 kr, brugt 0 kr → saldo: 1.000 kr
├── Februar: budget 2.000 kr, brugt 0 kr → saldo: 2.000 kr
├── Marts: budget 3.000 kr, brugt 2.500 kr → saldo: 500 kr
├── April: budget 1.500 kr, brugt 0 kr → saldo: 1.500 kr
└── ...
```

**Bemærk:** Loft med akkumulering ligner virtuel opsparing - pengene "øremærkes" men bliver på budgettets konti.

#### Budget-definition vs Periode-instans

Et budget har to lag:

**1. Budget-definition (skabelonen)**

Den løbende plan der beskriver hvordan økonomien ser ud:

```
Budget "Daglig økonomi" (definition)
├── Løn: +25.000 kr/md (fast)
├── Husleje: -8.000 kr/md (fast)
├── Mad: -3.000 kr/md (loft)
└── Gå i byen: -1.000 kr/md (loft)
```

- Kan ændres fremadrettet (f.eks. ved lønstigning)
- Ændringer gælder fra valgt dato og frem
- Afsluttede perioder påvirkes **ikke** af ændringer

**2. Periode-instans (den konkrete måned)**

Den faktiske status for en given periode:

```
Januar 2026 (instans)
├── Mad: Budget 3.000 kr | Brugt 3.500 kr | Rest -500 kr
├── Gå i byen: Budget 1.000 kr | Brugt 0 kr | Rest 1.000 kr
└── Status: 500 kr over budget
```

- Viser faktisk vs. planlagt
- Kan have omfordelinger (se nedenfor)
- Låses når perioden afsluttes

**Implementation:** Periode-instanser har ikke en separat tabel. De konstrueres fra:
- Arkiverede budgetposter (`is_archived=true`) for afsluttede perioder
- Aktive budgetposter + nuværende transaktioner for aktiv periode

#### Budget-omfordelinger

Når virkeligheden ikke matcher planen, kan man omfordele midler uden at ændre selve budget-definitionen:

**Scenarie:** Mad-budgettet er brugt op, men "Gå i byen" har ubrugte midler.

**Mulighed 1: Lad posten gå i negativ**

```
Mad: Budget 3.000 kr | Brugt 3.500 kr | Rest -500 kr
```

Simpelt og ærligt - viser præcist hvad der skete.

**Mulighed 2: Omfordel fra anden budgetpost (samme periode)**

```
Omfordeling i januar:
  Gå i byen → Mad: 500 kr

Resultat:
  Mad:        Budget 3.500 kr | Brugt 3.500 kr | Rest 0 kr
  Gå i byen:  Budget 500 kr   | Brugt 0 kr     | Rest 500 kr
```

Afspejler aktiv prioritering - man vælger at bruge pengene anderledes.

**Mulighed 3: Omfordel fra fremtidig periode**

```
Lån fra februar til januar:
  Mad (feb) → Mad (jan): 500 kr

Resultat:
  Mad (jan): Budget 3.500 kr | Brugt 3.500 kr | Rest 0 kr
  Mad (feb): Budget 2.500 kr | (starter med mindre)
```

Spreder konsekvensen - men skubber problemet.

**Budget-omfordeling (model):**

| Felt           | Beskrivelse                                      |
| -------------- | ------------------------------------------------ |
| fra_budgetpost | Hvilken budgetpost pengene kommer fra            |
| fra_periode    | År og måned (year, month) for kildeperioden      |
| til_budgetpost | Hvilken budgetpost pengene går til               |
| til_periode    | År og måned (year, month) for målperioden        |
| beløb          | Hvor meget der omfordeles                        |
| note           | Valgfri forklaring                               |

**Vigtigt:** Omfordelinger ændrer det budgetterede beløb for de påvirkede budgetposter i den specifikke periode. Transaktioner forbliver matchede - kun forventningen justeres. Brugeren har fuldt ansvar - systemet forhindrer ikke "dumme" omfordelinger. Budgettet er et værktøj til overblik, ikke en tvangstrøje.

#### Periode-håndtering og bekræftelses-model

Tiøren bruger en **bekræftelses-model** i stedet for eksplicit periode-låsning:

**Periode-skift trigger:**

- Primært: Automatisk ved midnat d. 1. i ny måned (scheduler/cron)
- Fallback: Ved første brugeradgang hvis automatisk skift ikke skete
- Under skift: Systemet er "låst" - brugeren ser "Vent venligst..." besked

**Ved skift:**

- Hver aktiv budgetpost arkiveres: markeres `is_archived=true`, `period_year`/`period_month` sættes
- Ny budgetpost oprettes som klon med opdaterede beløbsmønstre (se Budgetpost-livscyklus)
- Teknisk lås på budget under periode-skift for at undgå race conditions

**Ændringer i afsluttede perioder:**

- Intet brugersynligt "låse/oplåse"-koncept
- Alle ændringer til afsluttede perioder (transaktioner) samles som "afventende kladde"
- Gælder både manuelle ændringer og import af gamle transaktioner
- Regel-matching foreslås men anvendes først ved bekræftelse

**Bekræftelses-flow:**

- Brugeren samler ændringer (kan være mange)
- Før godkendelse vises konsekvenser:
  - Påvirkning af akkumulerende budgetposter
  - Ændrede afvigelser
  - Effekt på nutidens saldi
- Brugeren bekræfter samlet, ændringer træder i kraft

```
         ◄── ARKIVERET ──►  ◄── AKTIV ──►  ◄── FREMTID ──►
         dec         jan    feb            mar    apr
Definition: [v1]      [v1]   [v2 ←────────────────────────]
                             ↑
                      Lønstigning fra 1. feb

Ændringer til arkiverede perioder → samles i kladde → bekræftes samlet
```

#### Budget-sektioner baseret på konto-formål

Et budget opdeles i **sektioner** baseret på de tilknyttede kontis formål:

| Sektion               | Konti med formål | Indhold                                        |
| --------------------- | ---------------- | ---------------------------------------------- |
| **Hovedsektion**      | Normal           | Indtægter og udgifter, samlet disponibel saldo |
| **Opsparingssektion** | Opsparing        | Indskud, udtræk, opsparingssaldo               |
| **Lånesektion**       | Lån              | Afdrag, renter, restgæld                       |

```
BUDGET "Daglig økonomi"
│
├── HOVEDSEKTION (normale konti)
│   ├── Samlet saldo: 9.700 kr
│   ├── Indtægter (Løn, ...)
│   └── Udgifter (Husleje, Mad, ...)
│
├── OPSPARINGSSEKTION
│   └── Ferieopsparing
│         ├── Saldo: 12.000 kr
│         └── Planlagte: +2.000 kr/md indskud
│
└── LÅNESEKTION
      └── Billån
            ├── Restgæld: -146.500 kr
            └── Planlagte: -3.500 kr/md afdrag
```

**Planlagte transaktioner på tværs af sektioner:**

Der kan oprettes planlagte transaktioner for alle sektioner. Overførsler mellem sektioner opretter **bundne transaktioner** på begge konti:

| Planlagt transaktion                      | Resultat ved udførelse                             |
| ----------------------------------------- | -------------------------------------------------- |
| "Månedlig opsparing" (Normal → Opsparing) | -2.000 kr på Lønkonto, +2.000 kr på Ferieopsparing |
| "Udtræk til ferie" (Opsparing → Normal)   | -5.000 kr på Ferieopsparing, +5.000 kr på Lønkonto |
| "Månedlig ydelse" (Normal → Lån)          | -3.500 kr på Lønkonto, +3.500 kr på Billån         |

**Princip:**

- **Hovedsektionens saldo** = kun normale konti (disponibelt beløb)
- **Opsparingssektionens saldo** = alt på opsparingskonti
- **Lånesektionens gæld** = saldo på lånekonti (negativ)
- Overførsler mellem sektioner **spejles** på begge konti

**Sammenligning af sektioner:**

| Aspekt       | Hovedsektion | Opsparing  | Lån            |
| ------------ | ------------ | ---------- | -------------- |
| Typisk saldo | Positiv      | Positiv    | Negativ (gæld) |
| Mål          | Balance      | Øge saldo  | Reducere gæld  |
| Renter       | N/A          | Øger saldo | Øger gæld      |

**Virtuelle lånekonti:**

For lån hvor man ikke har adgang til selve lånekontoen (f.eks. realkredit), oprettes en virtuel lånekonto. Transaktioner registreres manuelt eller estimeres baseret på lånevilkår.

#### Øremærkning (virtuel opsparing)

Ønskes øremærkning af penge på en normal konto (uden separat opsparingskonto), bruges en **loft-budgetpost med akkumulering**:

```
Udgift > Bilreparation (loft, akkumuler, 1.000 kr/md)
```

Pengene akkumulerer på de normale konti, men er "øremærket" i budgettet. Se "Budgetpost-typer" for detaljer.

### 5. Kategori (Category)

Kategorier tilhører et Budget og organiserer budgetposter hierarkisk. Kategorier er isoleret per budget.

**Vigtigt princip:** Budgetpost ER kategorien. Transaktioner tildeles budgetposter (ikke separate kategorier). Kategorier er hierarkisk gruppering af budgetposter til overblik og rapporter.

**Struktur:**

- Kategorier er grupper/mapper (kan ikke modtage transaktioner direkte)
- Budgetposter er blade i hierarkiet (modtager transaktioner)
- Én budgetpost = et eller flere beløbsmønstre (med hver sin gentagelse)
- Flere budgetposter kan dele kategori

**Budgetpost-modes:**

- **Planlagt:** Har budgetteret beløb, vises altid (husleje, løn, mad)
- **Ad-hoc:** 0 kr budgetteret, vises kun når der er transaktioner (tandlæge, reparationer)

Brugeren kan oprette budgetposter on-demand ved kategorisering af transaktioner.

**Faste kategorier (kan ikke slettes):**

- **Indtægt** - penge der kommer ind (inkl. "Fra opsparing", "Fra lån")
- **Udgift** - penge der går ud (inkl. "Til opsparing", "Til lån")

**Standard kategori-preset ved oprettelse af budget:**

Nye budgetter oprettes med følgende danske kategori-struktur (kan tilpasses af brugeren):

```
Indtægt
├── Løn
└── Andet

Udgift
├── Bolig
│     ├── Husleje
│     ├── El
│     ├── Varme
│     └── Forsikring
├── Mad & dagligvarer
├── Transport
├── Abonnementer
├── Sundhed
├── Tøj
├── Underholdning
└── Andet
```

**Tags:** Tiøren understøtter ikke tags - kategorier og budgetposter dækker organiseringsbehovet.

**Auto-genererede underkategorier:**

Når opsparings- eller lånekonti tilknyttes, oprettes automatisk:

- Under Indtægt: "Fra opsparing" / "Fra lån" (med underkategori per konto)
- Under Udgift: "Til opsparing" / "Til lån" (med underkategori per konto)

**Bruger-definerede underkategorier:**

Brugeren kan oprette egne underkategorier under Indtægt og Udgift:

```
Budget "Daglig økonomi" - HOVEDBUDGET
│
├── Indtægt
│     ├── Løn
│     ├── Feriepenge
│     ├── Andet
│     ├── Fra opsparing (auto)
│     │     ├── Ferieopsparing
│     │     └── Nødfond
│     └── Fra lån (auto)
│           └── Billån
│
├── Udgift
│     ├── Bolig
│     │     ├── Husleje
│     │     ├── El
│     │     └── Varme
│     ├── Transport
│     ├── Mad & drikke
│     ├── Til opsparing (auto)
│     │     ├── Ferieopsparing
│     │     └── Nødfond
│     └── Til lån (auto)
│           └── Billån
│
OPSPARINGER (mini-budgetter)
│
├── Ferieopsparing
│     ├── Ind
│     └── Ud
│
└── Nødfond
      ├── Ind
      └── Ud

LÅN (mini-budgetter)
│
└── Billån
      ├── Ind
      └── Ud
```

**Kategorisering af transaktioner:**

En transaktion kategoriseres ved at tildeles én eller flere budgetposter. Budgetposten er "bladet" i kategori-hierarkiet.

### 6. Regel (Rule)

Regler håndterer automatisk matching og fordeling af transaktioner til budgetposter. Regler tilhører et Budget og deles ikke mellem budgetter.

**Princip:** Regler henviser til budgetposter (ikke kategorier direkte). Når en transaktion matcher en regel, tildeles den til de relevante budgetposter.

| Felt         | Beskrivelse                                    |
| ------------ | ---------------------------------------------- |
| navn         | "Husleje-match", "Føtex-split"                 |
| betingelser  | Kriterier der skal matche (se nedenfor)        |
| budgetposter | Hvilke budgetposter transaktionen fordeles til |
| fordeling    | Hvordan beløbet deles (procent eller fast)     |
| tilstand     | auto, afventer_bekræftelse, afventer_bilag     |

**Betingelser (conditions):**

- Beskrivelse indeholder "NETS \*FØTEX"
- Beløb er mellem -1000 og -100
- Konto er "Lønkonto"
- Dato er mellem d. 1-5 i måneden

**Regel-tilstande:**

| Tilstand             | Beskrivelse                               | Eksempel                                      |
| -------------------- | ----------------------------------------- | --------------------------------------------- |
| auto                 | Matcher og tildeler automatisk            | Husleje, Netflix                              |
| afventer_bekræftelse | Foreslår, men bruger skal godkende        | Større køb, usikre matches                    |
| afventer_bilag       | Kræver kvittering/opgørelse før tildeling | Samlet forsikring, udgifter der skal splittes |

**Eksempel 1: Simpel regel (auto)**

```
Regel: "Husleje-match"
├── Tilstand: auto
├── Betingelser:
│   ├── Beskrivelse indeholder "Boligforening"
│   ├── Beløb er mellem -8500 og -7500
│   └── Dato er mellem d. 1-3 i måneden
└── Tildeling:
    └── 100% → Budgetpost "Husleje"
```

**Eksempel 2: Split-regel (auto)**

```
Regel: "Føtex-split"
├── Tilstand: auto
├── Betingelser:
│   └── Beskrivelse indeholder "FØTEX"
└── Tildeling:
    ├── 80% → Budgetpost "Mad-budget"
    └── 20% → Budgetpost "Husholdning"
```

**Eksempel 3: Regel der afventer bilag**

```
Regel: "Tryg-forsikring"
├── Tilstand: afventer_bilag
├── Betingelser:
│   └── Beskrivelse indeholder "Tryg"
└── Ved bilag modtaget:
    LLM parser opgørelse og foreslår:
    ├── 800 kr → Budgetpost "Indboforsikring"
    ├── 1.200 kr → Budgetpost "Bilforsikring"
    └── 500 kr → Budgetpost "Ulykkesforsikring"

    Bruger bekræfter eller justerer fordeling.
```

**Relationer:**

- Tilhører ét Budget
- Henviser til én eller flere Budgetposter
- Matcher Transaktioner baseret på betingelser

**Regel-prioritet og matching:**

- Regler har en rækkefølge/prioritet (sorteret liste)
- Første matchende regel anvendes - øvrige ignoreres
- Én regel definerer hele fordelingen (kan indeholde split til flere budgetposter)
- Hvis reglen ikke fordeler 100%, ender resten som ukategoriseret
- Brugeren kan omsortere regler for at ændre prioritet

**Matching-strategi:**

- Matching sker via regel ELLER manuelt (ingen implicit matching baseret på dato/beløb alene)
- Alle betingelser i en regel skal passe for at reglen matcher (AND-logik)
- Tolerance og betingelser defineres per regel, ikke globalt

**Betingelsestyper:**

- Dato inden for X dage fra beløbsmønsterets forventede dato
- Beløb matcher præcist (beløbsmønsterets beløb)
- Beløb inden for ± X af beløbsmønsterets beløb
- Tekst indeholder/matcher mønster
- Konto er én af (arvet fra budgetpost eller specificeret)

**Matching-flow:**

1. Transaktion ankommer på en konto
2. Find budgetposter der har kontoen i deres `from_account_ids` eller `to_account_ids`
3. Find regler der er tilknyttet de fundne budgetposter
4. Kør reglerne i prioritetsrækkefølge
5. Første matchende regel anvendes

### 7. Validering (saldo-tjek)

Tiøren validerer på to niveauer for at sikre der er penge nok til alle forventede udgifter.

**Niveau 1: Budgetniveau (samlet)**

Tjekker om budgettet som helhed går op:

- Samlet indtægt vs. samlet udgift
- Er der balance eller overskud?

```
Budget "Daglig økonomi" - BUDGETNIVEAU
├── Samlet indtægt: +25.000 kr
├── Samlet udgift:  -23.000 kr
└── Balance:         +2.000 kr ✓
```

**Niveau 2: Kontoniveau (per konto)**

Tjekker om hver konto har nok til sine konto-specifikke budgetposter:

- Respekterer kontoens regler (kan_gå_i_minus)
- Reserverer beløb til konto-bundne poster

```
Lønkonto - KONTONIVEAU
├── Saldo: 10.000 kr
├── Konto-specifikke budgetposter:
│   ├── Husleje: -8.000 kr (kun Lønkonto)
│   ├── El: -500 kr (kun Lønkonto)
│   └── Løn: +25.000 kr (kun Lønkonto)
├── Forventet resultat: +16.500 kr ✓
└── Konto-regel: Kan ikke gå i minus ✓
```

**Fleksible budgetposter (flere konti):**

Når en budgetpost kan betales fra flere konti, gælder:

1. **Samlet** skal der være nok på tværs af de tilknyttede konti
2. **Per konto** må ingen fordeling bryde kontoens regler

```
Budgetpost: "Dagligvarer" -4.000 kr
├── Konti: Lønkonto, Mastercard, Kontanter
│
├── Tilgængelig saldo:
│   ├── Lønkonto:  5.000 kr (kan ikke gå i minus)
│   ├── Mastercard: -200 kr (limit -5.000, dvs. 4.800 til rådighed)
│   └── Kontanter:   300 kr (kan ikke gå i minus)
│   ─────────────────────────────────────────
│   Samlet til rådighed: 10.100 kr ✓
│
└── Validering:
    ├── Samlet nok: 10.100 kr ≥ 4.000 kr ✓
    └── Enhver fordeling må ikke bryde konto-regler
        (f.eks. kan Lønkonto max bidrage med 5.000 kr)
```

**Opsummering af validering:**

| Niveau            | Tjekker                        | Eksempel                         |
| ----------------- | ------------------------------ | -------------------------------- |
| Budget            | Går det hele op?               | Indtægt ≥ Udgift                 |
| Konto (specifik)  | Nok til bundne poster?         | Husleje kan betales fra Lønkonto |
| Konto (fleksibel) | Samlet nok + regler overholdt? | Dagligvarer kan dækkes på tværs  |

---

## Nøglerelationer

| Relation                      | Kardinalitet | Beskrivelse                                                |
| ----------------------------- | ------------ | ---------------------------------------------------------- |
| Bruger → Budget               | N:M          | En bruger kan have flere budgetter, og budgetter kan deles |
| Budget → Konto                | 1:N          | Et budget har flere konti (af alle formål)                 |
| Konto → Budget                | N:1          | En konto tilhører ét budget                                |
| Budget → Kategori             | 1:N          | Et budget har sine egne kategorier                         |
| Budget → Regel                | 1:N          | Et budget har sine egne regler                             |
| Budget → Budgetpost           | 1:N          | Et budget har flere budgetposter                           |
| **Budgetpost → Konto**        | **N:M**      | **En budgetpost kan bruges på flere konti (fleksibel)**    |
| **Regel → Budgetpost**        | **N:M**      | **En regel kan fordele til flere budgetposter (split)**    |
| Konto → Transaktion           | 1:N          | En konto har flere transaktioner                           |
| **Transaktion → Budgetpost**  | **N:M**      | **En transaktion kan tildeles flere budgetposter (split)** |
| Transaktion → Transaktion     | 1:1          | Intern overførsel: to bundne transaktioner                 |
| Budget → Budgetpost (arkiveret) | 1:N        | Et budget har mange arkiverede budgetposter over tid       |
| Budgetpost → Omfordeling        | 1:N        | En budgetpost kan have omfordelinger i sin periode         |

**Bemærk:** Budgettet opdeles i sektioner baseret på konto-formål (normal, opsparing, lån). Se Budget-sektionen for detaljer.

**Centrale relationer for transaktion-flow:**

```
Transaktion (virkelighed)
     ↓ sker på
   Konto
     ↓ bruges af
Budgetposter (forventning)
     ↑ henviser til
   Regler (matching)
```

---

## Hovedfunktioner

### 1. Transaktionsoversigt

- Se alle transaktioner (filtrér på konto, kategori, dato)
- Kategorisér ukategoriserede
- Split en transaktion på flere kategorier
- Match med planlagte transaktioner
- Vedhæft kvitteringer (billede/scan)

### 2. Forecast / Fremtidsudsigt

- Se forventet saldo X måneder frem
- Baseret på planlagte transaktioner
- **Samlet saldo:** "Har jeg råd til dette?"
- **Per-konto saldo:** "Har Lønkonto nok til regningerne?"
- Markér når planlagt ≠ faktisk
- Advarsler ved forventet underskud (samlet eller per-konto)

### 3. Regnings-tjek

- "Er alle mine faste udgifter betalt denne måned?"
- Liste over planlagte udgifter med status:
  - [Betalt] - matched med faktisk transaktion
  - [Afventer] - dato ikke nået endnu
  - [Forsinket] - dato passeret, ikke matched
  - [Mangler] - betydeligt forsinket

### 4. Kategori-analyse

- "Hvor meget bruger jeg på X per måned?"
- Grafer og trends over tid
- Sammenlign perioder
- Drill-down i hierarkiet

### 5. Import

**Grundlæggende:**

- Manuel indtastning
- CSV-import fra bank (fleksibelt format)
- Duplikat-håndtering (hash-baseret)
- Auto-kategorisering via regler
- Arkitektur klar til fremtidige bank-integrationer

**Duplikat-detection:**

- `external_id` - bankens unikke reference (gemmes separat, kan være null)
- `import_hash` - hash af (konto_id + dato + tidsstempel + beløb + beskrivelse)
- Tidsstempel inkluderes hvis tilgængeligt

**Duplikat-tjek ved import:**

1. Hvis `external_id` findes → tjek mod eksisterende
2. Uanset → tjek også mod `import_hash`
3. Potentielle duplikater vises til brugeren
4. Brugeren vælger: "Skip (duplikat)" eller "Importér (ny transaktion)"

**CSV-import flow:**

1. Bruger uploader CSV
2. System viser preview af første rækker
3. Bruger mapper kolonner (Dato, Beløb, Beskrivelse, Bank-reference, Tidsstempel, Saldo)
4. Mapping gemmes som "profil" til fremtidige imports

**Dato- og tal-format:**

- Auto-detect baseret på data
- Brugeren bekræfter/justerer i preview
- Gemmes i import-profilen
- Preview viser fortolkning så brugeren kan verificere
- Understøtter dansk (1.234,56) og engelsk (1,234.56) format

**Import-profiler:**

- Gemmes per konto (f.eks. "Nordea CSV", "Danske Bank CSV")
- Kan genbruges ved fremtidige imports

### 6. Eksport

**Formater:**

- **CSV** - til analyse i regneark (Excel, Google Sheets)
- **JSON** - til backup og migration (bevarer struktur og relationer)

**Eksport-muligheder:**

- Transaktioner (filtrérbar på periode, konto, kategori)
- Budgetposter
- Komplet budget-backup (JSON)

### 7. Kvitteringshåndtering (fremtidig)

- Upload/scan kvittering
- OCR + LLM til udtræk af linjer
- Foreslå split-kategorisering
- Gem kvittering på transaktionen

---

## Brugergrænsefladen

### Principper

- **Visuelt frem for tekst-tungt** - inspiration fra Spiir
- **Intuitiv oprettelse** af planlagte transaktioner
- **Mobil-venlig** (responsive)
- **Hurtig** - ingen unødvendig loading
- **Ingen emoji** - hvis ikoner behøves, bruges Lucide Icons (open source, ISC licens)
- **Ikoner som inline SVG** for nem CSS-styling og farvetilpasning

### Overordnet stil

**Inspiration:** Moderne finans-apps (Spiir, Lunar, N26) - rent, minimalistisk, data-drevet.

**Karakteristika:**

- Mørk/lys tema (brugervalg)
- Store, læsbare tal
- Visuel feedback via farver (grøn = positiv, rød = negativ)
- Kort og cards som primære containere
- Generøs whitespace

### Farvepalette (forslag)

#### Lys tema

| Funktion        | Farve        | Hex       |
| --------------- | ------------ | --------- |
| Baggrund        | Hvid/lysegrå | `#FAFAFA` |
| Primær tekst    | Mørkegrå     | `#1A1A1A` |
| Sekundær tekst  | Grå          | `#6B7280` |
| Accent (primær) | Blå          | `#3B82F6` |
| Positiv/indtægt | Grøn         | `#10B981` |
| Negativ/udgift  | Rød          | `#EF4444` |
| Advarsel        | Orange       | `#F59E0B` |
| Kort-baggrund   | Hvid         | `#FFFFFF` |
| Border          | Lysegrå      | `#E5E7EB` |

#### Mørk tema

Inverterede farver med dæmpede accenter. (Post-MVP feature)

#### CSS-tokenisering

Farver implementeres som CSS custom properties med semantiske navne:

```css
:root {
  /* Baggrunde */
  --bg-page: #fafafa;
  --bg-card: #ffffff;

  /* Tekst */
  --text-primary: #1a1a1a;
  --text-secondary: #6b7280;

  /* Semantiske farver */
  --accent: #3b82f6;
  --positive: #10b981;
  --negative: #ef4444;
  --warning: #f59e0b;

  /* Borders */
  --border: #e5e7eb;
}
```

Semantiske navne (`--positive`) bruges frem for farvenavne (`--green`) for nem tema-switching.

### Layout-struktur

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER                                                     │
│  ┌─────────────┐                    ┌──────┐ ┌──────┐      │
│  │ Tiøren logo │    [Budget-vælger]    │notif││profil│      │
│  └─────────────┘                    └──────┘ └──────┘      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  NAVIGATION (sidebar på desktop, bottom-bar på mobil)       │
│  ┌──────────────┐                                          │
│  │ * Overblik   │                                          │
│  │ * Transakt.  │  <- Badge hvis ukategoriserede           │
│  │ * Forecast   │                                          │
│  │ * Budget     │                                          │
│  │ * Indstill.  │                                          │
│  └──────────────┘                                          │
│                                                             │
│  CONTENT AREA                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │   (Skærm-specifikt indhold)                         │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Hovednavigation

1. **Overblik** - Dashboard med nøgletal og advarsler
2. **Transaktioner** - Liste, kategorisering, import
3. **Forecast** - Fremtidsudsigt med graf
4. **Budgetter** - Budgetstyring og kategorier
5. **Indstillinger** - Konti, regler, brugere

### Skærme

See the UI wireframes in the original specification for detailed screen layouts:
- Skærm 1: Overblik (Dashboard)
- Skærm 2: Transaktioner
- Skærm 3: Forecast
- Skærm 4: Budget
- Modal: Kategorisering af transaktion

### Responsivt design

**Tilgang:** Desktop-first med responsivt design til mobil.

**Breakpoint:** 768px

| Aspekt      | Desktop (>=768px)             | Mobil (<768px)                     |
| ----------- | ----------------------------- | ---------------------------------- |
| Navigation  | Sidebar                       | Bottom-bar (5 ikoner)              |
| Layout      | Multi-kolonne                 | Stacked cards                      |
| Modals      | Centered overlay              | Fullscreen                         |
| Primær brug | Regnskab, import, planlægning | Status-tjek, hurtig kategorisering |

---

## Arkitektur

### Overordnet struktur

Løsningen består af to adskilte dele:

| Del               | Ansvar                                              |
| ----------------- | --------------------------------------------------- |
| **Backend (API)** | RESTful JSON API, forretningslogik, database-adgang |
| **Frontend (UI)** | Brugergrænseflade, kalder API, renderer data        |

- Backend sender **kun JSON** - aldrig færdig HTML
- Frontend er en selvstændig applikation der consumer API'et
- Klar separation muliggør uafhængig udvikling og test

### Deployment (Docker)

Løsningen deployes som tre Docker containers via Docker Compose:

| Container         | Beskrivelse                      |
| ----------------- | -------------------------------- |
| **UI**            | Serverer statiske frontend-filer |
| **API**           | FastAPI backend                  |
| **Reverse Proxy** | Router trafik, håndterer TLS     |
| **PostgreSQL**    | Database (kan være ekstern)      |

### Routing

| URL               | Destination   |
| ----------------- | ------------- |
| `domain.dk/*`     | UI container  |
| `domain.dk/api/*` | API container |

Reverse proxy håndterer routing baseret på URL-prefix.

---

## Database-specifikationer

### Primærnøgler

- **UUID** (UUIDv7 foretrukket) bruges som primærnøgle på alle entiteter
- UUIDv7 er tidsbaseret og sortérbar, hvilket giver bedre indeks-performance
- UUIDv4 som fallback hvis PostgreSQL < 17
- Fordele: Ingen enumeration-angreb, kan genereres på klient (fremtidig offline-support)

### Soft delete

Hovedentiteter bruger soft delete med `deleted_at` timestamp:

- Budgetter, Konti, Budgetposter, Regler, Kategorier, Transaktioner
- Soft-deleted filtreres fra i normale queries
- Periodisk cleanup kan permanent slette gamle soft-deleted records (f.eks. > 1 år)

Permanent sletning bruges på:

- Junction-tabeller (tildelinger)
- Sessions/tokens

### Audit trail

Minimal audit trail til MVP:

| Entitet                        | created_at | updated_at | created_by | updated_by |
| ------------------------------ | ---------- | ---------- | ---------- | ---------- |
| User                           | Ja         | Ja         | -          | -          |
| Budget                         | Ja         | Ja         | Ja         | Ja         |
| Konto                          | Ja         | Ja         | Ja         | Ja         |
| Transaktion                    | Ja         | Ja         | Ja         | Ja         |
| Budgetpost                     | Ja         | Ja*        | Ja         | Ja         |
| Beløbsmønster                  | Ja         | Ja         | -          | -          |
| Kategori                       | Ja         | Ja         | Ja         | Ja         |
| Regel                          | Ja         | Ja         | Ja         | Ja         |
| Tildeling (junction)           | Ja         | Ja         | -          | -          |
| Omfordeling                    | Ja         | Ja         | Ja         | Ja         |

*Arkiverede budgetposter (`is_archived=true`) er uforanderlige efter arkivering - `updated_at` opdateres ikke.

### Budgetpost-arkivering

Budgetposter arkiveres ved periode-afslutning. Aktive og arkiverede lever i samme tabel:

| Felt           | Type    | Beskrivelse                                          |
| -------------- | ------- | ---------------------------------------------------- |
| is_archived    | bool    | Om budgetposten er arkiveret (default: false)        |
| period_year    | int     | Periodens år (kun for arkiverede, null ellers)       |
| period_month   | int     | Periodens måned 1-12 (kun for arkiverede)            |
| successor_id   | UUID    | Reference til den nye aktive budgetpost (hvis nogen) |

Se "Budgetpost-livscyklus" for detaljer om arkiveringsprocessen.

### Budgetpost konto-binding

Budgetposter bindes til konti via JSONB-felter:

| Felt              | Type       | Beskrivelse                                              |
| ----------------- | ---------- | -------------------------------------------------------- |
| from_account_ids  | UUID[]     | Konti penge trækkes fra (udgift). Null for indtægter.    |
| to_account_ids    | UUID[]     | Konti penge går til (indtægt). Null for udgifter.        |

Se "Fra/til konti model" for retningslogik. Kun én af fra/til kan være sat (ikke begge - undtagen overførsler).

### Beløb-præcision

- Beløb gemmes som **integer** i mindste møntenhed (øre for DKK)
- Eksempel: 1.234,56 kr = 123456
- Undgår floating-point afrundingsfejl
- Hurtigere beregninger, simpel sammenligning
- Kolonnenavn: `amount` (generisk, ikke bundet til specifik valuta)
- BIGINT giver rigeligt med plads

### Split-tildelinger (remainder-model)

Ved split af transaktioner bruges fast beløb + "resten"-model:

- Tildelinger gemmes som faste beløb (integer)
- Én tildeling markeres som `is_remainder = true`
- Remainder beregnes som: transaktionsbeløb - sum(øvrige tildelinger)
- Eksempel 3-vejs split af 1.000 kr: 33333 + 33333 + 33334 (remainder) = 100000 øre
- Validering: sum må aldrig overstige transaktionsbeløb, remainder kan ikke blive negativ

---

## Authentication og sikkerhed

### Login-metode

- **Email/password** til MVP
- OAuth (Google) kan tilføjes post-MVP som supplement
- Passer naturligt med email-invitation til delte budgetter

### Password-krav

- Minimum: 12 tegn
- Maximum: 128 tegn
- Ingen kompleksitetskrav (ingen krav om tal, store bogstaver, specialtegn)
- Valgfrit: Tjek mod top 10.000 mest almindelige passwords
- UI: Password strength-indikator

### Session-håndtering

**Web UI (sessions):**

- Session-ID i cookie (HttpOnly, Secure, SameSite=Strict)
- Session-data i PostgreSQL
- Levetid: 30 dage (sliding expiration ved aktivitet)
- Ved logout/password-skift: Invalidér alle sessions for brugeren

**Programmatisk adgang (API-tokens, post-MVP):**

- Brugeren kan oprette API-tokens i indstillinger
- Tokens har valgfri udløbsdato (eller "aldrig")
- Tokens kan have begrænset scope (læs/skriv, specifikke budgetter)
- Bruges til integrationer (Home Assistant, scripts, etc.)
- Tokens kan tilbagekaldes individuelt

### Password-reset

- Bruger anmoder om reset → email med unikt link sendes
- Token-levetid: 1 time
- Token kan kun bruges én gang, hashet i database
- Ved nyt password: Alle sessions invalideres
- Rate limiting: Max 3 reset-emails per time per email
- Feedback: Altid "Hvis emailen findes, har vi sendt et link" (ingen enumeration)

### Email-verifikation

- Email skal verificeres før brugeren kan tilgå appen
- Flow: Opret konto → "Tjek din email" → Klik link → Adgang
- Token-levetid: 24 timer
- Kan gen-sende verifikations-email (rate limited: max 3 per time)
- Uverificerede konti slettes automatisk efter 7 dage

---

## API-design

### Forecast-beregning

- On-the-fly beregning, ingen persisteret cache til MVP
- Fokus på optimeret datalagring og effektive SQL-queries
- Aggregater beregnes direkte i databasen (undgå N+1 queries)
- Budgetpost-gentagelser udfoldes i hukommelsen (billigt for personlige budgetter)
- Hvis performance bliver et problem post-MVP, kan cache-lag tilføjes (f.eks. Redis)

### Forecast-horisont

- Default visning: 12 perioder (nuværende + 11 fremtidige, eller mix af forrige/fremtidige)
- API accepterer vilkårlig periode-range (start/slut måned)
- Ingen hård grænse - brugeren kan se f.eks. hele 2027 fra 2026
- Frontend tilbyder standard-views (3, 6, 12 måneder) + mulighed for custom range

### Validerings-respons

To-niveau respons med errors og warnings:

- **Errors:** Blokerende fejl, handlingen afvises (manglende felter, ugyldigt format, ugyldige referencer)
- **Warnings:** Handlingen gennemføres, men brugeren adviseres (budget i minus, potentiel duplikat)
- Respons inkluderer `success`, `data`, `errors[]` og/eller `warnings[]`

### Pagination

Cursor-baseret pagination:

- Cursor er encoded reference til sidste element (f.eks. base64 af id + dato)
- Stabil ved ændringer - ingen "hop" eller duplikater når data ændres
- Format: `GET /api/.../transactions?limit=50&cursor=abc123`
- Respons inkluderer `next_cursor` (null hvis ingen flere)

### Rate limiting

| Endpoint-type      | Grænse             |
| ------------------ | ------------------ |
| Generelle API-kald | 100/min per bruger |
| Login-forsøg       | 5/min per IP       |
| Password reset     | 3/time per email   |
| Email-verifikation | 3/time per email   |

HTTP 429 "Too Many Requests" ved overskridelse med `Retry-After` header.

---

## Tech Stack

| Komponent          | Teknologi                                                       | Begrundelse                                                                   |
| ------------------ | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Backend            | Python + FastAPI                                                | Moderne, hurtig, god dokumentation                                            |
| Database           | PostgreSQL                                                      | Robust, JSONB til fleksible felter                                            |
| Frontend           | Svelte                                                          | Kompilerer til vanilla JS, minimal runtime, reaktivitet indbygget, scoped CSS |
| Styling            | Scoped CSS (Svelte)                                             | Indbygget i Svelte, ingen naming-konflikter, bruger CSS custom properties     |
| Grafer             | Apache ECharts                                                  | Built-in Sankey support, custom build ~300KB                                  |
| Auth               | passlib (bcrypt), itsdangerous, slowapi                         | Simpel custom implementation                                                  |
| Migrations         | Alembic                                                         | Standard for SQLAlchemy                                                       |
| Ikoner             | Lucide Icons                                                    | Open source (ISC), inline SVG                                                 |
| Test               | pytest (backend)                                                | Pragmatisk MVP-tilgang, manuel test for frontend                              |
| Container          | Docker Compose                                                  | Nem selfhosted deployment                                                     |
| Base images        | python:3.12-slim (API), nginx:alpine (UI), caddy:alpine (proxy) | Undgår Alpine/musl-problemer med Python                                       |
| Frontend webserver | Nginx                                                           | Industristandard, hurtig, minimal ressourceforbrug                            |
| Reverse proxy      | Caddy                                                           | Automatisk HTTPS, simpel config, perfekt til selfhosted                       |

### CI/CD

- **MVP:** GitHub som backup og versionering, manuel deployment
- **Post-MVP:** GitHub Actions med lint, test og auto-deploy

---

## Language and Internationalization

### Code and Documentation Language

All code and documentation must be written in **English**:

| Element                 | Language | Example                              |
| ----------------------- | -------- | ------------------------------------ |
| Variable/function names | English  | `get_account_balance()`, `isLoading` |
| Comments                | English  | `// Calculate running total`         |
| Commit messages         | English  | `feat(auth): add session management` |
| Documentation           | English  | README, API docs, code comments      |
| Error messages (code)   | English  | `raise ValueError("Invalid amount")` |

### User-Facing Text (i18n)

User-facing text uses **translation files** with Danish as default:

| Element             | Approach                                          |
| ------------------- | ------------------------------------------------- |
| UI labels           | Translation keys, e.g., `$t('dashboard.balance')` |
| Error messages (UI) | Translation keys                                  |
| Default locale      | Danish (`da`)                                     |
| Future locales      | Prepared structure for `en`, `de`, etc.           |

### Translation File Structure

```
ui/src/lib/i18n/
├── index.ts          # i18n setup and helper functions
├── locales/
│   ├── da.json       # Danish (default)
│   └── en.json       # English (placeholder for future)
```

### Translation File Format

```json
{
  "common": {
    "save": "Gem",
    "cancel": "Annuller",
    "delete": "Slet",
    "loading": "Indlæser..."
  },
  "dashboard": {
    "title": "Overblik",
    "availableBalance": "Disponibel saldo",
    "thisMonth": "Denne måned"
  },
  "auth": {
    "login": "Log ind",
    "register": "Opret konto",
    "email": "Email",
    "password": "Adgangskode"
  }
}
```

### Implementation Notes

- Use a simple i18n approach (e.g., `svelte-i18n` or custom lightweight solution)
- All hardcoded Danish text in UI must use translation keys
- Backend API responses use English; translation happens in frontend
- Database content (user data) is not translated

---

## MVP-scope

### Must-have (MVP)

Følgende funktioner er påkrævet til første version:

- **Bruger-registrering og login** (email/password)
- **Opret/rediger budget og konti**
- **Manuel oprettelse af transaktioner**
- **Kategorisering** (tildel transaktion til budgetpost)
- **Budgetposter med gentagelse**
- **Dashboard** (saldo, afventer-liste, faste udgifter)
- **Simpel forecast** (linjegraf + tabel)

### Nice-to-have (post-MVP, prioriteret)

| Prioritet | Feature                    | Beskrivelse                            |
| --------- | -------------------------- | -------------------------------------- |
| Høj       | CSV-import                 | Import af transaktioner fra bankudtræk |
| Høj       | Regler/auto-kategorisering | Automatisk matching af transaktioner   |
| Medium    | Delte budgetter            | Del budget med partner/familie         |
| Lav       | Mørkt tema                 | Alternativt farvetema                  |
| Lav       | Kvitteringshåndtering/OCR  | Scan og parse kvitteringer             |
| Lav       | API-tokens                 | Programmatisk adgang til data          |

### Eksplicit IKKE i MVP

- Delte budgetter (post-MVP, medium prioritet)
- CSV-import (post-MVP, høj prioritet - første feature efter MVP)
- API-tokens (post-MVP, lav prioritet)
- Mørkt tema (post-MVP, lav prioritet)
- Offline-support / PWA (ikke planlagt)
- Onboarding-wizard (ikke nødvendigt - simpel oprettelse)
- Import fra andre systemer (Spiir etc.)

---

_Status: MVP specifikation komplet. Se CLAUDE.md for udviklings-workflow._
