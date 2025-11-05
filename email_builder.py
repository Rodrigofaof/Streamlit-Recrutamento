from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib

BANDEIRAS = {
    "BR": "🇧🇷", "MX": "🇲🇽", "CL": "🇨🇱", "AR": "🇦🇷", "CO": "🇨🇴", "PE": "🇵🇪",
    "EC": "🇪🇨", "GT": "🇬🇹", "NI": "🇳🇮", "SV": "🇸🇻", "VE": "🇻🇪", "BO": "🇧🇴",
    "PA": "🇵🇦", "PY": "🇵🇾", "UY": "🇺🇾", "DO": "🇩🇴", "CR": "🇨🇷", "HN": "🇭🇳", "PR": "🇵🇷"
}


def sort_with_nacional_first(df):
    df = df.copy()
    df["region_priority"] = df["region"].astype(str).str.lower().apply(
        lambda x: 0 if "nacional" in x or "national" in x else 1
    )
    df = df.sort_values(["region_priority", "region", "AgeGroup", "Gender"], ascending=[True, True, True, True])
    return df.drop(columns=["region_priority"])


def build_email_html(FinalMatch_display, NoMatch, requests_by_country):
    total_completes = FinalMatch_display["Completes"].sum()
    total_recruits = int(requests_by_country["Requests"].sum())
    total_panelists = FinalMatch_display["Panelists"].sum()

    summary_cards = f"""
    <table style="width:100%;border-collapse:collapse;margin-bottom:30px;">
      <tr>
        <td style="width:33%;padding:10px;">
          <div style="background-color:#ffffff;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.08);
                      border:1px solid #e0e0e0;padding:20px;text-align:center;">
            <div style="font-size:18px;font-weight:600;color:#004080;margin-bottom:8px;">
              Total Completes Needed
            </div>
            <div style="font-size:28px;font-weight:700;color:#0077c8;">
              {total_completes:,}
            </div>
          </div>
        </td>
        <td style="width:33%;padding:10px;">
          <div style="background-color:#ffffff;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.08);
                      border:1px solid #e0e0e0;padding:20px;text-align:center;">
            <div style="font-size:18px;font-weight:600;color:#004080;margin-bottom:8px;">
              Recruitment Requests
            </div>
            <div style="font-size:28px;font-weight:700;color:#0077c8;">
              {total_recruits:,}
            </div>
          </div>
        </td>
        <td style="width:33%;padding:10px;">
          <div style="background-color:#ffffff;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,0.08);
                      border:1px solid #e0e0e0;padding:20px;text-align:center;">
            <div style="font-size:18px;font-weight:600;color:#004080;margin-bottom:8px;">
              Panelists Needed
            </div>
            <div style="font-size:28px;font-weight:700;color:#0077c8;">
              {total_panelists:,}
            </div>
          </div>
        </td>
      </tr>
    </table>
    """


    # --- Tabelas por país em 2 colunas ---
    html_sections = []
    for country in FinalMatch_display["Code"].unique():
        df_country = FinalMatch_display[FinalMatch_display["Code"] == country]

        # Busca requests do país
        requests_row = requests_by_country[requests_by_country["code"] == country]
        num_requests = (
            int(requests_row["Requests"].values[0]) if not requests_row.empty else 0
        )

        header = """
        <table style="width:100%;border-collapse:collapse;border:1px solid #d9d9d9;
                      font-family:'Arial',sans-serif;font-size:13px;margin-bottom:10px;">
          <thead>
            <tr style="background-color:#0077c8;color:white;">
              <th style="border:1px solid #d9d9d9;padding:6px;text-align:left;">Region</th>
              <th style="border:1px solid #d9d9d9;padding:6px;text-align:left;">Age Group</th>
              <th style="border:1px solid #d9d9d9;padding:6px;text-align:left;">Gender</th>
              <th style="border:1px solid #d9d9d9;padding:6px;text-align:right;">Completes</th>
              <th style="border:1px solid #d9d9d9;padding:6px;text-align:right;">CPI (USD)</th>
              <th style="border:1px solid #d9d9d9;padding:6px;text-align:right;">Panelists</th>
            </tr>
          </thead>
          <tbody>
        """

        rows = ""
        for _, r in df_country.iterrows():
            region_name = str(r["region"])
            highlight = "background-color:#fff8c6;" if "nacional" in region_name.lower() or "national" in region_name.lower() else ""
            rows += f"""
            <tr style="{highlight}">
              <td style="border:1px solid #d9d9d9;padding:6px;font-weight:bold;">{region_name}</td>
              <td style="border:1px solid #d9d9d9;padding:6px;">{r['AgeGroup']}</td>
              <td style="border:1px solid #d9d9d9;padding:6px;">{r['Gender']}</td>
              <td style="border:1px solid #d9d9d9;padding:6px;text-align:right;">{int(r['Completes']):,}</td>
              <td style="border:1px solid #d9d9d9;padding:6px;text-align:right;">${r['CPI']:.2f}</td>
              <td style="border:1px solid #d9d9d9;padding:6px;text-align:right;">{int(r.get('Panelists',0)):,}</td>
            </tr>
            """

        footer = "</tbody></table>"
        tabela = header + rows + footer

        bandeira = BANDEIRAS.get(country, "🌍")
        total_completes = int(df_country["Completes"].sum())
        total_panelists = int(df_country.get("Panelists", 0).sum() if "Panelists" in df_country.columns else 0)

        bloco = f"""
        <td valign="top" width="50%" style="padding:10px;">
          <div style="border:1px solid #e0e0e0;border-radius:8px;background-color:#ffffff;
                      box-shadow:0 1px 3px rgba(0,0,0,0.05);padding:12px;">
            <div style="font-size:16px;font-weight:bold;margin-bottom:6px;color:#004080;">
              {bandeira} {country} — {total_completes:,} completes | {num_requests} requests | {total_panelists:,} panelists
            </div>
            {tabela}
          </div>
        </td>
        """
        html_sections.append(bloco)

    rows = []
    for i in range(0, len(html_sections), 2):
        col1 = html_sections[i]
        col2 = html_sections[i + 1] if i + 1 < len(html_sections) else "<td width='50%'></td>"
        rows.append(f"<tr>{col1}{col2}</tr>")

    html_body = f"<table width='100%' style='border-collapse:collapse;'>{''.join(rows)}</table>"

    # --- Seção NoMatch ---
    if NoMatch is not None and not NoMatch.empty:
        no_match_html = """
        <div style="background-color:#f8fafc;border:1px solid #d9d9d9;border-radius:8px;
                    padding:20px;margin-top:30px;">
          <h3 style="color:#004080;font-size:18px;font-weight:600;margin-top:0;">
            🔍 Projects Without Matches
          </h3>
          <p style="font-size:13px;color:#555;margin-bottom:10px;">
            These projects were not included in the KPI metrics above.
          </p>
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="background-color:#0077c8;color:white;">
        """
        for col in NoMatch.columns:
            no_match_html += f"<th style='border:1px solid #d9d9d9;padding:6px;text-align:left;'>{col}</th>"
        no_match_html += "</tr></thead><tbody>"

        for _, row in NoMatch.iterrows():
          no_match_html += "<tr>"
          for col in NoMatch.columns:
              cell_value = row[col]
              # Se for a coluna Project_ID, cria o hyperlink
              if col == "Project_ID":
                  url = f"https://sample.offerwise.com/project/recruit/{cell_value}"
                  cell_html = f"<a href='{url}' target='_blank' style='color:#0077c8;text-decoration:none;'>{cell_value}</a>"
              else:
                  cell_html = cell_value
              no_match_html += f"<td style='border:1px solid #d9d9d9;padding:6px;'>{cell_html}</td>"
          no_match_html += "</tr>"
    else:
        no_match_html = ""

    # --- HTML Final ---
    email_html = f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#333;background-color:#f4f6f8;padding:0;margin:0;">
        <div style="background-color:#004080;color:white;padding:15px 25px;display:flex;align-items:center;gap:10px;">
          <h2 style="margin:0;font-weight:600;font-size:22px;">Recruitment Needs</h2>
        </div>
        <div style="background-color:#ffffff;padding:25px;margin:20px;border-radius:8px;border:1px solid #ddd;">
          <p style="font-size:15px;line-height:1.5;color:#333;">
            Hello,<br><br>
            Here's the summary of recruitment needs for today:
          </p>
          {summary_cards}
          {html_body}
          {no_match_html}
          <p style="font-size:13px;color:#555;margin-top:20px;">
            Any questions please contact Offerwise's Data Team.
          </p>
        </div>
                <!-- Rodapé corrigido -->
        <table width="100%" style="border-collapse:collapse;margin-top:40px;">
          <tr>
            <td align="center" style="background-color:#f4f6f8;padding:20px 0;border-top:1px solid #d9d9d9;">
              <p style="font-size:12px;color:#555;margin:0;line-height:1.6;">
                This e-mail was automatically generated.
              </p>
              <p style="font-size:12px;color:#777;margin:0;line-height:1.6;">
                © 2025 Offerwise | All rights reserved.
              </p>
            </td>
          </tr>
        </table>


      </body>
    </html>
    """
    return email_html


def send_email(sender, password, recipients, subject, html_body, attachment_path=None, cc=None, bcc=None):
    """Envia o e-mail formatado em HTML, com anexo opcional."""
    def _norm(x):
        if not x:
            return []
        if isinstance(x, str):
            return [x]
        return [str(i) for i in x if str(i).strip()]

    to_list = _norm(recipients)
    cc_list = _norm(cc)
    bcc_list = _norm(bcc)

    if not (to_list or cc_list or bcc_list):
        raise ValueError("Nenhum destinatário informado (To/Cc/Bcc).")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    if to_list:
        msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    msg.attach(MIMEText(html_body, "html"))

    if attachment_path:
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = attachment_path.split("/")[-1]
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)

    all_rcpts = []
    for x in to_list + cc_list + bcc_list:
        if x not in all_rcpts:
            all_rcpts.append(x)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg, from_addr=sender, to_addrs=all_rcpts)

    print(f"✅ E-mail enviado com sucesso para: {', '.join(all_rcpts)} | Anexo: '{attachment_path or '-'}'")
