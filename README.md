# Matchline ATS

A FastAPI landing page and analysis input flow for an applicant tracking system concept.

## Run locally

```powershell
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

The `POST /analyze` handler currently acknowledges the submitted inputs. The scoring and recommendation API can be connected there later.
