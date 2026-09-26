import collections
import collections.abc
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
# Set slide dimensions to 16:9
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

BG_COLOR = RGBColor(15, 23, 42)
TEXT_COLOR = RGBColor(241, 245, 249)
ACCENT_CYAN = RGBColor(56, 189, 248)
ACCENT_GREEN = RGBColor(16, 185, 129)
ACCENT_RED = RGBColor(239, 68, 68)
BOX_BG = RGBColor(30, 41, 59)
LINE_COLOR = RGBColor(71, 85, 105)

def set_bg(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BG_COLOR

def add_text(slide, text, left, top, width, height, font_size, color=TEXT_COLOR, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = align
    return txBox

def add_box(slide, text, left, top, width, height, bg_color=BOX_BG, font_color=TEXT_COLOR, font_size=14, bold=True, outline_color=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if outline_color:
        shape.line.color.rgb = outline_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.color.rgb = LINE_COLOR
        shape.line.width = Pt(1)
    
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.alignment = PP_ALIGN.CENTER
    return shape

def add_node(slide, text, left, top, size, bg_color=BG_COLOR, outline_color=ACCENT_CYAN):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, size, size)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = outline_color
    shape.line.width = Pt(2)
    tf = shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(12)
    p.font.color.rgb = outline_color
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER
    return shape

def add_line(slide, x1, y1, width, height, is_vertical=False, color=LINE_COLOR):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x1, y1, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape

# SLIDE 1: TITLE
s1 = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s1)

# Network Motif
add_line(s1, Inches(2), Inches(3.7), Inches(9.3), Inches(0.05), color=LINE_COLOR)
add_node(s1, "ALIAS", Inches(1.5), Inches(3.2), Inches(1))
add_node(s1, "PGP", Inches(4.5), Inches(3.2), Inches(1))
add_node(s1, "BTC", Inches(7.5), Inches(3.2), Inches(1))
add_node(s1, "ENTITY", Inches(10.5), Inches(3.2), Inches(1), bg_color=ACCENT_CYAN, outline_color=TEXT_COLOR)

add_text(s1, "GOTHAMITE", Inches(0), Inches(1.5), Inches(13.333), Inches(1.5), 68, ACCENT_CYAN, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
add_text(s1, "DARK-WEB THREAT ACTOR INVESTIGATION", Inches(0), Inches(2.5), Inches(13.333), Inches(0.5), 20, TEXT_COLOR, False, PP_ALIGN.CENTER)

# Admin Info
admin_box = add_box(s1, "", Inches(3.66), Inches(4.8), Inches(6), Inches(2.2), BOX_BG)
tf = admin_box.text_frame
tf.clear()
lines = [
    ("SMART INDIA HACKATHON 2026", 14, True, ACCENT_CYAN),
    ("SIH26151 | Dark Web Threat Actor De-anonymization", 14, False, TEXT_COLOR),
    ("Theme: Blockchain & Cybersecurity | Category: Software", 12, False, RGBColor(200, 200, 200)),
    ("", 10, False, TEXT_COLOR),
    ("Team Name: AvivCREW", 14, True, TEXT_COLOR),
    ("Team ID: [TO BE ADDED] | Institute Code: [TO BE ADDED]", 12, False, RGBColor(200, 200, 200))
]
for text, size, bold, color in lines:
    p = tf.add_paragraph()
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = PP_ALIGN.CENTER


# SLIDE 2: PROBLEM + ANSWER
s2 = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s2)
add_text(s2, "THE FRAGMENTATION PROBLEM & OUR ANSWER", Inches(0.5), Inches(0.5), Inches(12), Inches(0.8), 28, ACCENT_CYAN, True)

# Streams
add_box(s2, "FORUMS", Inches(0.5), Inches(1.8), Inches(2), Inches(0.6), BOX_BG)
add_box(s2, "MARKETPLACES", Inches(0.5), Inches(2.6), Inches(2), Inches(0.6), BOX_BG)
add_box(s2, "LEAKS", Inches(0.5), Inches(3.4), Inches(2), Inches(0.6), BOX_BG)

add_line(s2, Inches(2.5), Inches(2.9), Inches(1.5), Inches(0.05), color=LINE_COLOR)

add_text(s2, "ALIAS • PGP • BTC • ARTIFACT", Inches(2.7), Inches(2.5), Inches(3), Inches(0.5), 14, TEXT_COLOR, False, PP_ALIGN.CENTER)

add_box(s2, "GOTHAMITE", Inches(5.5), Inches(2.6), Inches(2.2), Inches(0.8), ACCENT_CYAN, BOX_BG, 20, True)

add_line(s2, Inches(7.7), Inches(2.9), Inches(1), Inches(0.05), color=LINE_COLOR)

add_box(s2, "DETERMINISTIC\nCORRELATION", Inches(8.5), Inches(2.6), Inches(2), Inches(0.8), BOX_BG, outline_color=ACCENT_CYAN)

add_line(s2, Inches(10.5), Inches(2.9), Inches(0.5), Inches(0.05), color=LINE_COLOR)

add_box(s2, "INVESTIGATOR\nGRAPH", Inches(10.8), Inches(2.6), Inches(2), Inches(0.8), BOX_BG, outline_color=ACCENT_CYAN)

add_text(s2, "NOT EVERY CONNECTION MEANS IDENTITY.", Inches(0), Inches(4.5), Inches(13.33), Inches(0.5), 24, ACCENT_CYAN, True, PP_ALIGN.CENTER)

# 3 Mechanisms
m1 = add_box(s2, "CONTRADICTION-AWARE SCORING\n\nPenalizes concurrent activity overlap\n(-0.30 weight) to mathematicaly\nfilter typosquatting decoys.", Inches(1), Inches(5.5), Inches(3.5), Inches(1.2), BOX_BG, font_size=12, bold=False)
m1.text_frame.paragraphs[0].font.bold = True
m1.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

m2 = add_box(s2, "EVIDENCE PROVENANCE\n\nEvery graph edge links directly\nto immutable, SHA-256 hashed\nsource artifacts.", Inches(4.9), Inches(5.5), Inches(3.5), Inches(1.2), BOX_BG, font_size=12, bold=False)
m2.text_frame.paragraphs[0].font.bold = True
m2.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

m3 = add_box(s2, "INTERACTION ISOLATION\n\n'Transacted with' edges are structurally\nisolated and never promoted to\nidentity linkages.", Inches(8.8), Inches(5.5), Inches(3.5), Inches(1.2), BOX_BG, font_size=12, bold=False)
m3.text_frame.paragraphs[0].font.bold = True
m3.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN


# SLIDE 3: SYSTEM ARCHITECTURE
s3 = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s3)
add_text(s3, "SYSTEM ARCHITECTURE & DATA FLOW", Inches(0.5), Inches(0.5), Inches(12), Inches(0.8), 28, ACCENT_CYAN, True)

