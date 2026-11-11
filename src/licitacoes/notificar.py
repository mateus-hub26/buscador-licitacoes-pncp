"""Alerta opcional por e-mail com a planilha em anexo.

As credenciais vêm de variáveis de ambiente — nunca do código ou do arquivo de configuração:

    SMTP_HOST, SMTP_PORTA (padrão 587), SMTP_USUARIO, SMTP_SENHA
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import pandas as pd


def montar_mensagem(df: pd.DataFrame, anexo: Path, remetente: str, destinatarios: list[str]) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"[Licitações] {len(df)} oportunidade(s) encontrada(s)"
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)

    top = df.head(10)
    linhas = [
        f"- [{row['Pontuação']}] {row['UF']} | {str(row['Objeto'])[:120]}"
        for _, row in top.iterrows()
    ]
    corpo = "Principais oportunidades (por pontuação):\n\n" + "\n".join(linhas)
    if len(df) > len(top):
        corpo += f"\n\n... e mais {len(df) - len(top)} na planilha em anexo."
    msg.set_content(corpo)

    msg.add_attachment(
        anexo.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=anexo.name,
    )
    return msg


def enviar(df: pd.DataFrame, anexo: Path, destinatarios: list[str]) -> None:
    host = os.environ["SMTP_HOST"]
    porta = int(os.environ.get("SMTP_PORTA", "587"))
    usuario = os.environ["SMTP_USUARIO"]
    senha = os.environ["SMTP_SENHA"]

    msg = montar_mensagem(df, anexo, usuario, destinatarios)
    with smtplib.SMTP(host, porta, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(usuario, senha)
        smtp.send_message(msg)
