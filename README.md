# ashvin-doc-classifier

Classifies DME medical PDF documents into six types using OpenAI GPT-4o-mini, with per-patient completeness checking.

## Document Types

- Prescription
- Sleep Study Report
- Physician Notes
- Compliance Report
- Order
- Delivery Ticket

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

## Usage

```bash
python -m src.classify --input documents/ --output output/
```

## Output

| File | Contents |
|------|----------|
| `output/classifications.json` | Per-document type and confidence |
| `output/completeness.json` | Per-patient missing document types |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/adr/](docs/adr/) for design decisions.

## Tests

```bash
pytest
```