# Left Arch
add_box(s3, "DARK-WEB SOURCES", Inches(1), Inches(1.5), Inches(4.5), Inches(0.5), BOX_BG, font_size=12)
add_line(s3, Inches(3.2), Inches(2), Inches(0.05), Inches(0.4), color=LINE_COLOR)

add_box(s3, "INGEST\nFastAPI", Inches(1), Inches(2.4), Inches(4.5), Inches(0.8), BOX_BG, font_size=14, outline_color=ACCENT_CYAN)
add_line(s3, Inches(3.2), Inches(3.2), Inches(0.05), Inches(0.4), color=LINE_COLOR)

add_box(s3, "EVIDENCE LAYER\nSQLite / SQLAlchemy", Inches(1), Inches(3.6), Inches(4.5), Inches(0.8), BOX_BG, font_size=14, outline_color=ACCENT_CYAN)
add_line(s3, Inches(3.2), Inches(4.4), Inches(0.05), Inches(0.4), color=LINE_COLOR)

add_box(s3, "DETERMINISTIC CORRELATION\nRules + NetworkX", Inches(1), Inches(4.8), Inches(4.5), Inches(0.8), BOX_BG, font_size=14, outline_color=ACCENT_CYAN)
add_line(s3, Inches(3.2), Inches(5.6), Inches(0.05), Inches(0.4), color=LINE_COLOR)

add_box(s3, "INVESTIGATOR GRAPH\nStreamlit + streamlit-agraph", Inches(1), Inches(6.0), Inches(4.5), Inches(0.8), ACCENT_CYAN, BOX_BG, font_size=14)

# Right Data Flow
add_line(s3, Inches(7.5), Inches(1.75), Inches(0.05), Inches(4.65), color=LINE_COLOR)
for y in [1.75, 2.8, 4.0, 5.2, 6.4]:
    add_node(s3, "", Inches(7.45), Inches(y-0.05), Inches(0.15), bg_color=ACCENT_CYAN, outline_color=ACCENT_CYAN)

add_box(s3, "SOURCE DATA\nRaw dark-web content", Inches(8), Inches(1.5), Inches(4), Inches(0.6), BOX_BG, font_size=12)
add_box(s3, "IMMUTABLE ARTIFACT\nSHA-256 hashed payload", Inches(8), Inches(2.5), Inches(4), Inches(0.6), BOX_BG, font_size=12)
add_box(s3, "ENTITY / IDENTIFIER\nExtracted PGP, Base58, Alias", Inches(8), Inches(3.7), Inches(4), Inches(0.6), BOX_BG, font_size=12)
add_box(s3, "SCORED RELATIONSHIP\nArithmetic linkage weights", Inches(8), Inches(4.9), Inches(4), Inches(0.6), BOX_BG, font_size=12)
add_box(s3, "INVESTIGATION GRAPH\nRendered visual topology", Inches(8), Inches(6.1), Inches(4), Inches(0.6), BOX_BG, font_size=12)

