# Tiøren

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

**Flow:** Transaktion → Konto → Budgetposter på kontoen → Regler → Tildeling til Budgetpost(er)

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
│  │     └── Bilreparation -1.000 (løbende/øremærket)            │
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

| Felt | Beskrivelse |
|------|-------------|
| navn | "Lønkonto", "Mastercard", "Ferieopsparing" |
| formål | normal, opsparing, lån |
| datakilde | bank, kredit, kontant, virtuel |
| valuta | DKK (default) |
| startsaldo | Saldo ved oprettelse |
| kan_gå_i_minus | Om kontoen tillader negativ saldo |
| skal_dækkes | Om negativ saldo skal udlignes (kredit) |

**Konto-formål (ny!):**

| Formål | Beskrivelse | I budgettet |
|--------|-------------|-------------|
| **Normal** | Daglig økonomi | Primære konti, tæller i samlet saldo |
| **Opsparing** | Dedikeret opsparing | Auto-kategori "Opsparing" |
| **Lån** | Gæld/afdrag | Auto-kategori "Lån" |

Formål bestemmer hvordan kontoen bruges i budgettet og hvilke kategorier der auto-genereres.

**Datakilde (tidligere "type"):**

| Datakilde | Beskrivelse | Kan gå i minus | Import |
|-----------|-------------|----------------|--------|
| Bank | Normal bankkonto | Nej (eller overtræk) | Ja |
| Kredit | Kassekredit, kreditkort | Ja, skal dækkes | Ja |
| Kontant | Fysiske penge | Nej | Nej |
| Virtuel | Kun i Tiøren | Konfigurerbar | Nej |

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

| Felt | Beskrivelse |
|------|-------------|
| dato | Hvornår skete det |
| beløb | Positivt = ind, negativt = ud |
| beskrivelse | Fra banken eller manuelt |
| konto | Hvilken konto (påkrævet) |
| status | Se nedenfor |
| er_intern_overførsel | Om dette er del af intern flytning |
| modpart_transaktion | Reference til den anden side af overførslen |

**Transaktionsstatus:**

| Status | Beskrivelse |
|--------|-------------|
| ukategoriseret | Ingen regel matchede, kræver manuel håndtering |
| afventer_bekræftelse | Regel matchede, men kræver brugerbekræftelse |
| afventer_bilag | Regel kræver kvittering/opgørelse før endelig kategorisering |
| kategoriseret | Færdigbehandlet og tildelt budgetpost(er) |

**Transaktionstyper:**

| Type | Påvirker samlet saldo | Eksempel |
|------|----------------------|----------|
| Indtægt | Ja (+) | Løn, renter |
| Udgift | Ja (-) | Køb, regninger |
| Intern overførsel | Nej | Penge mellem egne konti |

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

### 3. Budgetpost (forventning)

En budgetpost beskriver **hvad vi forventer skal ske** - en plan for fremtidige pengebevægelser. Budgetposter er "forventningen" i Tiøren, mens transaktioner er "virkeligheden".

En enkelt budgetpost kan matche med **mange transaktioner** over tid (f.eks. "Husleje" matcher med 12 huslejetransaktioner om året).

| Felt | Beskrivelse |
|------|-------------|
| navn | "Løn", "Husleje", "Netflix" |
| beløb_min | Minimum forventet (eller fast beløb) |
| beløb_max | Maximum forventet |
| type | fast, loft, løbende (se budgetpost-typer) |
| konti | Én specifik konto ELLER flere konti (fleksibel) |
| gentagelse | Se mønstre nedenfor |

**Konto-binding:**

| Binding | Beskrivelse | Eksempel |
|---------|-------------|----------|
| Én specifik konto | SKAL ske på denne konto | Husleje (kun Lønkonto) |
| Flere konti (fleksibel) | Kan ske på hvilken som helst af de angivne | Dagligvarer (Lønkonto, Mastercard, Kontanter) |

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

**Gentagelsesmønstre:**

| Type | Eksempel | Beskrivelse |
|------|----------|-------------|
| Engangs | 15. nov 2026 | Én specifik dato |
| Daglig | Hver dag | Simpel daglig |
| Ugentlig | Hver mandag | Fast ugedag |
| Månedlig fast | D. 1. hver måned | Fast dato i måneden |
| Månedlig fleksibel | Mellem d. 25-31 | Vindue i måneden |
| Månedlig relativ | Sidste hverdag | Beregnet dato |
| Interval | Hver 2. uge | Fast interval |
| Kvartalsvis | 1. mar, jun, sep, dec | Specifikke måneder |
| Årlig | 15. juni hvert år | Årlig gentagelse |

