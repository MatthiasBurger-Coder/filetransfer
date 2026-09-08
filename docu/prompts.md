
Ja. Für **2 Mio. LOC** würde ich den 250k-Kontext von Qwen **nicht als Speicher für das Repository**, sondern als großen **Working-Set-Cache** benutzen.

Die passende Architektur für deinen RAG-Skill sieht ungefähr so aus:

```text
                    2 Mio LOC Repository
                           │
                           ▼
                 ┌──────────────────┐
                 │ Repository Index │
                 │──────────────────│
                 │ AST / Symbols    │
                 │ Imports          │
                 │ Calls            │
                 │ Inheritance      │
                 │ DB/API/Events    │
                 │ Tests            │
                 │ Git History      │
                 └────────┬─────────┘
                          │
             ┌────────────┴─────────────┐
             ▼                          ▼
      Vector Retrieval            Code Graph
      "semantic meaning"          "structural truth"
             │                          │
             └────────────┬─────────────┘
                          ▼
                 Candidate Resolver
                    500–2000 Chunks
                          │
                          ▼
                       Rerank
                       20–80
                          │
                          ▼
              Context / Evidence Builder
                  ~30k–120k Tokens
                          │
                          ▼
                      Qwen 3.8
                    max ~250k
                          │
                   tool requests
                          │
                 ┌────────┴─────────┐
                 ▼                  ▼
             fetch_symbol       expand_graph
             fetch_file         search_code
             callers_of         implementations
             tests_for          git_history
```

Das ist der entscheidende Unterschied zu einem klassischen RAG.

### 1. Das Repository wird **symbolisch**, nicht nur in Chunks zerlegt

Bei Sourcecode würde ich **niemals einfach 500-Zeilen-Chunks embedden**.

Stattdessen bekommt jedes Codeobjekt eine eigene Identität:

```text
Repository
 └─ Module
     └─ Package
         └─ File
             └─ Class
                 ├─ Method
                 ├─ Field
                 └─ InnerClass
```

Beispiel:

```json
{
  "symbol": "OrderService.createOrder",
  "type": "method",
  "file": "order/OrderService.java",
  "lines": [117, 184],

  "calls": [
    "OrderRepository.save",
    "PaymentService.authorize"
  ],

  "called_by": [
    "OrderController.create",
    "OrderImportJob.process"
  ],

  "implements": null,

  "references": [
    "Order",
    "Payment",
    "Customer"
  ]
}
```

Damit musst du bei einer Anfrage nicht überlegen:

> Welche 400 Text-Chunks könnten ähnlich klingen?

sondern:

> Welche Code-Subgraphen sind für diese Frage relevant?

Das ist für große Softwareprojekte erheblich mächtiger.

---

## 2. Drei Ebenen von Wissen speichern

Ich würde für deinen Skill drei Repräsentationen erzeugen.

```text
L0 – Repository Map
L1 – Architecture / Component Summaries
L2 – Real Source Code
```

### L0 – Repo Map

Vielleicht nur **5–20k Tokens** für ein gigantisches Projekt.

Beispiel:

```yaml
repository:
  name: legacy-platform

domains:
  - billing
  - customer
  - provisioning
  - authentication

modules:

  billing-service:
    responsibility:
      - invoice creation
      - payment booking
      - dunning

    entrypoints:
      - InvoiceController
      - PaymentConsumer

    dependencies:
      - customer-core
      - postgres
      - rabbitmq

    important_symbols:
      - InvoiceService
      - BookingEngine
      - PaymentProcessor
```

Qwen bekommt diese **Landkarte fast immer**.

---

## 3. L1: Zusammenfassungen als hierarchischer Index

Beispielsweise:

```text
repository-summary
    ↓
module-summary
    ↓
package-summary
    ↓
class-summary
    ↓
method-summary
    ↓
source
```

Für:

```java
public PaymentResult executePayment(...)
```

speicherst du neben dem Code:

```yaml
symbol: PaymentService.executePayment

purpose:
  Executes a customer payment transaction.

inputs:
  - CustomerId
  - PaymentRequest

side_effects:
  - writes PaymentEntity
  - publishes PaymentCompleted

dependencies:
  - PaymentRepository
  - PaymentGateway
  - EventPublisher

throws:
  - PaymentRejectedException

business_rules:
  - inactive customers cannot execute payments
  - payment limit is checked before gateway invocation
```