# Arrows mapping layers to data
add_line(s3, Inches(5.5), Inches(2.8), Inches(2), Inches(0.03), color=LINE_COLOR)
add_line(s3, Inches(5.5), Inches(4.0), Inches(2), Inches(0.03), color=LINE_COLOR)
add_line(s3, Inches(5.5), Inches(5.2), Inches(2), Inches(0.03), color=LINE_COLOR)
add_line(s3, Inches(5.5), Inches(6.4), Inches(2), Inches(0.03), color=LINE_COLOR)


# SLIDE 4: DEFENSE
s4 = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s4)
add_text(s4, "ADVERSARIAL INPUT → DEFENSIVE CORRELATION", Inches(0.5), Inches(0.5), Inches(12), Inches(0.8), 28, ACCENT_CYAN, True)

# Core concept
concept_box = add_box(s4, "", Inches(0.5), Inches(1.5), Inches(12.33), Inches(2), BOX_BG)
add_text(s4, "INTERACTION ≠ IDENTITY", Inches(0), Inches(1.7), Inches(13.33), Inches(0.5), 24, ACCENT_CYAN, True, PP_ALIGN.CENTER)
add_node(s4, "ACTOR A", Inches(3.5), Inches(2.3), Inches(1), outline_color=TEXT_COLOR)
add_line(s4, Inches(4.5), Inches(2.8), Inches(4.3), Inches(0.05), color=RGBColor(100, 100, 100))
add_text(s4, "transacted_with", Inches(4.5), Inches(2.5), Inches(4.3), Inches(0.3), 12, TEXT_COLOR, False, PP_ALIGN.CENTER)
add_node(s4, "ACTOR B", Inches(8.8), Inches(2.3), Inches(1), outline_color=TEXT_COLOR)

add_text(s4, "A transaction is evidence of interaction, not proof of common identity.", Inches(0), Inches(3.6), Inches(13.33), Inches(0.5), 16, RGBColor(200, 200, 200), False, PP_ALIGN.CENTER)

# 4 Mitigations
def threat_box(s, y, threat, defense):
    add_box(s, threat, Inches(1), Inches(y), Inches(4.5), Inches(0.7), BOX_BG, ACCENT_RED, 16, True, outline_color=ACCENT_RED)
    add_line(s, Inches(5.5), Inches(y+0.33), Inches(2.3), Inches(0.05), color=LINE_COLOR)
    add_box(s, defense, Inches(7.8), Inches(y), Inches(4.5), Inches(0.7), BOX_BG, ACCENT_GREEN, 16, True, outline_color=ACCENT_GREEN)

threat_box(s4, 4.3, "HOSTILE INPUT", "STRICT PAYLOAD VALIDATION")
threat_box(s4, 5.2, "FALSE LINKAGES", "CONTRADICTION-AWARE SCORING")
threat_box(s4, 6.1, "AUDITABILITY FAILURE", "SHA-256 PROVENANCE")


# SLIDE 5: INVESTIGATOR EXPERIENCE
s5 = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s5)
add_text(s5, "THE INVESTIGATOR EXPERIENCE", Inches(0.5), Inches(0.5), Inches(12), Inches(0.8), 28, ACCENT_CYAN, True)

# Screenshot placeholder
ss_box = add_box(s5, "[SCREENSHOT TO BE ADDED]\n\nENTITY GRAPH / WORKBENCH\n\nALIAS ───── PGP ───── BTC ───── ENTITY", Inches(4), Inches(1.5), Inches(8.8), Inches(5), RGBColor(10, 15, 25), LINE_COLOR, 16, outline_color=LINE_COLOR)

# 4 Outcomes on left
out1 = add_box(s5, "STANDARDIZED ATTRIBUTION\nArithmetic, explainable linkage signals", Inches(0.5), Inches(1.5), Inches(3.2), Inches(1.1), BOX_BG, font_size=12, bold=False)
out1.text_frame.paragraphs[0].font.bold = True
out1.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

out2 = add_box(s5, "AUDITABLE EVIDENCE\nSHA-256 provenance and traceability", Inches(0.5), Inches(2.8), Inches(3.2), Inches(1.1), BOX_BG, font_size=12, bold=False)
out2.text_frame.paragraphs[0].font.bold = True
out2.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