**Eksempler på komplekse mønstre:**
- "Løn: Sidste hverdag i måneden"
- "Husleje: D. 1. hver måned (eller næste hverdag)"
- "El: Mellem d. 5-10 hver måned"
- "Forsikring: Kvartalsvis (mar, jun, sep, dec)"

### 4. Budget

Budget er den centrale enhed i Tiøren - en samling af økonomi-data der kan deles mellem brugere.

**Eksempler:**
- "Min private økonomi" (kun mig)
- "Fælles husholdning" (delt med partner)
- "Sommerhus" (delt med familie)

| Felt | Beskrivelse |
|------|-------------|
| navn | "Daglig økonomi", "Husholdning" |
| periode | Tidsramme (måned, år, custom) |
| konti | Liste af tilknyttede konti (påkrævet, min. 1) |
| advarselsgrænse | Advar når saldo under X |

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

| Type | Konto-binding | Eksempel |
|------|---------------|----------|
| Konto-specifik | Kun én bestemt konto | Husleje (kun Lønkonto) |
| Fleksibel | Kan ske på flere konti | Mad (Lønkonto, Mastercard, Kontanter) |

**Kategorier i Budget:**

> **Bemærk:** Kategori-konceptet er under udvikling og ikke færdigbehandlet.

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

#### Budgetpost-typer

Hver budgetpost (planlagt transaktion i et budget) har en type der bestemmer hvordan beløbet håndteres:

| Type | Beskrivelse | Nulstilling | Eksempel |
|------|-------------|-------------|----------|
| **Fast** | Præcist beløb hver periode | Ja, per periode | Husleje 8.000 kr |
| **Loft** | Maksimum beløb per periode | Ja, per periode | Mad max 3.000 kr |
| **Løbende** | Akkumulerer over tid | Nej, ruller videre | Bilreparation 1.000 kr/md |

**Fast:** Forventer præcist dette beløb hver periode. Bruges til faste udgifter som husleje, abonnementer, løn.

**Loft:** Sætter en øvre grænse for perioden. Ubrugte midler "forsvinder" ved ny periode. Bruges til variable udgifter som mad, tøj, underholdning.

**Løbende:** Beløbet akkumulerer måned for måned indtil det bruges. Fungerer som intern øremærkning til uforudsete udgifter. Bruges til bilreparation, vedligeholdelse, buffer.

```
Eksempel på løbende kategori:

Bilreparation (løbende, 1.000 kr/md)
├── Januar: +1.000 kr → Saldo: 1.000 kr
├── Februar: +1.000 kr → Saldo: 2.000 kr
├── Marts: +1.000 kr, brugt -2.500 kr → Saldo: 500 kr
├── April: +1.000 kr → Saldo: 1.500 kr
└── ...
```

**Bemærk:** Løbende kategorier ligner virtuel opsparing - pengene "øremærkes" men bliver på budgettets konti.

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

| Felt | Beskrivelse |
|------|-------------|
| fra_budgetpost | Hvilken budgetpost pengene kommer fra |
| fra_periode | Hvilken periode (kan være samme eller fremtidig) |
| til_budgetpost | Hvilken budgetpost pengene går til |
| til_periode | Hvilken periode (typisk aktuel) |
| beløb | Hvor meget der omfordeles |
| note | Valgfri forklaring |

**Vigtigt:** Omfordelinger er synlige justeringer - de ændrer ikke budget-definitionen, men vises tydeligt i rapporter og grafer.

#### Periode-lås

Afsluttede perioder låses for at bevare historisk integritet:

```
         ◄── LÅST ──►  ◄── AKTIV ──►  ◄── FREMTID ──►
         dec    jan    feb            mar    apr
Definition: [v1]   [v1]   [v2 ←────────────────────────]
                          ↑
                   Lønstigning fra 1. feb
```

**Regler:**
- Låste perioder kan ikke ændres
- Budget-ændringer gælder kun fremadrettet
- Omfordelinger kan kun laves i aktive/fremtidige perioder
- Historik bevares: "Oprindeligt budget: X, Justeret: Y"

#### Budget-sektioner baseret på konto-formål

Et budget opdeles i **sektioner** baseret på de tilknyttede kontis formål:

| Sektion | Konti med formål | Indhold |
|---------|------------------|---------|
| **Hovedsektion** | Normal | Indtægter og udgifter, samlet disponibel saldo |
| **Opsparingssektion** | Opsparing | Indskud, udtræk, opsparingssaldo |
| **Lånesektion** | Lån | Afdrag, renter, restgæld |

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

| Planlagt transaktion | Resultat ved udførelse |
|---------------------|------------------------|
| "Månedlig opsparing" (Normal → Opsparing) | -2.000 kr på Lønkonto, +2.000 kr på Ferieopsparing |
| "Udtræk til ferie" (Opsparing → Normal) | -5.000 kr på Ferieopsparing, +5.000 kr på Lønkonto |
| "Månedlig ydelse" (Normal → Lån) | -3.500 kr på Lønkonto, +3.500 kr på Billån |

