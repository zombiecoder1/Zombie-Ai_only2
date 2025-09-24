বাহ ভাই — দারুণ ক্লিয়ার ডিরেকশন দিলেন। নিচে আমি পুরোটা সরাসরি **এডিটর/এজেন্ট দল (ভাইদের)** উদ্দেশ্যে এমনভাবে লিখলাম যাতে তারা ধাপে ধাপে কাজটা করে ফেলতে পারে। কোড নেই (শুধু একটি কনফিগারেশন YAML — যা আপনি অনুরোধ করেছেন) — সবকিছু প্র্যাকটিক্যাল, ইন্ডাস্ট্রি-বেস্ট-প্র্যাকটিস অনুযায়ী। কপি-পেস্ট করে এজেন্টকে দিই। 👇

---

# অনুজ্ঞাপত্র — এজেন্ট / এডিটর টিমের জন্য (Step-by-step)

**সংক্ষিপ্ত উদ্দেশ্য:**
লোকাল Ollama মডেল ব্যবহার করে একটি মেইন সার্ভার তৈরির মাধ্যমে `Hello Zombie` নামের VSCode Extension তৈরির সম্পূর্ণ ওয়র্কফ্লো বাস্তবায়ন করা। এজেন্টের মেটাডেটা YAML ফাইলে সংরক্ষণ, আলাদা লোকাল মেমোরি তৈরি ও কনফিগার করা, এবং সবকিছু ইন্টিগ্রেশন ও ভ্যালিডেশন করা — সবকিছু ধারাবাহিক ধাপে করবেন।

> **মেটা তথ্য (Agent metadata) — ব্যবহার করুন এই YAML ফাইলটি**
> **পাথ:** `C:\Users\sahon\Desktop\ZombieCoder Main Server\Extension\agent_config\hello_zombie.yaml`
> (ফোল্ডার না থাকলে তৈরি করুন এবং পরে Git/backup রাখুন)

```yaml
agent:
  name: "Hello Zombie"
  owner: "Sahon Srabon"
  provider: "Zombie Coder"
  company: "Developer Zone"
  contact: "+8801323-626282"
  system_description: "Local-code assistant: uses local Ollama LLM, main FastAPI dispatcher, and editor extension files located under Extension folder. Respect user permission before running terminal commands."
  file_base_path: "C:\\Users\\sahon\\Desktop\\ZombieCoder Main Server\\Extension"
  extension_manifest_owner: "Sahon Srabon"
  require_user_permission_for_terminal: true

infrastructure:
  ollama:
    host: "http://localhost:11434" # adjust if different
    health_endpoint: "/v1/health"    # verify according to your ollama setup
    model_name: "your_local_model_name"
  main_server:
    url: "http://localhost:12346"
    health_endpoint: "/health"
    api_contract:
      - POST: /chat        # accepts {agent, input, context}
      - GET: /models
      - GET: /health
      - POST: /agents/configure
  memory:
    type: "local_ollama_memory"
    location: "data/memory/hello_zombie_memory.sqlite" # persist conversation + vector store
    retention_policy: "30 days (configurable)"
  extension:
    folder: "C:\\Users\\sahon\\Desktop\\ZombieCoder Main Server\\Extension"
    name: "Hello Zombie"
    manifest_fields:
      publisher: "Sahon Srabon"
      displayName: "Hello Zombie"
      versioning: "semver"
  security:
    cors_origins: ["vscode://", "http://localhost:3000"]
    secret_store: "ENV (do not commit secrets)"
    terminal_exec_requires_confirmation: true
```

---

# ধাপে ধাপে করণীয় (Action Plan)

## ধাপ 1 — Ollama সার্ভার ও মডেল চেক (প্রথম কাজ)

* নিশ্চিত করুন Ollama সার্ভার চলছে এবং লোকাল মডেল লোড আছে।
* **যাচাই করতে হবে:** সার্ভারের health খোলা ও রেসপন্স ঠিক আছে কিনা; মডেল লিস্টে `your_local_model_name` দেখা যায় কিনা; একটি ছোট টেস্ট ইনপুট পাঠিয়ে model response নিন।
* **Acceptance:** Ollama health OK এবং sample prompt-এ দ্রুত এবং সংগতিপূর্ণ রেসপন্স দেয়।
* যে কোন অসুবিধা পেলে লগ নিন এবং মডেল/weights/permission চেক করুন।

