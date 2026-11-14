import os
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Cyrillic Arial fonts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
arial_path = os.path.join(FONTS_DIR, "arial.ttf")
arialbd_path = os.path.join(FONTS_DIR, "arialbd.ttf")

if os.path.exists(arial_path):
    pdfmetrics.registerFont(TTFont("Arial", arial_path))
if os.path.exists(arialbd_path):
    pdfmetrics.registerFont(TTFont("Arial-Bold", arialbd_path))

def create_targetpro_pdf(handle, target_data=None, smm_digital=None):
    target_data = target_data or {}
    smm_digital = smm_digital or {}

    clean_handle = re.sub(r'[^A-Za-z0-9._-]', '', handle).lstrip('@')
    niche_name = target_data.get("shortName") or target_data.get("niche") or "Бизнес & Услуги"
    geo_name = target_data.get("geo") or "Казахстан / СНГ"
    avg_check = target_data.get("check") or "Стандарт"
    usp_text = target_data.get("usp") or "Быстрый расчет, гарантия качества и понятный сервис"
    diagnosis_text = target_data.get("diagnosis") or f"Для аккаунта @{clean_handle} критически важно упаковать конкретную выгоду в шапке профиля и переводить входящий трафик из Reels напрямую в WhatsApp."
    bad_offer = target_data.get("badOffer") or "«Высокое качество, доступные цены, пишите в Директ!»"
    killer_offer = target_data.get("killerOffer") or f"«Узнайте точную стоимость по «{niche_name}» в {geo_name} за 1 минуту в WhatsApp + заберите подарок к первому заказу!»"
    funnel_steps = target_data.get("funnelSteps") or [
        "Короткий Reels (15–20 сек) с наглядным обзором услуги и честными ценами",
        "Переход клиента в WhatsApp в 1 клик (Предзаказ / Расчёт / Бронь)",
        "Ответ менеджера за 3 минуты с отправкой прайса и геолокации 2ГИС"
    ]
    hooks = target_data.get("hooks") or [
        {
            "type": "Разбор острой боли клиента",
            "visual": "Процесс работы крупным планом или эмоциональная ситуация",
            "onScreenText": f"Ищете честный сервис по {niche_name.lower()}?",
            "spokenLine": "Показываю за 15 секунд реальные цены и как не переплатить..."
        },
        {
            "type": "Кейс и наглядные цифры",
            "visual": "Сравнение ДО / ПОСЛЕ или живой отзыв довольного клиента",
            "onScreenText": "Как сэкономить деньги и время при первом заказе",
            "spokenLine": "Смотрите, как мы решаем эту задачу под ключ за 1 день..."
        }
    ]
    segments = target_data.get("segments") or [
        {
            "name": f"Горячий локальный спрос ({geo_name})",
            "who": f"Жители города {geo_name}, которым нужна услуга прямо сейчас.",
            "fear": "Скрытые доплаты, некачественная работа и долгое ожидание.",
            "trigger": "Открытый прайс, живые видео в Reels и быстрый ответ в WhatsApp."
        }
    ]
    seo_bio = smm_digital.get("seoName") or f"{niche_name.upper()} • {geo_name.upper()}"
    targeting_notes = smm_digital.get("digitalBudget") or f"Рекомендуемый бюджет на таргет: $5–15/день. Цель: Лиды в WhatsApp / Сообщения в Direct. Гео: {geo_name} (+ радиус 5–10 км)."

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=14*mm,
        leftMargin=14*mm,
        topMargin=14*mm,
        bottomMargin=14*mm
    )

    styles = getSampleStyleSheet()
    font_regular = "Arial" if "Arial" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    font_bold = "Arial-Bold" if "Arial-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"

    title_style = ParagraphStyle("TTitle", fontName=font_bold, fontSize=16, leading=20, textColor=colors.HexColor("#0D9488"))
    subtitle_style = ParagraphStyle("TSubtitle", fontName=font_regular, fontSize=9, leading=13, textColor=colors.HexColor("#64748B"))
    h2_style = ParagraphStyle("TH2", fontName=font_bold, fontSize=12, leading=16, textColor=colors.HexColor("#0D9488"), spaceBefore=10, spaceAfter=4)
    normal_style = ParagraphStyle("TNormal", fontName=font_regular, fontSize=9, leading=13, textColor=colors.HexColor("#1E293B"))
    bold_style = ParagraphStyle("TBold", fontName=font_bold, fontSize=9, leading=13, textColor=colors.HexColor("#1E293B"))
    white_bold = ParagraphStyle("TWhiteBold", fontName=font_bold, fontSize=9, leading=13, textColor=colors.white)

    story = []

    # 1. Header Card
    header_data = [
        [
            Paragraph("⚡ TARGETPRO AI — МАРКЕТИНГ-ПЛАН И АУДИТ", title_style),
            Paragraph(f"Дата: <b>{datetime.now().strftime('%d.%m.%Y')}</b><br/>Профиль: <b>@{clean_handle}</b>", subtitle_style)
        ]
    ]
    t_header = Table(header_data, colWidths=[125*mm, 55*mm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D9488"), spaceBefore=4, spaceAfter=10))

    # 2. Executive Summary Box
    summary_data = [
        [
            Paragraph(f"<b>Ниша бизнеса:</b> {niche_name}<br/><b>Гео-локация:</b> {geo_name}<br/><b>Средний чек:</b> {avg_check}", normal_style),
            Paragraph(f"<b>Главное УТП:</b> {usp_text}<br/><b>Рекомендуемый поисковый заголовок Bio:</b><br/><font color='#0D9488'><b>{seo_bio}</b></font>", normal_style)
        ]
    ]
    t_summary = Table(summary_data, colWidths=[80*mm, 100*mm])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ECFDF5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#99F6E4")),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 8))

    # 3. Diagnosis & Offer Box
    story.append(Paragraph("1. Диагноз профиля и офферная воронка", h2_style))
    story.append(Paragraph(diagnosis_text, normal_style))
    story.append(Spacer(1, 6))

    offers_data = [
        [Paragraph("❌ <b>Слабый оффер (как сливаются заявки):</b>", bold_style)],
        [Paragraph(bad_offer, normal_style)],
        [Paragraph("🔥 <b>Убойный оффер (Killer Offer для рекламы и шапки):</b>", bold_style)],
        [Paragraph(f"<b>«{killer_offer}»</b>", normal_style)]
    ]
    t_offers = Table(offers_data, colWidths=[180*mm])
    t_offers.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#FFF1F2")),
        ('BACKGROUND', (0,2), (-1,3), colors.HexColor("#F0FDF4")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_offers)
    story.append(Spacer(1, 8))

    # 4. Sales Funnel
    story.append(Paragraph("2. 3 шага воронки продаж (Reels ➔ WhatsApp ➔ Продажа)", h2_style))
    funnel_rows = []
    for idx, step in enumerate(funnel_steps, 1):
        funnel_rows.append([
            Paragraph(f"<b>Шаг {idx}</b>", white_bold),
            Paragraph(step, normal_style)
        ])
    t_funnel = Table(funnel_rows, colWidths=[20*mm, 160*mm])
    t_funnel.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#0D9488")),
        ('BACKGROUND', (1,0), (1,-1), colors.HexColor("#F8FAFC")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_funnel)
    story.append(Spacer(1, 8))

    # 5. Hooks for Reels
    story.append(Paragraph("3. Топовые хуки для Reels и баннеров (0–3 сек)", h2_style))
    hooks_rows = [
        [Paragraph("<b>Тип хука</b>", bold_style), Paragraph("<b>Визуал (0-3 сек)</b>", bold_style), Paragraph("<b>Текст на видео и озвучка</b>", bold_style)]
    ]
    for h in hooks[:3]:
        h_type = h.get("type", "Хук")
        h_vis = h.get("visual", "Крупный план")
        h_txt = f"<b>Надпись:</b> «{h.get('onScreenText', '')}»<br/><b>Голос:</b> «{h.get('spokenLine', '')}»"
        hooks_rows.append([Paragraph(h_type, bold_style), Paragraph(h_vis, normal_style), Paragraph(h_txt, normal_style)])

    t_hooks = Table(hooks_rows, colWidths=[40*mm, 55*mm, 85*mm])
    t_hooks.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#ECFDF5")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_hooks)
    story.append(Spacer(1, 8))

    # 6. Target Settings
    story.append(Paragraph("4. Рекомендации по таргетированной рекламе", h2_style))
    story.append(Paragraph(targeting_notes, normal_style))
    story.append(Spacer(1, 10))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceBefore=6, spaceAfter=6))
    footer_text = "TargetPro AI • Персональный ИИ-маркетолог и таргетолог • Автор: <b>@imamaliev.ads</b> • Telegram: <b>@TargetPro_ai</b>"
    story.append(Paragraph(footer_text, subtitle_style))

    doc.build(story)
    return pdf_buffer.getvalue()

if __name__ == "__main__":
    b = create_targetpro_pdf("imamaliev.ads")
    print("Generated bytes:", len(b))
