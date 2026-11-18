# Law Corpus: Source, Schema and Ingestion Guide

This directory holds legislative text files for the Indian legal corpus used by Verdict's RAG knowledge base.

## 1. Legal Basis and Licensing

Under **Section 52(1)(q) of the Indian Copyright Act, 1957**, the reproduction or publication of:
- Any Act of the Legislature (Parliament of India or State Legislatures),
- Any judgment or order of a court, tribunal or other judicial authority,
- Any official Gazette notification,

does not constitute an infringement of copyright. All legislative texts placed in this directory are public domain government works.

Official sources:
- India Code: https://www.indiacode.nic.in
- The Gazette of India: https://egazette.gov.in
- Legislative Department, Ministry of Law and Justice: https://legislative.gov.in

## 2. File Format

Act files may be provided either as plain text files (`.txt` / `.md`) or structured JSON (`.json`).

### Structured JSON Schema (`<act>.json`)

```json
{
  "act": "BNS",
  "domain": "statute",
  "license": "Public Domain / Government Work under Section 52(1)(q) Indian Copyright Act, 1957",
  "source": "The Gazette of India Extraordinary, Act No. 45 of 2023",
  "sections": [
    {
      "section_no": "103",
      "title": "Punishment for murder",
      "body": "(1) Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine...",
      "ipc_equivalent": "IPC 302",
      "audience": ["judge", "lawyer"],
      "valid_from": "2024-07-01"
    }
  ]
}
```

## 3. Ingestion Command

To validate and preview an act:
```bash
python scripts/ingest_law.py --file data/law_corpus/sample_corpus.json --dry-run
```

To ingest into PostgreSQL:
```bash
python scripts/ingest_law.py --file data/law_corpus/sample_corpus.json
```

