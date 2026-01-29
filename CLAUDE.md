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
  └── Regnskaber (Ledgers) - kan deles med andre brugere
        ├── Konti (Accounts) - bankkonti, kontanter
        ├── Kategorier (Categories) - hierarkisk
        ├── Regler (Rules) - auto-kategorisering og matching
        ├── Transaktioner (Transactions) - faktiske bevægelser
        └── Planer (Plans)
              ├── Budget - løbende økonomi
              ├── Opsparing - spare op til noget
              └── Lån - afbetale gæld
```

### Visualisering af relationer

```
┌─────────────────────────────────────────────────────────────────┐
│                        REGNSKAB                                 │
│                   (f.eks. "Fælles økonomi")                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   KONTO      │  │   KONTO      │  │   KONTO      │          │
│  │  Lønkonto    │  │  Opsparing   │  │  Visa        │          │
│  │  12.450 kr   │  │  45.000 kr   │  │  -2.300 kr   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └────────────┬────┴─────────────────┘                   │
│                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  TRANSAKTIONER                          │   │
│  │  (faktiske pengebevægelser - tilhører én konto)         │   │
│  │                                                         │   │
│  │  • 28/1: +25.000 (Lønkonto) ← matched med "Løn"        │   │
│  │  • 1/2:  -8.000 (Lønkonto)  ← matched med "Husleje"    │   │
│  │  • 3/2:  -523 (Visa)        ← split: Dagligvarer + Vin │   │
│  │  • 5/2:  -5.000 (Lønkonto)  ← matched med 2 opsparinger│   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ matching via regler              │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     PLANER                              │   │
│  │                                                         │   │
│  │  ┌─────────────────┐  ┌─────────────────┐              │   │
│  │  │ BUDGET          │  │ OPSPARING       │              │   │
│  │  │ "Månedligt"     │  │ "Ferie 2026"    │              │   │
│  │  │                 │  │                 │              │   │
│  │  │ Bruger konti:   │  │ Mål: 30.000 kr  │              │   │
│  │  │ • Lønkonto      │  │ Deadline: Jul   │              │   │
│  │  │ • Visa          │  │                 │              │   │
│  │  │                 │  │ Bruger konto:   │              │   │
│  │  │ Planlagte:      │  │ • Opsparing     │              │   │
│  │  │ • Løn +25.000   │  │                 │              │   │
│  │  │ • Husleje -8.000│  │ Planlagte:      │              │   │
│  │  │ • El -500       │  │ • +2.000/måned  │              │   │
│  │  └─────────────────┘  └─────────────────┘              │   │
│  │                                                         │   │
│  │  ┌─────────────────┐                                   │   │
│  │  │ OPSPARING       │  ← VIRTUEL (øremærket på Lønkonto)│   │
│  │  │ "Nødfond"       │                                   │   │
│  │  │ 10.000 kr       │  Budget ser kun 2.450 kr som fri  │   │
│  │  └─────────────────┘                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detaljerede koncepter

### 1. Regnskab (Ledger)

En samling af økonomi-data der kan deles mellem brugere.

**Eksempler:**
- "Min private økonomi" (kun mig)
- "Fælles husholdning" (delt med partner)
- "Sommerhus" (delt med familie)

**Indeholder:**
- Konti
- Kategorier (kan være regnskabs-specifikke)
- Transaktioner
- Planer (budgetter, opsparinger, lån)
- Regler for auto-kategorisering og matching

**UI-tekst:** "Opret nyt regnskab", "Mine regnskaber", etc.

### 2. Konto (Account)

En fysisk penge-lokation.

| Felt | Beskrivelse |
|------|-------------|
| navn | "Lønkonto", "Ferieopsparing", "Visa" |
| type | bank, kontant, kredit |
| valuta | DKK (default) |
| startsaldo | Saldo ved oprettelse |

**Relationer:**
- Tilhører ét Regnskab
- Kan bruges af flere Planer samtidig
- Transaktioner sker på én specifik konto

### 3. Transaktion (Transaction)

En faktisk pengebevægelse på en konto.

| Felt | Beskrivelse |
|------|-------------|
| dato | Hvornår skete det |
| beløb | Positivt = ind, negativt = ud |
| beskrivelse | Fra banken eller manuelt |
| konto | Hvilken konto (påkrævet) |
| kategori | Valgfrit, kan være flere (split) |
| status | ubehandlet, kategoriseret, ignoreret |

**Relationer:**
- Tilhører én Konto (fysisk faktum)
- Kan matches med én eller flere Planlagte Transaktioner (via regler)
- Kan splittes på flere Kategorier

**Split-kategorisering eksempel:**
```
Transaktion: -523 kr hos Føtex

Split:
├── 350 kr → Dagligvarer
├── 120 kr → Husholdning
└── 53 kr  → Vin & spiritus
```

