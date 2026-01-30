# Research World (Standalone, No Clove)

This demo runs fully on your PC without Clove. It uses a local multi‑agent pipeline and direct Gemini API calls.

## 1) Prerequisites

- Python 3.10+
- API key(s): `GEMINI_API_KEY` or `GOOGLE_API_KEY` (single key)  
  Or a pool via `GOOGLE_API_KEY_1` … `GOOGLE_API_KEY_10`.

## 2) Setup

```bash
cd /home/anixd/Documents/CLOVE/demo/without_clove/research_world
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Configure API keys

Option A — environment:
```bash
export GOOGLE_API_KEY="your_key"
# Or a pool:
export GOOGLE_API_KEY_1="key1"
export GOOGLE_API_KEY_2="key2"
```

Option B — `.env` file in this directory:
```env
GOOGLE_API_KEY_1=your_key_1
GOOGLE_API_KEY_2=your_key_2
```

## 4) Prepare a dataset

### Fastest (built‑in sample data)
```bash
python download_papers.py
```
This creates `.txt` files under `data/pdfs/` and is enough to run the demo.

### Add your own PDFs or text
```bash
cp /path/to/paper.pdf data/pdfs/
cp /path/to/notes.txt data/pdfs/
```

### Download open access papers (manual)
Below are official sources. Download PDFs and place them in `data/pdfs/`.

PubMed Central OA (biomed):
```
https://pmc.ncbi.nlm.nih.gov/tools/ftp/
https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/
```

PMC OA Web Service (search + download):
```
https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi
```

arXiv bulk access:
```
https://www.lib.ncsu.edu/text-and-data-mining/arxiv-bulk-data-access
```

## 5) Run the demo

```bash
python main.py "What are the best treatments for Type 2 Diabetes?"
```

Shorter run:
```bash
python main.py "Compare SGLT2 inhibitors vs GLP-1 agonists" --hours 0.5
```

Create sample docs and run:
```bash
python main.py --create-samples
python main.py "Summarize the dataset"
```

## 6) Checkpoints and resume

List checkpoints:
```bash
python main.py --list-checkpoints
```

Resume from last checkpoint:
```bash
python main.py --resume
```

## 7) Outputs

- Reports: `reports/`
- Checkpoints: `checkpoints/`
- Logs: `logs/`

## Notes

- This demo intentionally runs **without** Clove to show baseline behavior.
- For large datasets, add more PDFs/texts to `data/pdfs/` and increase `--hours`.