out3 = add_box(s5, "REDUCED MANUAL BIAS\nConsistent deterministic scoring", Inches(0.5), Inches(4.1), Inches(3.2), Inches(1.1), BOX_BG, font_size=12, bold=False)
out3.text_frame.paragraphs[0].font.bold = True
out3.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

out4 = add_box(s5, "INVESTIGATOR VISIBILITY\nGraph-based relationship exploration", Inches(0.5), Inches(5.4), Inches(3.2), Inches(1.1), BOX_BG, font_size=12, bold=False)
out4.text_frame.paragraphs[0].font.bold = True
out4.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

add_text(s5, "Cryptographically backed, auditable evidence designed to support rigorous digital investigations.", Inches(0), Inches(6.8), Inches(13.33), Inches(0.5), 16, ACCENT_CYAN, False, PP_ALIGN.CENTER)


# SLIDE 6: DIFFERENTIATOR / CLOSE
s6 = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(s6)

add_text(s6, "FROM DARK-WEB FRAGMENTS", Inches(0), Inches(1.2), Inches(13.33), Inches(0.6), 28, RGBColor(200,200,200), True, PP_ALIGN.CENTER)
add_text(s6, "TO TRACEABLE ACTOR INTELLIGENCE", Inches(0), Inches(1.8), Inches(13.33), Inches(0.8), 36, ACCENT_CYAN, True, PP_ALIGN.CENTER)

add_box(s6, "DETERMINISTIC\nCORRELATION", Inches(1), Inches(3), Inches(2.5), Inches(1), BOX_BG, outline_color=ACCENT_CYAN)
add_text(s6, "+", Inches(3.7), Inches(3.3), Inches(0.5), Inches(0.5), 24, TEXT_COLOR, True, PP_ALIGN.CENTER)
add_box(s6, "EVIDENCE\nPROVENANCE", Inches(4.0), Inches(3), Inches(2.5), Inches(1), BOX_BG, outline_color=ACCENT_CYAN)
add_text(s6, "+", Inches(6.7), Inches(3.3), Inches(0.5), Inches(0.5), 24, TEXT_COLOR, True, PP_ALIGN.CENTER)
add_box(s6, "CONTRADICTION-AWARE\nDEFENSE", Inches(7.0), Inches(3), Inches(2.5), Inches(1), BOX_BG, outline_color=ACCENT_CYAN)
add_text(s6, "+", Inches(9.7), Inches(3.3), Inches(0.5), Inches(0.5), 24, TEXT_COLOR, True, PP_ALIGN.CENTER)
add_box(s6, "SAFE SYNTHETIC\nVALIDATION", Inches(10.0), Inches(3), Inches(2.5), Inches(1), BOX_BG, outline_color=ACCENT_CYAN)

add_line(s6, Inches(1.5), Inches(4.5), Inches(10.33), Inches(0.05), color=LINE_COLOR)
add_node(s6, "", Inches(1.4), Inches(4.45), Inches(0.15), ACCENT_CYAN, ACCENT_CYAN)
add_node(s6, "", Inches(3.9), Inches(4.45), Inches(0.15), ACCENT_CYAN, ACCENT_CYAN)
add_node(s6, "", Inches(6.4), Inches(4.45), Inches(0.15), ACCENT_CYAN, ACCENT_CYAN)
add_node(s6, "", Inches(8.9), Inches(4.45), Inches(0.15), ACCENT_CYAN, ACCENT_CYAN)
add_node(s6, "", Inches(11.4), Inches(4.45), Inches(0.15), ACCENT_CYAN, ACCENT_CYAN)
add_text(s6, "SOURCE                 ARTIFACT                 ENTITY                 RELATIONSHIP                 ACTOR GRAPH", Inches(1.2), Inches(4.7), Inches(11), Inches(0.5), 12, TEXT_COLOR, True, PP_ALIGN.CENTER)

footer = add_box(s6, "", Inches(1), Inches(5.8), Inches(11.33), Inches(1), RGBColor(10,15,25), outline_color=LINE_COLOR)
ftf = footer.text_frame
ftf.clear()
p1 = ftf.add_paragraph()
p1.text = "References & Standards: • Digital Evidence Handling Standards • Deterministic PGP / Base58 Cryptocurrency Validation"
p1.font.size = Pt(12)
p1.font.color.rgb = RGBColor(150, 150, 150)
p1.alignment = PP_ALIGN.CENTER
p2 = ftf.add_paragraph()
p2.text = "• Containerized mock Tor networks (.onion.mock) for ethical extraction validation • OSINT architectural benchmarks"
p2.font.size = Pt(12)
p2.font.color.rgb = RGBColor(150, 150, 150)
p2.alignment = PP_ALIGN.CENTER

prs.save('C:/Users/aadik/sih 2026/gothamite/ppt/GOTHAMITE_SIH_2026_FINAL.pptx')