**Princip:**
- **Hovedsektionens saldo** = kun normale konti (disponibelt beløb)
- **Opsparingssektionens saldo** = alt på opsparingskonti
- **Lånesektionens gæld** = saldo på lånekonti (negativ)
- Overførsler mellem sektioner **spejles** på begge konti

**Sammenligning af sektioner:**

| Aspekt | Hovedsektion | Opsparing | Lån |
|--------|--------------|-----------|-----|
| Typisk saldo | Positiv | Positiv | Negativ (gæld) |
| Mål | Balance | Øge saldo | Reducere gæld |
| Renter | N/A | Øger saldo | Øger gæld |

**Virtuelle lånekonti:**

For lån hvor man ikke har adgang til selve lånekontoen (f.eks. realkredit), oprettes en virtuel lånekonto. Transaktioner registreres manuelt eller estimeres baseret på lånevilkår.

#### Øremærkning (virtuel opsparing)

Ønskes øremærkning af penge på en normal konto (uden separat opsparingskonto), bruges en **løbende budgetpost**:

```
Udgift > Bilreparation (løbende, 1.000 kr/md)
```

Pengene akkumulerer på de normale konti, men er "øremærket" i budgettet. Se "Budgetpost-typer" for detaljer.

### 5. Kategori (Category)

> **Bemærk:** Kategori-konceptet er under udvikling og ikke færdigbehandlet.

Kategorier tilhører et Budget og bruges til at kategorisere transaktioner. Kategorier er isoleret per budget.

**Faste kategorier (kan ikke slettes):**
- **Indtægt** - penge der kommer ind (inkl. "Fra opsparing", "Fra lån")
- **Udgift** - penge der går ud (inkl. "Til opsparing", "Til lån")

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

En transaktion kategoriseres ved at bindes til en kategori i et budget. En transaktion kan splittes på flere kategorier.

### 6. Regel (Rule)

Regler håndterer automatisk matching og fordeling af transaktioner til budgetposter. Regler tilhører et Budget og deles ikke mellem budgetter.

**Princip:** Regler henviser til budgetposter (ikke kategorier direkte). Når en transaktion matcher en regel, tildeles den til de relevante budgetposter.

| Felt | Beskrivelse |
|------|-------------|
| navn | "Husleje-match", "Føtex-split" |
| betingelser | Kriterier der skal matche (se nedenfor) |
| budgetposter | Hvilke budgetposter transaktionen fordeles til |
| fordeling | Hvordan beløbet deles (procent eller fast) |
| tilstand | auto, afventer_bekræftelse, afventer_bilag |

**Betingelser (conditions):**
- Beskrivelse indeholder "NETS *FØTEX"
- Beløb er mellem -1000 og -100
- Konto er "Lønkonto"
- Dato er mellem d. 1-5 i måneden

**Regel-tilstande:**

| Tilstand | Beskrivelse | Eksempel |
|----------|-------------|----------|
| auto | Matcher og tildeler automatisk | Husleje, Netflix |
| afventer_bekræftelse | Foreslår, men bruger skal godkende | Større køb, usikre matches |
| afventer_bilag | Kræver kvittering/opgørelse før tildeling | Samlet forsikring, udgifter der skal splittes |

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

| Niveau | Tjekker | Eksempel |
|--------|---------|----------|
| Budget | Går det hele op? | Indtægt ≥ Udgift |
| Konto (specifik) | Nok til bundne poster? | Husleje kan betales fra Lønkonto |
| Konto (fleksibel) | Samlet nok + regler overholdt? | Dagligvarer kan dækkes på tværs |

---

## Nøglerelationer

| Relation | Kardinalitet | Beskrivelse |
|----------|--------------|-------------|
| Bruger → Budget | N:M | En bruger kan have flere budgetter, og budgetter kan deles |
| Budget → Konto | 1:N | Et budget har flere konti (af alle formål) |
| Konto → Budget | N:1 | En konto tilhører ét budget |
| Budget → Kategori | 1:N | Et budget har sine egne kategorier |
| Budget → Regel | 1:N | Et budget har sine egne regler |
| Budget → Budgetpost | 1:N | Et budget har flere budgetposter |
| **Budgetpost → Konto** | **N:M** | **En budgetpost kan bruges på flere konti (fleksibel)** |
| **Regel → Budgetpost** | **N:M** | **En regel kan fordele til flere budgetposter (split)** |
| Konto → Transaktion | 1:N | En konto har flere transaktioner |
| **Transaktion → Budgetpost** | **N:M** | **En transaktion kan tildeles flere budgetposter (split)** |
| Transaktion → Transaktion | 1:1 | Intern overførsel: to bundne transaktioner |
| Budget → Periode-instans | 1:N | Et budget har en instans per periode |
| Periode-instans → Omfordeling | 1:N | En periode kan have flere omfordelinger |

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
- Manuel indtastning
- CSV-import fra bank (fleksibelt format)
- Duplikat-håndtering (hash-baseret)
- Auto-kategorisering via regler
- Arkitektur klar til fremtidige bank-integrationer