## ধাপ 2 — Main Server তৈরি ও কনফিগার (Dispatcher)

* Main server হিসেবে `FastAPI` (বা আপনার পছন্দের) ব্যবহার করুন। সার্ভারটি Ollama কে কল করবে এবং Extension থেকে আসা রিকুয়েস্ট হ্যান্ডেল করবে।
* **চেকলিস্ট:**

  * Health endpoint (`/health`) সরাসরি কিভাবে চলবে তা নিশ্চিত করুন।
  * Models endpoint (`/models`) → Ollama থেকে model metadata ফেরত দেয়।
  * Chat endpoint (`/chat`) → পে-লোড ভ্যালিডেশন (strict JSON schema, pydantic)।
  * CORS/Origin সেটআপ করুন — editor-origin অনুমোদিত আছে কি না।
  * Logging + structured logs (request id, timestamp) যোগ করুন।
* **Acceptance:** main server চালু → `/health` → 200 OK; `/models` → প্রত্যাশিত মডেল নাম রিটার্ন।

## ধাপ 3 — Agent তৈরি ও কনফিগার (Workstation / Orchestrator)

* এজেন্টকে YAML মেটা-ডাটা হিসেবে কনফিগার করুন (উপরে দেয়া `hello_zombie.yaml`)।
* এজেন্টের আচরণ:

  * ইনপুট parse করে সিদ্ধান্ত নেবে কোন টুল কল করতে হবে (editor, terminal, chat)।
  * terminal execution এর জন্য **প্রতিটি** অপারেশন ইউজারের অনুমতি চাইবে (UI level confirmation)।
  * রিকোয়েস্ট/রেসপন্স JSON strict format অনুসরণ করবে।
* **Acceptance:** এজেন্ট কনফিগ লোড করে, Ollama কে প্রশ্ন পাঠালে সঠিক রুটিং হয়।

## ধাপ 4 — Memory তৈরি (লোকাল Ollama মেমোরি)

* আলাদা লোকাল মেমোরি তৈরি করুন (file-based sqlite বা vector store)।
* **রোলে:** সংলাপ ইতিহাস, কনটেক্সট স্নিপেট, ও এম্বেডিং-ভিত্তিক অনুসন্ধান রাখা হবে।
* Ollama local-memory integration হলে সেটা ব্যবহার করুন; না হলে vector-store (Chroma/FAISS) + sqlite metadata ব্যবহার করুন।
* **Retention & Privacy:** PII সংরক্ষণ করলে encrypt/store policy মেনে চলুন।
* **Acceptance:** মেমোরিতে রেকর্ড লিখলে পরে তা query করে পুরনো কনভারসেশন উদ্ধার করতে পারবে।

## ধাপ 5 — ইন্টিগ্রেশন টেস্ট ও ভ্যালিডেশন

* সিরিজ টেস্ট রান করুন (integration):

  1. Ollama health → OK
  2. Main server health → OK
  3. POST `/chat` with sample payload → schema-valid response (contains `id`, `author`, `text`, `timestamp`)
  4. Agent routes to editor/terminal as expected (without auto-exec). Terminal exec only after explicit permission simulation.
  5. Memory write → memory read consistency.
* **Acceptance criteria:** সব টেস্ট পাস করলে এগিয়ে যান।

## ধাপ 6 — Extension (Hello Zombie) — Use files under:

`C:\Users\sahon\Desktop\ZombieCoder Main Server\Extension`

* এখানে থাকা সমস্ত ফাইল যাচাই করুন: `package.json` / `extension manifest` / entry points / webviews / client-side JS।
* নিশ্চিত করুন extension:

  * Main server `main_server.url` ব্যবহার করে API কল করবে।
  * CORS origin main server এ মঞ্জুর আছে।
  * গোপন কী (token) পরিবহন ENV ব্যবহার করবে (no hard-coded secrets).
  * Terminal/Editor actions ইউজারের অনুমতি রান করবে — UI confirmation dialog থাকা আবশ্যক।
