# Matchline ATS

A FastAPI landing page and resume analysis input flow for an applicant tracking system concept.

## Run locally

```powershell
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

## n8n integration

Import `n8n/matchline-resume-analysis.json` into n8n. The workflow receives:

- `POST /webhook/ats-resume-analysis`
- multipart field `analysis_id`
- multipart field `job_description`
- multipart file field `resume`

Set these n8n environment variables before activating the workflow:

- `OPENAI_API_KEY`: API key used by the analysis request
- `ATS_BACKEND_URL`: public base URL for this FastAPI app, for example `https://ats.example.com`

The workflow extracts the PDF text, asks the model for structured ATS findings, then posts the result to:
`POST /api/analyses/{analysis_id}/result`.

## API contracts

`POST /api/analyses` accepts multipart form data with `job_description` and a PDF `resume`. It returns `202` with an `analysis_id` and `status_url`.

`GET /api/analyses/{analysis_id}` returns `queued`, `processing`, `completed`, or `failed`, plus the completed result when available.

`GET /api/analyses` returns the current account's complete analysis history. The browser account page is available at `/account`, and completed records link back to their result dashboard.

`POST /api/analyses/{analysis_id}/result` is the n8n callback. Its JSON body is:

```json
{
	"analysis_id": "uuid",
	"status": "completed",
	"result": {
		"score": 87,
		"verdict": "Strong fit",
		"summary": "...",
		"strengths": ["..."],
		"gaps": ["..."],
		"recommendations": ["..."],
		"matched_keywords": ["..."],
		"missing_keywords": ["..."]
	}
}
```

Analysis metadata and completed results are stored in the local SQLite database `matchline.db`. Resume binaries are sent to n8n for processing and are not stored locally.