### 6. Kvitteringshåndtering (fremtidig)
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
- **Ingen emoji** - hvis ikoner behøves, laves de som egentlige SVG-ikoner eller lignende. Emoji-brug virker billigt og uprofessionelt.

### Hovednavigation
1. **Overblik** - Dashboard med nøgletal og advarsler
2. **Transaktioner** - Liste, kategorisering, import
3. **Forecast** - Fremtidsudsigt med graf
4. **Budgetter** - Budgetstyring og kategorier
5. **Indstillinger** - Konti, regler, brugere

---

## Åbne spørgsmål

### Funktionalitet
- [ ] Standard kategori-liste ved oprettelse?
- [ ] Valuta-konvertering? (kun DKK til start)
- [ ] Tags udover kategorier?
- [ ] Notifikationer/påmindelser?

### Teknisk
- [ ] Authentication-metode (email/password, OAuth, begge?)
- [ ] Data-eksport format (CSV, JSON, begge?)
- [ ] Offline-support / PWA?
- [ ] API til tredjeparter?

### UX
- [ ] Onboarding-flow for nye brugere?
- [ ] Wizard til oprettelse af budget?
- [ ] Import fra andre systemer (Spiir-eksport)?

---

## Arkitektur

### Overordnet struktur

Løsningen består af to adskilte dele:

| Del | Ansvar |
|-----|--------|
| **Backend (API)** | RESTful JSON API, forretningslogik, database-adgang |
| **Frontend (UI)** | Brugergrænseflade, kalder API, renderer data |

- Backend sender **kun JSON** - aldrig færdig HTML
- Frontend er en selvstændig applikation der consumer API'et
- Klar separation muliggør uafhængig udvikling og test

### Deployment (Docker)

Løsningen deployes som tre Docker containers via Docker Compose:

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│   ┌──────────────┐                                  │
│   │ Reverse Proxy│  ← Port 80/443                   │
│   └──────┬───────┘                                  │
│          │                                          │
│    ┌─────┴─────┐                                    │
│    │           │                                    │
│    ▼           ▼                                    │
│ ┌──────┐   ┌──────┐   ┌────────────┐               │
│ │  UI  │   │ API  │───│ PostgreSQL │               │
│ └──────┘   └──────┘   └────────────┘               │
│                                                      │
│   ──── Docker network (internt) ────                │
└─────────────────────────────────────────────────────┘
```

| Container | Beskrivelse |
|-----------|-------------|
| **UI** | Serverer statiske frontend-filer |
| **API** | FastAPI backend |
| **Reverse Proxy** | Router trafik, håndterer TLS |
| **PostgreSQL** | Database (kan være ekstern) |

### Routing

| URL | Destination |
|-----|-------------|
| `domain.dk/*` | UI container |
| `domain.dk/api/*` | API container |

Reverse proxy håndterer routing baseret på URL-prefix.

### Fordele ved denne arkitektur

- **Skalerbarhed:** Containers kan skaleres uafhængigt
- **Fleksibilitet:** API kan bruges af andre klienter (mobil-app, scripts, integrationer)
- **Sikkerhed:** Reverse proxy håndterer TLS centralt
- **Udvikling:** Frontend og backend kan udvikles/testes isoleret

---

## Tech Stack (forslag)

| Komponent | Teknologi | Begrundelse |
|-----------|-----------|-------------|
| Backend | Python + FastAPI | Moderne, hurtig, god dokumentation |
| Database | PostgreSQL | Robust, JSONB til fleksible felter |
| Frontend | Vanilla JS | Simpelt, ingen build-step |
| Styling | Ren CSS | Fuld kontrol, ingen bloat |
| Grafer | TBD | Skal undersøges |
| Container | Docker | Nem deployment |
| Auth | TBD | Skal besluttes |

> **Bemærk:** Tech stack er ikke endeligt besluttet. Ovenstående er indledende forslag. De endelige teknologi-valg træffes når al anden planlægning er på plads.

---

## Næste skridt

1. Afklar kernekoncepter og relationer
2. Diskutér MVP-scope (hvad er must-have vs. nice-to-have)
3. Design database-schema
4. Design API-struktur
5. Tegn wireframes for hovedskærme
6. Prioritér og planlæg implementering

---

*Status: Under planlægning*