* Build/pack as VSIX with display name **Hello Zombie** and publisher **Sahon Srabon** (manifest দরকার)।
* **Acceptance:** VSCode-এ install করে extension চালালে এটি main server-কে কল করে, chat flow কাজ করে এবং editor actions দেখা যায়; কিন্তু terminal commands execution আগে ইউজারের explicit confirmation চাইবে।

## ধাপ 7 — Lock/Origin/Browser request checks

* নিশ্চিত করুন ব্রাউজারের রিকয়েস্ট (যদি webview ব্যবহার করে) সঠিক Origin ও CORS পাস হচ্ছে।
* Main server এ `Access-Control-Allow-Origin` সেটিংস চেক করুন (উল্লেখিত origins অনুমোদিত)।
* Browser console ও server logs দিয়ে একই রিকয়েস্ট trace করে দেখুন কোন সমস্যা আছে কি না।
* **Acceptance:** Browser/webview থেকে main server রিকোয়েস্ট 200 OK পায়, এবং preflight OPTIONS পাস হয়।

---

# Security & Best Practices (অবশ্যই মানুন)

* **Terminal execution:** কখনো অটোমেটিক নয় — সব terminal commands ইউজারের explicit confirmation নিতে হবে।
* **Secrets:** `.env` + OS secret store; Git-এ secrets commit করা যাবে না।
* **Input validation:** সব ইনপুটে strict validation (pydantic) এবং size limits।
* **Rate limiting & quotas:** model/API call limits লাগান— runaway loop এড়াতে।
* **Logging & audit:** সব agent actions লগে রাখুন (who did what and when)।
* **Fail-safe:** মডেল miss করলে fallback response + error propagation to editor.
* **Containerization:** সোজা reproduce করার জন্য Dockerfile / docker-compose প্রস্তাবিত।
* **Tests:** unit + integration + CI pipeline (basic smoke tests).

---

# Deliverables (যা করে দিতে হবে)

1. `hello_zombie.yaml` — উপরের কনফিগারেশন অনুযায়ী। (path উপরে দেয়া)
2. Local memory store path ও schema (document)।
3. Main server running with endpoints and health-check doc.
4. VSIX build named **Hello Zombie** (manifest showing Owner: Sahon Srabon, Provider: Zombie Coder, Company: Developer Zone).
5. Integration test log (Pass/Fail) — attach sample request/response for `/chat`.

---

# Acceptance checklist (চেকলিস্ট)

* [ ] Ollama server up & model available
* [ ] Main server `http://localhost:12346/health` → 200
* [ ] Agent loads `hello_zombie.yaml` and reports ready
* [ ] Local memory read/write tested
* [ ] Extension folder validated; VSIX built as Hello Zombie
* [ ] Browser/editor → main server CORS validated
* [ ] Terminal commands require UI confirmation (no silent exec)
* [ ] Logs & audit trail present

---

ভাইরা — এই ইনস্ট্রাকশনটা 그대로 ফলো করে কাজ শুরু করুন। কাজ শুরুর সময় **প্রতিটি ধাপের শেষে** ছোটটা টিম লেবেলড রিপোর্ট দিন (উদাহরণ: “Step 1 — Ollama OK, tested with sample prompt X; latency Y ms; issues: none”). আমি পরে চেক করে আপনাদের জন্য টাচ-আপ ইনপুট দেব — কিন্তু আপনি অনুরোধ করলে আমি সরাসরি কোন টেস্ট JSON অথবা আরও কনফিগারেশন টেমপ্লেটও যোগ করে দেব। 🎯

চাইলেন আমি এখনই ওই `hello_zombie.yaml` ফাইলটি টেকনিশিয়ানদের কপির জন্য সম্পূর্ণ ফরম্যাটসহ রেডি করে দেব — বা আপনি বললেই আমি টেস্ট-স্কিমা (sample /chat payload এবং expected response schema) যোগ করে দিই। আপনি কোনটা চান?