**Fremtidig feature:** Kvitteringsscanning med OCR + LLM til automatisk split-forslag.

### 4. Planlagt Transaktion (Planned Transaction)

En forventet fremtidig (eller tilbagevendende) transaktion.

| Felt | Beskrivelse |
|------|-------------|
| navn | "Løn", "Husleje", "Netflix" |
| beløb_min | Minimum forventet (eller fast beløb) |
| beløb_max | Maximum forventet |
| type | indtægt, udgift, overførsel |
| kategori | Hvilken kategori |
| forventet_konto | Valgfrit - hvilken konto den forventes på |
| gentagelse | Se mønstre nedenfor |

**Relationer:**
- Tilhører én Plan
- Kan valgfrit angive forventet konto (eller lade regler håndtere det)
- Matches med faktiske transaktioner via regler

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

### 5. Plan

En samling af planlagte transaktioner med et formål.

**Fælles egenskaber:**
- Har et navn
- Kan tilknyttes én eller flere konti
- Indeholder planlagte transaktioner
- Bidrager til forecast

#### Budget
Løbende økonomi med indtægter og udgifter.

| Felt | Beskrivelse |
|------|-------------|
| tidsramme | Måned, år, custom |
| advarselsgrænse | Advar når saldo under X |

**Viser:** Forventet vs. faktisk, forecast fremad

#### Opsparing
Spare op til et mål.

| Felt | Beskrivelse |
|------|-------------|
| målbeløb | Valgfrit - hvor meget skal der spares |
| måldato | Valgfrit - hvornår skal målet nås |
| er_virtuel | Om pengene er øremærket på en anden konto |

**Virtuel opsparing:** Pengene står fysisk på f.eks. Lønkonto, men er "reserveret" til opsparingen. Budget ser kun den frie del af kontoen.

#### Lån
Afbetale gæld.

| Felt | Beskrivelse |
|------|-------------|
| restgæld | Hvor meget skyldes |
| ydelse | Månedlig betaling |
| rente | Årlig rente i % |

**Beregner:** Hvornår er lånet betalt af?

### 6. Kategori (Category)

Hierarkisk kategorisering af transaktioner.

```
Udgifter
  ├── Bolig
  │     ├── Husleje/lån
  │     ├── El
  │     ├── Vand
  │     └── Varme
  ├── Transport
  │     ├── Benzin
  │     ├── Offentlig transport
  │     └── Bil (værksted, forsikring)
  ├── Mad & drikke
  │     ├── Dagligvarer
  │     ├── Restaurant
  │     └── Vin & spiritus
  └── Underholdning
        ├── Streaming
        └── Spil

Indtægter
  ├── Løn
  ├── Feriepenge
  └── Andet
```

### 7. Regel (Rule)

Automatisk kategorisering og matching af transaktioner.

**Betingelser (conditions):**
- Beskrivelse indeholder "NETS *FØTEX"
- Beløb er mellem -1000 og -100
- Konto er "Visa"
- Dato er mellem d. 1-5 i måneden

**Handlinger (actions):**
- Sæt kategori til "Dagligvarer"
- Match med planlagt transaktion "Dagligvarer-budget"
- Split beløb: 80% Dagligvarer, 20% Husholdning

**Eksempel:**
```
Regel: "Husleje-match"
Betingelser:
  - Beskrivelse indeholder "Boligforening"
  - Beløb er mellem -8500 og -7500
  - Dato er mellem d. 1-3 i måneden
Handlinger:
  - Match med planlagt "Husleje"
  - Sæt kategori "Bolig > Husleje"
```

---

## Nøglerelationer

| Relation | Kardinalitet | Beskrivelse |
|----------|--------------|-------------|
| Regnskab → Konto | 1:N | Et regnskab har flere konti |
| Regnskab → Plan | 1:N | Et regnskab har flere planer |
| Plan → Konto | N:M | En plan kan bruge flere konti, en konto kan bruges af flere planer |
| Plan → Planlagt Transaktion | 1:N | En plan har flere planlagte transaktioner |
| Konto → Transaktion | 1:N | En konto har flere transaktioner |
| Transaktion → Planlagt Transaktion | N:M | En transaktion kan matche flere planlagte (og omvendt) |
| Transaktion → Kategori | N:M | En transaktion kan splittes på flere kategorier |

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
- Tager højde for virtuelle opsparinger
- Markér når planlagt ≠ faktisk
- Advarsler ved forventet underskud

### 3. Regnings-tjek
- "Er alle mine faste udgifter betalt denne måned?"
- Liste over planlagte udgifter med status:
  - ✓ Betalt (matched)
  - ⏳ Afventer (dato ikke nået)
  - ⚠️ Forsinket (dato passeret, ikke matched)
  - ❌ Mangler (betydeligt forsinket)

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
4. **Planer** - Budgetter, opsparing, lån
5. **Indstillinger** - Konti, kategorier, regler, brugere

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
