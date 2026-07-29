import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_client():
    """Autentica na API do Google Sheets utilizando a variável GOOGLE_CREDENTIALS_JSON."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if not creds_json:
        logging.warning("GOOGLE_CREDENTIALS_JSON não configurado nas Variáveis de Ambiente.")
        return None

    try:
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        logging.error(f"Erro na autenticação do Google Sheets: {e}")
        return None

def get_spreadsheet():
    """Abre a folha de cálculo principal pelo ID."""
    client = get_google_client()
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID")
    
    if not client or not sheet_id:
        return None

    try:
        return client.open_by_key(sheet_id)
    except Exception as e:
        logging.error(f"Erro ao abrir a folha de cálculo: {e}")
        return None

def get_sheet(sheet_name="Produtos"):
    """Retorna uma aba/worksheet específica da folha de cálculo."""
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        raise ValueError("Não foi possível conectar ao Google Sheets.")
    return spreadsheet.worksheet(sheet_name)

def sheet_to_dict(sheet):
    """Converte os registos da folha de cálculo numa lista de dicionários."""
    try:
        return sheet.get_all_records()
    except Exception as e:
        logging.error(f"Erro ao ler registos da folha: {e}")
        return []
