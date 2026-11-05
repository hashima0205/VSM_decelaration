"""Create standalone PDFs with embedded Japanese fonts; original figure PDFs remain untouched."""
from pathlib import Path
import csv, re
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle,KeepTogether
from PIL import Image as PILImage

HERE=Path(__file__).resolve().parent
OUT=HERE/'VSM_rotation_paper_materials_2026-11-05'
pdfmetrics.registerFont(TTFont('JP','/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf'))
pdfmetrics.registerFontFamily('JP',normal='JP',bold='JP',italic='JP',boldItalic='JP')
W,H=A4; M=43; FW=W-2*M; FH=H-2*M
styles={
 'body':ParagraphStyle('body',fontName='JP',fontSize=9.2,leading=15.5,spaceAfter=8,wordWrap='CJK'),
 'h1':ParagraphStyle('h1',fontName='JP',fontSize=21,leading=30,spaceAfter=18,textColor=colors.HexColor('#123453'),keepWithNext=True,wordWrap='CJK'),
 'h2':ParagraphStyle('h2',fontName='JP',fontSize=14,leading=21,spaceBefore=15,spaceAfter=10,textColor=colors.HexColor('#123453'),keepWithNext=True,wordWrap='CJK'),
 'h3':ParagraphStyle('h3',fontName='JP',fontSize=11,leading=17,spaceBefore=10,spaceAfter=8,textColor=colors.HexColor('#234965'),keepWithNext=True,wordWrap='CJK'),
 'cell':ParagraphStyle('cell',fontName='JP',fontSize=7.8,leading=12,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='JP',fontSize=7.6,leading=12,spaceAfter=7,textColor=colors.HexColor('#4b5864'),wordWrap='CJK'),
 'code':ParagraphStyle('code',fontName='JP',fontSize=8,leading=13,spaceAfter=4,leftIndent=8,wordWrap='CJK'),
}
def inline(s):
    s=escape(s.replace("≥", ">=").replace("≤", "<="))
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:f'<link href="{m[2]}">{m[1]}</link>',s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'`([^`]+)`',r'\1',s)
    return s
def p(s,style='body'):return Paragraph(inline(s),styles[style])
def footer(canvas,doc):
    canvas.setFont('JP',7)
    canvas.setFillColor(colors.HexColor('#637687'))
    canvas.drawString(M,25,'VSM回転現象・論文執筆用資料　2026-11-05')
    canvas.drawRightString(W-M,25,str(doc.page))
def doc(path,story,title):
    d=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=M,rightMargin=M,topMargin=M,bottomMargin=M,title=title,author='Simulation study compilation',pageCompression=1)
    d.build(story,onFirstPage=footer,onLaterPages=footer)

def markdown_story(text):
    lines=text.splitlines();story=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('```'):
            i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                story.append(p(lines[i],'code'));i+=1
            story.append(Spacer(1,6));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                vals=[a.strip() for a in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',a) for a in vals):rows.append(vals)
                i+=1
            n=len(rows[0]);widths=([.28]+[.72/(n-1)]*(n-1)) if n>2 else [.29,.71]
            t=Table([[p(c,'cell') for c in row] for row in rows],colWidths=[FW*x for x in widths],repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f5')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#bbc8d1')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([t,Spacer(1,10)]);continue
        if line.startswith('# '):story.append(p(line[2:],'h1'))
        elif line.startswith('## '):story.append(p(line[3:],'h2'))
        elif line.startswith('### '):story.append(p(line[4:],'h3'))
        elif line.startswith('> '):story.append(p('【論旨】'+line[2:]))
        else:
            if line.startswith('- '):line='・'+line[2:]
            story.append(p(line))
        i+=1
    return story

figs=list(csv.DictReader((OUT/'report/FIGURE_CATALOG.csv').open()))
def figure_story(f):
    title=p(f"{f['id']}　{f['title']}",'h2')
    description=p(f['caption'])
    provenance=p(f"分類：{f['group']}　出典：{f['source']}",'small')
    # Use measured text heights to keep each figure and its caption together.
    texth=sum(a.wrap(FW,FH)[1] for a in [title,description,provenance])+70
    im=PILImage.open(OUT/f['png']);iw,ih=im.size
    scale=min(FW/iw,(FH-texth)/ih)
    photo=Image(str(OUT/f['png']),width=iw*scale,height=ih*scale)
    return [PageBreak(),title,photo,Spacer(1,9),description,provenance]

selected=['F01','F02','F03','F06','F11','F09','F07','F16','F17','F19','F21','F25','F26','F27','F30']
story=markdown_story((OUT/'report/REPORT_JA.md').read_text())
for fid in selected:story.extend(figure_story(next(f for f in figs if f['id']==fid)))
doc(OUT/'report/REPORT_JA.pdf',story,'容量補償VSM系統の負方向回転：論文執筆用統合レポート')
story=[p('全図一覧・図ごとの説明','h1'),p('2026年11月5日。補償後の既存31図を収録。今回のPIエネルギー蓄積・連続散逸の検討は含めない。'),p('F01–F30：容量補償後の主比較。F31：同じB5=1 pu、H=2.5秒でD1=0とした探索。補償前の図とDroop保存図は収録していない。'),p('図のPNG原本をこのPDFに収録した。ベクトル形式の原PDF/SVGがあるものはfigures内に併せて保存。全状態図など細かい図は原図を拡大して確認する。'),p('コピー元、用途、形式別ファイルへの対応はFIGURE_CATALOG.csv / HTMLを参照。主比較・反例・論文構成案はREPORT_JA.pdfに整理した。')]
for f in figs:story.extend(figure_story(f))
doc(OUT/'report/FIGURE_CATALOG.pdf',story,'VSM回転現象：全31図の図版と説明')
print('Created report and figure catalog PDFs with embedded Japanese font')
