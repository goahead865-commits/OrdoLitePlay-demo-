# OrdoLitePlay — Interactive Demo

An interactive demo of an order, inventory, purchasing, delivery, and accounts workflow application.

## Demo access

- Live app: https://6htsn6nzvucywh6rkadkur.streamlit.app/
- Username: `demo_admin`
- Password: `demo_admin`

This is a portfolio demonstration environment. All data is fictional; please do not enter personal, confidential, or production information.

## Run locally

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
2. Add the MySQL connection details to the copied file.
3. Install dependencies and run from the repository root:

   ```powershell
   python -m pip install -r page/requirements.txt
   python -m streamlit run page/home.py
   ```

Database credentials are never committed. Configure them through Streamlit Community Cloud's **Settings → Secrets** when deploying.