Diese Darstellung braucht vielleicht **150 Tokens statt 2.000 Tokens Sourcecode**.

Damit kann dein Retriever erst einmal extrem günstig arbeiten.

---

# 4. Erst ganz zum Schluss wird Sourcecode geladen

Angenommen du fragst:

> Warum kann ein stornierter Auftrag trotzdem eine Rechnung erzeugen?

Der Retriever findet vielleicht:

```text
OrderCancelService
InvoiceGenerationJob
InvoiceService.createInvoice
OrderStatusChangedConsumer
BillingRepository
```

Jetzt kommt Graph Expansion:

```text
InvoiceGenerationJob
        ↓ calls
InvoiceService.createInvoice
        ↓ reads
Order.status

OrderCancelService
        ↓ writes
Order.status

OrderStatusChangedConsumer
        ↓ triggers
InvoiceGenerationJob
```

Dann werden **nur diese Klassen vollständig geladen**.

Vielleicht:

```text
Repo Map                 8k
Architecture summary    10k
Relevant summaries      15k
Actual source code      45k
Tests                   20k
Git/Issue evidence       5k
Prompt/history          10k
--------------------------------
                       113k Tokens
```

Obwohl dahinter **2 Mio LOC** stehen.

---

# 5. Die 250k würde ich sogar absichtlich NICHT ausreizen

Das ist wichtig.

Nur weil ein Modell 250/256k Tokens kann, heißt das nicht:

```text
250k = besser
```

Bei Qwen3-Coder nennt Qwen offiziell 256k native context und bis zu 1M via Extrapolation; auch die neueren Qwen-Linien haben sehr große Kontextfenster. ([Qwen][1])

Ein praktischer Test mit Qwen3.8-27B zeigt zudem sehr schön das Problem: 230k Kontext funktionierte zwar, war dort aber ungefähr **zehnmal langsamer** als ein 50k-Kontextlauf. ([Syntalith][2])

Ich würde daher beispielsweise definieren:

```yaml
context_budget:

  target: 80000
  soft_limit: 120000
  hard_limit: 220000

  reserve:
    reasoning: 30000
    output: 10000
```

250k sind dann dein **Notfall-/Deep-Analysis-Fenster**, nicht der Normalbetrieb.

---

# 6. Und jetzt kommt der wichtige Teil für deinen RAG Skill

Gib Qwen selbst **Retrieval-Tools**.

Nicht:

```text
User
 ↓
RAG
 ↓
250k Prompt
 ↓
Qwen
```

sondern:

```text
User
  ↓
Qwen
  ↓
"I need to inspect PaymentService"
  ↓
RAG Skill
  ↓
fetch_symbol(PaymentService)
  ↓
Qwen
  ↓
"I need callers of executePayment"
  ↓
RAG Skill
  ↓
callers_of(PaymentService.executePayment)
  ↓
Qwen
  ↓
"I need PaymentCompleted consumers"
  ↓
RAG Skill
  ↓
event_consumers(PaymentCompleted)
  ↓
...
```

Das Modell **navigiert durch das Repository**.

Genau das macht 2 Mio LOC beherrschbar.

---

# 7. Dein Skill könnte etwa diese Tools anbieten

```text
repo.overview()

symbol.search(query)

symbol.get(id)

symbol.callers(id)

symbol.callees(id)

symbol.references(id)

type.implementations(id)

dependency.path(a, b)

module.dependencies(module)

event.producers(event)

event.consumers(event)

database.readers(table)

database.writers(table)

tests.for_symbol(id)

code.search(pattern)

git.history(symbol)

context.expand(symbol, depth=2)
```

Das ist bereits wesentlich mehr als normales Vector-RAG.

---

# 8. Besonders wichtig: `context.expand()`

Das würde ich als Kernoperation bauen.

Zum Beispiel:

```text
context.expand(
    symbol="InvoiceService.createInvoice",
    depth=2,
    edges=[
        "calls",
        "called_by",
        "reads",
        "writes",
        "events"
    ],
    budget_tokens=30000
)
```

Der Skill entscheidet dann:

```text
30k Token Budget
       │
       ├── InvoiceService                5k
       ├── InvoiceRepository             3k
       ├── InvoiceGenerationJob          4k
       ├── OrderService                  5k
       ├── OrderStatusChangedConsumer    3k
       ├── relevant DTOs                 2k
       └── tests                         8k
```

Und stoppt automatisch, wenn das Budget erreicht ist.

---

# 9. Für riesige Analysen brauchst du noch eine zweite Technik

Angenommen:

> Finde alle Architekturverletzungen in meinen 2 Mio LOC.

Das kannst du nicht sinnvoll über einen einzelnen Retrieval-Vorgang lösen.

Dann:

```text
                    Repository
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           Domain A    Domain B    Domain C
             │           │           │
          analyse      analyse     analyse
             │           │           │
             ▼           ▼           ▼
          findings     findings    findings
             └───────────┼───────────┘
                         ▼
                    Evidence DB
                         │
                         ▼
                  Global synthesis
                         │
                         ▼
                       Qwen
```

Also **Map → Evidence → Reduce**.

Einzelne Qwen-Aufrufe analysieren jeweils kleine Bereiche.

Am Ende bekommt der Synthese-Aufruf beispielsweise:

```text
82 architectural findings
37 dependency violations
11 cyclic dependencies
16 duplicated domain concepts
23 transaction boundary problems
```

plus die entscheidenden Beweisstellen.

Nicht 2 Mio LOC.

---

# 10. Das passt ziemlich exakt zu deinem Cognitive-Gateway-Ansatz

Eigentlich solltest du nicht bauen:

```text
CG → Vector DB → Qwen
```

sondern:

```text
                         Cognitive Gateway
                                │
            ┌───────────────────┼────────────────────┐
            │                   │                    │
       Semantic Index       Code Graph         Evidence Store
            │                   │                    │
            └───────────────────┼────────────────────┘
                                │
                         Context Planner
                                │
                         token budget
                                │
                                ▼
                            RAG Skill
                                │
                                ▼
                             Qwen 3.8
                                │
                          tool requests
                                │
                                └──────────────┐
                                               │
                               iterative retrieval
```

Und **der Context Planner deines Cognitive Gateways entscheidet**, was Qwen überhaupt sehen darf.

Damit bekommst du einen sehr interessanten Effekt:

> **Die Modellgröße wird weniger wichtig, weil dein Gateway das Repositoryverständnis übernimmt.**

Qwen muss nicht 2 Mio LOC „wissen“.

Es muss nur gut genug sein, um:

1. eine Frage zu zerlegen,
2. relevante Evidenz anzufordern,
3. Abhängigkeiten zu verfolgen,
4. Widersprüche zu erkennen,
5. aus 30–100k Tokens sauber zu reasoning.

### Zielgröße

Bei **2 Mio LOC** würde ich ungefähr auf Folgendes zielen:

```text
2,000,000 LOC
       ↓
~100,000–300,000 Symbols
       ↓
Code Knowledge Graph
       ↓
10k–50k candidate symbols
       ↓
100–500 semantic candidates
       ↓
20–80 graph-expanded symbols
       ↓
30k–120k Tokens
       ↓
Qwen 3.8
```

Das bedeutet ungefähr:

**2 Mio LOC → vielleicht 0,5–2 % des Codes pro Reasoning-Schritt.**

Und trotzdem kann das System über mehrere Tool-Schritte das **gesamte Repository untersuchen**.

Das ist meiner Ansicht nach auch der Punkt, an dem dein RAG im Cognitive Gateway von einem normalen „Vector-DB-RAG“ zu einer echten **Repository Reasoning Engine** wird. Für deine geplante Legacy-Reengineering-/Migrationsanalyse wäre genau diese Kombination aus **AST + Code Graph + Semantic Retrieval + Evidence Store + token-budgetiertem Context Planner** die passende Architektur.

[1]: https://qwenlm.github.io/blog/qwen3-coder/?utm_source=chatgpt.com "Qwen3-Coder: Agentic Coding in the World | Qwen"
[2]: https://syntalith.ai/en/blog/qwen-context-60k-120k-150k-250k?utm_source=chatgpt.com "Qwen3.8 context: 60k, 120k, 150k, 250k | Syntalith"
