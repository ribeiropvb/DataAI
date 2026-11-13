"""Leitura de planilhas com pandas, para validar e pré-visualizar."""

import csv
import io
from pathlib import Path

import pandas as pd

EXTENSOES = {'.csv', '.xlsx', '.xls'}
LINHAS_AMOSTRA = 10


class ArquivoIlegivel(Exception):
    pass


def _texto(valor):
    try:
        if pd.isna(valor):
            return ''
    except (TypeError, ValueError):
        pass
    if isinstance(valor, pd.Timestamp):
        formato = '%d/%m/%Y %H:%M' if (valor.hour or valor.minute) else '%d/%m/%Y'
        return valor.strftime(formato)
    return str(valor)


def _descrever(nome, df):
    return {
        'nome': nome,
        'linhas': int(len(df)),
        'colunas': [str(c) for c in df.columns],
        'amostra': [[_texto(v) for v in linha] for linha in df.head(LINHAS_AMOSTRA).itertuples(index=False)],
    }


def _ler_csv(conteudo):
    for codificacao in ('utf-8-sig', 'latin-1'):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    try:
        separador = csv.Sniffer().sniff(texto[:20000], delimiters=',;\t|').delimiter
    except csv.Error:
        separador = ','
    return pd.read_csv(io.StringIO(texto), sep=separador, dtype=str, keep_default_na=False)


def resumir(arquivo_enviado):
    """Abre o arquivo e devolve abas, colunas, total de linhas e amostra.

    Levanta ArquivoIlegivel se o pandas não conseguir ler.
    """
    extensao = Path(arquivo_enviado.name).suffix.lower()
    arquivo_enviado.seek(0)
    conteudo = arquivo_enviado.read()
    arquivo_enviado.seek(0)
    try:
        if extensao == '.csv':
            df = _ler_csv(conteudo)
            abas = [_descrever('CSV', df)]
        else:
            motor = 'openpyxl' if extensao == '.xlsx' else 'xlrd'
            planilhas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, engine=motor)
            abas = [_descrever(str(nome), df) for nome, df in planilhas.items()]
    except Exception as erro:  # qualquer falha do pandas vira mensagem para a pessoa
        raise ArquivoIlegivel(str(erro)) from erro
    if not abas or all(not aba['colunas'] for aba in abas):
        raise ArquivoIlegivel('o arquivo está vazio')
    return {'abas': abas}
